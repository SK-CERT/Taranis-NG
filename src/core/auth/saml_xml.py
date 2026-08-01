"""Reduce a SAML response to the one signed element ``minisaml`` can verify.

``minisignxml`` verifies a document carrying *exactly one* ``ds:Signature``, and
``minisaml`` only understands *plaintext* assertions. Real identity providers
routinely violate both assumptions: a federation encrypts the assertion to the
service provider's public key, and many IdPs sign the Response *and* the
Assertion. Both cases are resolved here by extracting the signed Assertion and
handing that to ``minisaml``, which accepts an Assertion as the signed root and
reads issuer, audience, conditions and InResponseTo from inside it - so nothing
goes unchecked.

Only RSA-OAEP key transport is accepted. The legacy ``rsa-1_5`` (PKCS#1 v1.5) is
refused on purpose: it is the Bleichenbacher padding-oracle construction, and an
SP that accepts it is the oracle.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from defusedxml.lxml import fromstring
from lxml import etree

XENC = "http://www.w3.org/2001/04/xmlenc#"
XENC11 = "http://www.w3.org/2009/xmlenc11#"
DS = "http://www.w3.org/2000/09/xmldsig#"
SAML = "urn:oasis:names:tc:SAML:2.0:assertion"

NAMESPACES = {"xenc": XENC, "xenc11": XENC11, "ds": DS, "saml": SAML}

# Key transport. rsa-1_5 is deliberately absent - see the module docstring.
RSA_OAEP_MGF1P = f"{XENC}rsa-oaep-mgf1p"
RSA_OAEP = f"{XENC11}rsa-oaep"

# Digest algorithms an EncryptedKey may name for OAEP
DIGESTS = {
    f"{DS}sha1": hashes.SHA1,
    f"{XENC}sha256": hashes.SHA256,
    f"{XENC11}sha256": hashes.SHA256,
    f"{XENC}sha512": hashes.SHA512,
}
MGF_DIGESTS = {
    f"{XENC11}mgf1sha1": hashes.SHA1,
    f"{XENC11}mgf1sha256": hashes.SHA256,
    f"{XENC11}mgf1sha512": hashes.SHA512,
}

# Data encryption
AES_CBC = {f"{XENC}aes128-cbc": 16, f"{XENC}aes192-cbc": 24, f"{XENC}aes256-cbc": 32}
AES_GCM = {f"{XENC11}aes128-gcm": 16, f"{XENC11}aes192-gcm": 24, f"{XENC11}aes256-gcm": 32}
AES_BLOCK_BYTES = 16
GCM_NONCE_BYTES = 12

# What minisignxml can verify: a document carrying exactly one ds:Signature.
SINGLE_SIGNATURE = 1


def _cipher_value(element: etree._Element) -> bytes:
    """Read and base64-decode a CipherData/CipherValue (it is line-wrapped)."""
    value = element.find(f"./{{{XENC}}}CipherData/{{{XENC}}}CipherValue")
    if value is None or not value.text:
        msg = "The encrypted assertion has no CipherValue"
        raise ValueError(msg)
    return base64.b64decode("".join(value.text.split()))


def _unwrap_session_key(encrypted_key: etree._Element, private_key: object) -> bytes:
    """RSA-unwrap the AES session key the assertion was encrypted with.

    Args:
        encrypted_key (Element): The xenc:EncryptedKey element.
        private_key: Our SP private key.

    Returns:
        bytes: The session key.

    Raises:
        ValueError: For an unsupported key-transport algorithm, or when the key
            was wrapped for a different SP key.
    """
    method = encrypted_key.find(f"./{{{XENC}}}EncryptionMethod")
    algorithm = method.get("Algorithm") if method is not None else None

    if algorithm == RSA_OAEP_MGF1P:
        # fixed SHA-1 digest and MGF1-SHA1 by definition
        digest, mgf_digest = hashes.SHA1, hashes.SHA1
    elif algorithm == RSA_OAEP:
        digest_element = method.find(f"./{{{DS}}}DigestMethod")
        mgf_element = method.find(f"./{{{XENC11}}}MGF")
        digest = DIGESTS.get(digest_element.get("Algorithm") if digest_element is not None else "", hashes.SHA1)
        mgf_digest = MGF_DIGESTS.get(mgf_element.get("Algorithm") if mgf_element is not None else "", hashes.SHA1)
    else:
        msg = f"Unsupported key transport algorithm '{algorithm}'. The identity provider must use RSA-OAEP."
        raise ValueError(msg)

    try:
        return private_key.decrypt(
            _cipher_value(encrypted_key),
            padding.OAEP(mgf=padding.MGF1(algorithm=mgf_digest()), algorithm=digest(), label=None),
        )
    except Exception as ex:
        msg = "The session key could not be unwrapped - the assertion was encrypted for a different service provider key"
        raise ValueError(msg) from ex


def _decrypt_data(encrypted_data: etree._Element, session_key: bytes) -> bytes:
    """Decrypt the AES-encrypted assertion.

    Args:
        encrypted_data (Element): The xenc:EncryptedData element.
        session_key (bytes): The unwrapped session key.

    Returns:
        bytes: The plaintext assertion XML.

    Raises:
        ValueError: For an unsupported data-encryption algorithm or a key of the
            wrong length.
    """
    method = encrypted_data.find(f"./{{{XENC}}}EncryptionMethod")
    algorithm = method.get("Algorithm") if method is not None else None
    ciphertext = _cipher_value(encrypted_data)

    if algorithm in AES_GCM:
        expected = AES_GCM[algorithm]
        if len(session_key) != expected:
            msg = f"The session key is {len(session_key)} bytes, but {algorithm} needs {expected}"
            raise ValueError(msg)
        # IV || ciphertext || tag - and AESGCM wants the tag appended, which it already is
        nonce, body = ciphertext[:GCM_NONCE_BYTES], ciphertext[GCM_NONCE_BYTES:]
        return AESGCM(session_key).decrypt(nonce, body, None)

    if algorithm in AES_CBC:
        expected = AES_CBC[algorithm]
        if len(session_key) != expected:
            msg = f"The session key is {len(session_key)} bytes, but {algorithm} needs {expected}"
            raise ValueError(msg)
        iv, body = ciphertext[:AES_BLOCK_BYTES], ciphertext[AES_BLOCK_BYTES:]
        decryptor = Cipher(algorithms.AES(session_key), modes.CBC(iv)).decryptor()
        plaintext = decryptor.update(body) + decryptor.finalize()
        # ISO 10126: the last byte is the padding length, the padding bytes
        # themselves are random - so they must not be checked for a constant value
        if not plaintext:
            msg = "The decrypted assertion is empty"
            raise ValueError(msg)
        pad_length = plaintext[-1]
        if not 1 <= pad_length <= AES_BLOCK_BYTES or pad_length > len(plaintext):
            msg = "The decrypted assertion has invalid padding"
            raise ValueError(msg)
        return plaintext[:-pad_length]

    msg = f"Unsupported data encryption algorithm '{algorithm}'. Use AES-CBC or AES-GCM."
    raise ValueError(msg)


def decrypt_assertion(saml_response_xml: bytes, private_key: object) -> bytes | None:
    """Recover the assertion from an encrypted SAML response.

    Args:
        saml_response_xml (bytes): The SAML response document.
        private_key: Our SP private key.

    Returns:
        bytes | None: The plaintext (still signed) assertion, or None when the
            response is not encrypted - in which case the caller passes the
            original response through untouched.

    Raises:
        ValueError: When the response is encrypted but cannot be decrypted.
    """
    root = fromstring(saml_response_xml)
    encrypted_assertion = root.find(f".//{{{SAML}}}EncryptedAssertion")
    if encrypted_assertion is None:
        return None

    if private_key is None:
        msg = "The identity provider encrypted the assertion, but this service provider has no keypair configured"
        raise ValueError(msg)

    encrypted_data = encrypted_assertion.find(f"./{{{XENC}}}EncryptedData")
    if encrypted_data is None:
        msg = "The encrypted assertion has no EncryptedData"
        raise ValueError(msg)

    # The EncryptedKey sits either inside EncryptedData/KeyInfo (Shibboleth) or
    # as a sibling of EncryptedData (ADFS). Searching the whole subtree covers both.
    encrypted_key = encrypted_assertion.find(f".//{{{XENC}}}EncryptedKey")
    if encrypted_key is None:
        msg = "The encrypted assertion carries no EncryptedKey"
        raise ValueError(msg)

    session_key = _unwrap_session_key(encrypted_key, private_key)
    assertion_xml = _decrypt_data(encrypted_data, session_key)

    # what we hand back must be an Assertion - never trust the ciphertext to
    # have contained what the envelope claimed
    assertion = fromstring(assertion_xml)
    if assertion.tag != f"{{{SAML}}}Assertion":
        msg = f"The decrypted element is a '{etree.QName(assertion).localname}', not a SAML Assertion"
        raise ValueError(msg)
    return assertion_xml


def extract_signed_assertion(saml_response_xml: bytes) -> bytes | None:
    """Pull the signed Assertion out of a response that carries several signatures.

    An identity provider may sign the Response, the Assertion, or both - and
    signing both is a common default (Shibboleth, ADFS). ``minisignxml`` verifies
    a document with exactly one ``ds:Signature`` and refuses anything else, so a
    doubly-signed response is reduced to the Assertion: the signature that
    actually protects the identity claims we go on to trust.

    The Assertion is re-serialized as a standalone document. Its signature is
    computed over exclusive canonicalization (the only kind ``minisignxml``
    verifies), which ignores namespace declarations inherited from the Response,
    so lifting the subtree out does not disturb it.

    Args:
        saml_response_xml (bytes): The SAML response document.

    Returns:
        bytes | None: The signed assertion as a standalone document, or None when
            the response carries at most one signature - the caller then passes the
            response through and ``minisaml`` verifies it as it stands.
    """
    root = fromstring(saml_response_xml)
    if len(root.findall(f".//{{{DS}}}Signature")) <= SINGLE_SIGNATURE:
        return None

    assertion = root.find(f"./{{{SAML}}}Assertion")
    if assertion is None:
        return None

    # Reducing to an unsigned assertion would strip the document of every
    # signature; leave it alone and let minisignxml reject the response.
    if len(assertion.findall(f".//{{{DS}}}Signature")) != SINGLE_SIGNATURE:
        return None

    return etree.tostring(assertion)
