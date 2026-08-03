from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PRESENTERS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRESENTERS_ROOT))

from template_migrations import promote_default_vulnerability as migration  # noqa: E402


PAYLOAD_ROOT = PRESENTERS_ROOT / "template_migrations" / "v2" / "payload"


class DefaultTemplateMigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.target = Path(self.temporary.name) / "templates"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def payload(self, relative: Path) -> bytes:
        return (PAYLOAD_ROOT / relative).read_bytes()

    def write(self, relative: Path, content: bytes) -> Path:
        destination = self.target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return destination

    def assert_payload_installed(self) -> None:
        for relative in (migration.ENTRY, *migration.COMPANIONS):
            self.assertEqual(self.payload(relative), (self.target / relative).read_bytes())

    def test_known_legacy_is_migrated(self) -> None:
        legacy = self.payload(Path("pdf_template_legacy.html"))
        self.assertIn(hashlib.sha256(legacy).hexdigest(), migration.KNOWN_LEGACY_HASHES)
        self.write(migration.ENTRY, legacy)
        self.assertEqual("migrated", migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT))
        self.assert_payload_installed()

    def test_missing_default_is_installed(self) -> None:
        self.assertEqual("migrated", migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT))
        self.assert_payload_installed()

    def test_current_default_is_idempotent(self) -> None:
        for relative in (migration.ENTRY, *migration.COMPANIONS):
            self.write(relative, self.payload(relative))
        self.assertEqual("current", migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT))

    def test_unknown_default_is_preserved(self) -> None:
        custom = b"operator-customized-template\n"
        self.write(migration.ENTRY, custom)
        self.assertEqual("preserved", migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT))
        self.assertEqual(custom, (self.target / migration.ENTRY).read_bytes())
        for relative in migration.COMPANIONS:
            self.assertFalse((self.target / relative).exists())

    def test_unknown_companion_aborts_before_writes(self) -> None:
        legacy = self.payload(Path("pdf_template_legacy.html"))
        self.write(migration.ENTRY, legacy)
        conflict = self.write(Path("_shared/tlp.html"), b"operator macro\n")
        self.assertEqual("preserved", migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT))
        self.assertEqual(legacy, (self.target / migration.ENTRY).read_bytes())
        self.assertEqual(b"operator macro\n", conflict.read_bytes())
        self.assertFalse((self.target / "pdf_template_legacy.html").exists())

    def test_current_default_repairs_missing_companion(self) -> None:
        self.write(migration.ENTRY, self.payload(migration.ENTRY))
        self.assertEqual("repaired", migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT))
        self.assert_payload_installed()

    def test_symlink_entry_is_preserved(self) -> None:
        self.target.mkdir(parents=True)
        elsewhere = Path(self.temporary.name) / "elsewhere.html"
        elsewhere.write_bytes(self.payload(Path("pdf_template_legacy.html")))
        (self.target / migration.ENTRY).symlink_to(elsewhere)
        self.assertEqual("preserved", migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT))
        self.assertTrue((self.target / migration.ENTRY).is_symlink())

    def test_dry_run_writes_nothing(self) -> None:
        legacy = self.payload(Path("pdf_template_legacy.html"))
        self.write(migration.ENTRY, legacy)
        self.assertEqual(
            "would_migrate",
            migration.migrate(target_root=self.target, payload_root=PAYLOAD_ROOT, dry_run=True),
        )
        self.assertEqual(legacy, (self.target / migration.ENTRY).read_bytes())
        self.assertFalse((self.target / "pdf_template_legacy.html").exists())

    def test_operator_skip_environment(self) -> None:
        with patch.dict(os.environ, {"TARANIS_SKIP_DEFAULT_TEMPLATE_MIGRATION": "1"}, clear=False):
            self.assertEqual(0, migration.main(["--target-root", str(self.target), "--payload-root", str(PAYLOAD_ROOT)]))
        self.assertFalse(self.target.exists())

    def test_payload_matches_fresh_install_templates(self) -> None:
        templates_root = PRESENTERS_ROOT / "templates"
        for relative in (migration.ENTRY, *migration.COMPANIONS):
            self.assertEqual((templates_root / relative).read_bytes(), self.payload(relative))


if __name__ == "__main__":
    unittest.main()
