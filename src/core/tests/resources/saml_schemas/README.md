# Vendored SAML 2.0 metadata XML Schemas

These XSDs are used by the test suite to validate SP metadata this service
generates against the official SAML 2.0 metadata schema.

Sources (unmodified content, see note below):

- `saml-schema-metadata-2.0.xsd`, `saml-schema-assertion-2.0.xsd` — OASIS SAML
  2.0 (https://docs.oasis-open.org/security/saml/v2.0/)
- `xmldsig-core-schema.xsd` — W3C XML-Signature Core (REC 2002-02-12)
- `xenc-schema.xsd` — W3C XML-Encryption (REC 2002-12-10)
- `xml.xsd` — W3C XML namespace schema

Only change from the originals: the `schemaLocation` of each cross-schema
`<import>` was rewritten from its absolute `http://…` URL to the sibling
filename here, so the schema set resolves **offline** (tests must not depend on
the network). The schema definitions themselves are untouched.
