#!/usr/bin/env python3
"""Build GUI-importable multilingual tag-cloud stop-word CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from pathlib import Path


LANGUAGES = {
    "ar": ("Arabic", "ar_complete.csv"),
    "bn": ("Bengali", "bn_complete.csv"),
    "cs": ("Czech", "cz_complete.csv"),
    "de": ("German", "de_complete.csv"),
    "en": ("English", "en_complete.csv"),
    "es": ("Spanish", "es_complete.csv"),
    "fr": ("French", "fr_complete.csv"),
    "hi": ("Hindi", "hi_complete.csv"),
    "id": ("Indonesian", "id_complete.csv"),
    "it": ("Italian", "it_complete.csv"),
    "ja": ("Japanese", "ja_complete.csv"),
    "ko": ("Korean", "ko_complete.csv"),
    "mr": ("Marathi", "mr_complete.csv"),
    "nl": ("Dutch", "nl_complete.csv"),
    "pl": ("Polish", "pl_complete.csv"),
    "pt": ("Portuguese", "pt_complete.csv"),
    "ru": ("Russian", "ru_complete.csv"),
    "sk": ("Slovak", "sk_complete.csv"),
    "th": ("Thai", "th_complete.csv"),
    "tr": ("Turkish", "tr_complete.csv"),
    "uk": ("Ukrainian", "uk_complete.csv"),
    "ur": ("Urdu", "ur_complete.csv"),
    "vi": ("Vietnamese", "vi_complete.csv"),
    "zh": ("Chinese", "zh_complete.csv"),
}


def normalized_words(words: list[str]) -> list[str]:
    """Return stable, case-insensitive, de-duplicated stop words."""
    normalized = {
        unicodedata.normalize("NFKC", word).strip().casefold()
        for word in words
        if isinstance(word, str) and word.strip()
    }
    return sorted(normalized)


def read_existing(path: Path) -> dict[str, str]:
    """Read an existing GUI CSV so project-specific entries are retained."""
    if not path.exists():
        return {}

    with path.open(encoding="utf-8", newline="") as csv_file:
        rows = csv.DictReader(csv_file, delimiter=";")
        return {
            unicodedata.normalize("NFKC", row["value"]).strip().casefold(): row.get("description", "")
            for row in rows
            if row.get("value", "").strip()
        }


def write_gui_csv_files(source: dict[str, list[str]], output_dir: Path) -> None:
    """Write one GUI-importable category CSV for every selected language."""
    missing = sorted(set(LANGUAGES) - set(source))
    if missing:
        raise ValueError(f"Missing source languages: {', '.join(missing)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for code, (_language, filename) in LANGUAGES.items():
        path = output_dir / filename
        entries = read_existing(path)
        for word in normalized_words(source[code]):
            entries.setdefault(word, "")

        with path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=("value", "description"), delimiter=";", lineterminator="\n")
            writer.writeheader()
            writer.writerows({"value": word, "description": entries[word]} for word in sorted(entries))


def main() -> None:
    """Build checked-in CSV files from stopwords-iso JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Path to stopwords-iso.json")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory for <language>_complete.csv files",
    )
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    write_gui_csv_files(source, args.output_dir)


if __name__ == "__main__":
    main()
