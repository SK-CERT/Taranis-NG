"""Integrity of CSAF documents: the published hash files and OpenPGP signatures.

A CSAF provider publishes `<document>.sha256` and/or `<document>.sha512` next to each document,
and a trusted provider also `<document>.asc`, signed with a key listed in its provider
metadata. The collector records the outcome as attributes and collects the document whatever
it is, so the checks here only ever report.
"""

from __future__ import annotations

import codecs
import hashlib
import hmac
import re
import string
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pysequoia import Cert, Sig, packet, verify

if TYPE_CHECKING:
    from collections.abc import Iterable

# Outcomes, stored as the CSAF_HASH and CSAF_SIGNATURE attribute values.
VALID = "valid"
MISMATCH = "mismatch"
MISSING = "missing"
INVALID = "invalid"
UNVERIFIED = "unverified"

# A hash file normally starts with the hex digest, followed by the file name (sha512sum).
# Windows' certutil writes it on a line of its own, in UTF-16, possibly with spaces between the
# bytes (OPC Foundation). The file is checked by content either way, because a missing one does
# not always answer 404: some servers redirect to an HTML page (Microsoft).
_DIGEST = re.compile(r"\A\s*([0-9A-Fa-f]{128}|[0-9A-Fa-f]{64})(?![0-9A-Fa-f])")
_DIGEST_LENGTHS = (64, 128)
_SIGNATURE_MARKER = b"-----BEGIN PGP SIGNATURE-----"


def _decode(body: bytes) -> str:
    if body.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return body.decode("utf-16", errors="replace")
    return body.decode("utf-8-sig", errors="replace")


def parse_digest(body: bytes) -> str | None:
    """Read the digest from a hash file.

    Args:
        body (bytes): The hash file.

    Returns:
        The lower-case hex digest, or None when the file holds none.
    """
    text = _decode(body)
    if match := _DIGEST.match(text):
        return match.group(1).lower()
    for line in text.splitlines():
        compact = line.strip().replace(" ", "")
        if len(compact) in _DIGEST_LENGTHS and all(character in string.hexdigits for character in compact):
            return compact.lower()
    return None


def line_ending_variants(document: bytes) -> list[bytes]:
    """The document with its line endings converted, as it may have been hashed or signed.

    A publisher that hashes and signs a file on Windows and commits it to Git gets it served
    with LF line endings, so the published hash and signature cover the CRLF version (OPC
    Foundation). The JSON is the same either way.
    """
    lf = document.replace(b"\r\n", b"\n")
    return [variant for variant in (lf.replace(b"\n", b"\r\n"), lf) if variant != document]


def check_digest(document: bytes, digest: str | None) -> str:
    """Compare a document with a published digest. SHA-512 and SHA-256 are told apart by length.

    Args:
        document (bytes): The document as downloaded.
        digest (str | None): The published digest, or None when none was found.

    Returns:
        VALID, MISMATCH or MISSING.
    """
    if not digest:
        return MISSING
    algorithm = hashlib.sha512 if len(digest) == max(_DIGEST_LENGTHS) else hashlib.sha256
    for candidate in (document, *line_ending_variants(document)):
        if hmac.compare_digest(algorithm(candidate).hexdigest(), digest):
            return VALID
    return MISMATCH


def looks_like_signature(body: bytes) -> bool:
    """Tell an armored OpenPGP signature from whatever a server answers for a missing one."""
    return _SIGNATURE_MARKER in body


def _normalized_fingerprint(value: str | None) -> str:
    return (value or "").replace(" ", "").lower()


@dataclass
class KeyRing:
    """The public keys a provider signs with.

    Besides the certificates, it keeps the fingerprint of every key in them - primary keys and
    subkeys - so a signature made by a key we do not hold is reported as unverified rather
    than invalid: that is a gap in what we know, not a sign of tampering.

    Attributes:
        rejected: Keys refused as suspicious - not a key, or not the one the metadata declares.
        unusable: Keys the verifier's policy refuses, e.g. bound with SHA-1 self-signatures
            (SUSE's). Signatures made with them are reported unverified, not invalid: GnuPG
            still accepts them, the weakness is the provider's.
    """

    certs: list = field(default_factory=list)
    fingerprints: set[str] = field(default_factory=set)
    rejected: list[str] = field(default_factory=list)
    unusable: list[str] = field(default_factory=list)

    def add(self, key_file: bytes, declared_fingerprint: str | None = None, *, origin: str = "") -> bool:
        """Add the usable certificates of one key file.

        Args:
            key_file (bytes): The key file, armored or binary.
            declared_fingerprint (str | None): The fingerprint the provider metadata lists
                for this key. A file whose certificates do not include it is refused: the
                metadata is what vouches for the key.
            origin (str): Where the file came from, for the messages.

        Returns:
            True when a certificate was added.
        """
        try:
            certs = Cert.split_bytes(key_file)
        except Exception as error:
            self.rejected.append(f"{origin}: not an OpenPGP key ({error})")
            return False
        if not certs:
            self.rejected.append(f"{origin}: no certificate in the file")
            return False
        declared = _normalized_fingerprint(declared_fingerprint)
        if declared and not any(_normalized_fingerprint(cert.fingerprint) == declared for cert in certs):
            self.rejected.append(f"{origin}: fingerprint does not match the declared {declared_fingerprint}")
            return False
        added = False
        for cert in certs:
            try:
                # Reading the expiration evaluates the binding signatures under the policy.
                _ = cert.expiration
                key_packets = packet.PacketPile.from_bytes(str(cert).encode())
            except Exception as error:
                # The last line of Sequoia's error chain ("1: SHA1 is not considered secure ...").
                reason = re.sub(r"^\d+:\s*", "", str(error).strip().splitlines()[-1].strip()) or type(error).__name__
                self.unusable.append(f"{origin}: key {cert.fingerprint} cannot be used ({reason})")
                continue
            self.certs.append(cert)
            self.fingerprints.update(_normalized_fingerprint(p.fingerprint) for p in key_packets if p.fingerprint)
            added = True
        return added

    def _holds_any(self, issuers: Iterable[str]) -> bool:
        # An issuer is a full fingerprint or a 16-hex key ID. The key ID is the low 64 bits of
        # a v4 fingerprint and the high 64 bits of a v6 one, so both ends are compared.
        return any(fingerprint.endswith(issuer) or fingerprint.startswith(issuer) for issuer in issuers for fingerprint in self.fingerprints)

    def verify(self, document: bytes, signature: bytes | None) -> str:
        """Check a detached signature over a document.

        Args:
            document (bytes): The document as downloaded.
            signature (bytes | None): The armored detached signature, or None when the provider
                publishes none.

        Returns:
            VALID; INVALID when the signature does not verify with a key we hold;
            UNVERIFIED when it was made with a key we do not hold; MISSING without a signature.
        """
        if signature is None:
            return MISSING
        try:
            issuers = {_normalized_fingerprint(p.issuer_fingerprint or p.issuer_key_id) for p in packet.PacketPile.from_bytes(signature)}
            issuers.discard("")
            parsed = Sig.from_bytes(signature)
        except Exception:
            return INVALID
        if issuers and not self._holds_any(issuers):
            return UNVERIFIED
        for candidate in (document, *line_ending_variants(document)):
            try:
                if verify(bytes=candidate, store=lambda _key_ids: self.certs, signature=parsed).valid_sigs:
                    return VALID
            except Exception:  # noqa: S112 - a failed verification is an answer, not an error
                continue
        # Without issuer information we cannot tell a foreign key from a bad signature.
        return INVALID if issuers else UNVERIFIED
