# Authentication in Taranis NG

Taranis NG supports **multiple simultaneous login methods** ("auth providers")
configured in the GUI under *Access Management → Login Methods* and stored in
the database. Any number of OpenID Connect, OAuth 2.0, SAML 2.0 and LDAP/Active
Directory providers can be enabled at the same time, next to local password
accounts. Passkeys (WebAuthn) are available on top of any of them - they are
user-owned credentials, switched on in *Access Management → Security*.

## Provider kinds

| Kind      | Login flow | Notes |
|-----------|------------|-------|
| `local`   | username + password form | passwords stored locally (werkzeug hash); at most one provider of this kind |
| `ldap`    | username + password form | direct bind via DN template, or search & bind with a service account |
| `oidc`    | browser redirect | discovery + JWKS-verified ID tokens (Authlib/PyJWT) |
| `oauth2`  | browser redirect | generic authorization-code flow + userinfo endpoint |
| `saml`    | browser redirect | SAML 2.0 web browser SSO (HTTP-Redirect request, HTTP-POST response) |

### LDAP CA certificate placement

Place the CA certificate used to validate the LDAP server in this directory and
name it `ldap_ca.pem`, or configure the current Core/Compose certificate path
explicitly. Keep private credentials out of this directory and out of version
control.

This is certificate placement only, not complete LDAP configuration. See the
current configuration source and Compose environment for the LDAP server and
base-DN settings. Placing the certificate does not configure user mapping,
rotate application passwords, or establish that LDAP login is working.

Provider secrets (OIDC/OAuth2 client secret, LDAP bind password) and TOTP
seeds are encrypted at rest with the `secrets_encryption_key` Docker secret
(fallback: `jwt_secret_key`). **Changing the encryption key requires
re-entering all provider secrets and re-enrolling TOTP.**

## Redirect URI (OIDC / OAuth 2.0)

Register this callback URL at your identity provider:

```
https://<your-host>/api/v1/auth/oauth/<provider_slug>/callback
```

The URL is derived from the incoming request (honoring the reverse proxy's
`X-Forwarded-*` headers); if that does not work in your deployment, set the
provider's *Redirect URI override* field explicitly.

## PKCE (OIDC / OAuth 2.0)

Per-provider *PKCE code challenge method* selector (RFC 7636):

- `none` (default) -- no PKCE. Do not select this for a new production
  provider.
- `SHA256 code challenge` (`S256`) -- a fresh random `code_verifier` is
  generated per login attempt, `code_challenge = BASE64URL(SHA256(verifier))`
  is sent on the authorization request, and the verifier is replayed on the
  token exchange. Required by IdPs that mandate PKCE for confidential clients.
- `plain` -- legacy compatibility only. It sends the verifier itself in the
  browser-visible authorization request. It can still protect against theft of
  only the returned authorization code, but not an observer that also sees the
  initial authorization request. The GUI shows a warning and requires explicit
  confirmation before saving it.

Use `S256` whenever the provider supports it; the Core never silently falls
back to `plain` or `none`. The verifier and nonce are stored
behind an opaque Redis transaction handle and the callback atomically consumes
that handle, so they are neither carried through the browser nor replayable.

## SAML 2.0

A SAML provider works in one of two modes: pointed at a **single identity
provider** (the default, described here), or connected to a whole **federation**
through a discovery service (see [Federation mode](#federation-mode-discovery-service--wayf)
below). The single-IdP setup comes first; everything in it about the SP keypair,
attribute mapping and returning-user identification applies to federation mode too.

Give the identity provider these two URLs (both are shown in the provider
dialog once the provider has been saved, since they contain its id):

```
metadata:  https://<your-host>/api/v1/auth/saml/<provider_id>/metadata
ACS:       https://<your-host>/api/v1/auth/saml/<provider_id>/acs
```

The metadata endpoint publishes what this SP can actually do, so a federation
or IdP admin can register it without hand-writing XML.

### Configuring the identity provider

Paste the IdP's **metadata URL (or the XML itself)** into the provider dialog
and press *Load*. Three fields are filled in from it:

- the **entityID**,
- the **SSO endpoint** with the HTTP-Redirect binding (the one this SP uses),
- every **signing certificate** - `use="signing"` key descriptors and those with
  no `use` at all. Keys marked `use="encryption"` are ignored: they cannot
  verify a signature, and we never encrypt. Several signing certificates are
  kept, so an IdP key rollover does not break logins.

Everything can still be typed by hand. The certificate field takes the bare
base64 block exactly as it appears in `<ds:X509Certificate>` - the PEM armor is
added for you - and an unparsable certificate is rejected when the provider is
saved rather than at the first login.

The remaining field is the **SP entityID** the IdP issues assertions for; the
metadata URL above is a good choice, since entityIDs are conventionally
resolvable.

### Encrypted assertions and the SP keypair

A federation typically requires the assertion to be **encrypted to the service
provider's public key**, and its registration form then asks for an *encryption
certificate*. That certificate is **ours**, not the IdP's.

Press *Generate keypair* in the provider dialog: the private key is stored
encrypted (in the provider's `secret` column) and never shown again, and the
certificate is published in our metadata as
`<md:KeyDescriptor use="encryption">` - which is exactly what such a form wants.
Paste that certificate into its *encryption certificate* field.

Leave a registration form's **signing certificate** field empty: we do not sign
AuthnRequests, and our metadata says so (`AuthnRequestsSigned="false"`).

The assertion itself must still be **signed** - the signature is what we verify,
so an assertion that decrypts but is unsigned is unusable. An IdP that signs only
the *Response* and encrypts the assertion is therefore not supported.

(Unencrypted responses have no such restriction: a signature on the Response
alone is verified as it stands.)

Rotating the SP keypair means re-registering the new certificate at the IdP;
until then it keeps encrypting to the old key and logins fail.

Responses are signature-verified and checked for issuer, audience and validity
window (2 minutes clock skew allowed). RelayState and discovery state are opaque,
one-time Redis transactions. The signed bearer confirmation must bind both its
`InResponseTo` and Recipient to the stored request and ACS URL; a signed Response
Destination must match when present. Verified Response and Assertion IDs are
claimed atomically until the assertion expires, and oversized or non-canonical
HTTP-POST responses are rejected before XML validation.

Deployments upgraded while a SAML browser round-trip is already in progress
must restart that login: older signed-JWT RelayState values are deliberately not
accepted by the opaque-state flow. Keep a provider disabled until its metadata,
certificate, ACS registration and representative login have been tested.

### Identifying a returning user

Set **Stable identifier attribute** (`external_id_attr`) to an assertion
attribute whose value never changes for a given person (a unique ID or a
principal name). It is what links the account across logins.

Leave it empty **only** if the IdP issues a *persistent* NameID, which is then
used instead. A *transient* NameID changes every session: with the attribute
unset, each login would look like a brand-new person. If the attribute is
configured but the assertion does not carry it, the login is rejected rather
than silently falling back to the NameID.

### What the identity provider must do

- **Attributes are matched by their SAML `Name`**, never by `FriendlyName`. With
  the URI name-format that means the OID (e.g. `urn:oid:0.9.2342.19200300.100.1.3`
  for mail), so configure the attribute fields with exactly the `Name` the IdP
  sends. Multi-valued attributes yield their first value.
- **Sign the Assertion, the Response, or both.** When both are signed, the
  *assertion's* signature is the one verified - it is what covers the identity
  claims - and the response is reduced to that assertion before validation.
- **RSA with SHA-256** and exclusive canonicalization; SHA-1 is refused. The
  signing certificate must be embedded in the signature's `KeyInfo`.
- **Encryption is supported, but only with RSA-OAEP** key transport and AES-CBC
  or AES-GCM data encryption. The legacy `rsa-1_5` is refused on purpose (it is
  the Bleichenbacher padding-oracle construction). Without an SP keypair we
  advertise no key, and the IdP should then send the assertion in clear.
- Several signing certificates can be configured (they are all tried), so an
  IdP certificate rollover does not break logins - re-import the metadata while
  both keys are published.

AuthnRequests are not signed, single logout is not supported, and IdP-initiated
SSO is not supported (the RelayState must be one this SP minted when the login
started).

### Service information in the metadata

A federation registration form validates the SP metadata and requires
human-readable service information in it: a **display name**, a
**description**, an **information URL**, an **organization** and a
**technical contact**. The provider dialog has optional fields for these under
*Service information*; each is emitted into the metadata only when set, and
the values a federation lists in several languages are published for each
(the same text). The entityID must also be an **`https://` URL** (most
federations require this, and an IdP's schema validator may otherwise reject
the metadata) - and it must stay stable, because the IdP registration is keyed
on it. It should therefore **not** include the login method's database ID:
moving or recreating the method changes that ID, which would force a new
registration. The SP's own metadata URL is the canonical choice, and also what
the provider dialog suggests:

```
https://<your-host>/api/v1/auth/saml/<provider_slug>/metadata
```

It carries the provider *slug* (a URL-safe identifier derived from the
provider name).

### Federation mode (discovery service / WAYF)

Instead of one identity provider, a SAML provider can join a whole **federation**
(e.g. eduGAIN, InCommon, DFN-AAI). Turn on *Connect to a federation
(discovery service)* in the provider dialog. The user is then sent to the
federation's **discovery service** - a WAYF, "Where Are You From" - to pick their
home institution, and the chosen IdP is resolved from the federation's signed
metadata, so no IdP is registered by hand.

The flow adds a discovery hop in front of the ordinary one:

```
login  ->  discovery service (user picks an institution)
       ->  AuthnRequest to the chosen IdP  ->  HTTP-POST response to the ACS
```

so a third URL joins the two above, likewise shown once the provider is saved:

```
discovery response:  https://<your-host>/api/v1/auth/saml/<provider_id>/disco
```

It is published in our metadata as an `<idpdisc:DiscoveryResponse>`, which is how
the discovery service validates the `return` address we hand it - registering the
metadata URL is enough. This follows the SAML Identity Provider Discovery Service
protocol, so it works with any federation's discovery service.

Federation mode replaces the single IdP's SSO URL and certificate with:

- **Discovery service (WAYF) URL** - where the user picks an IdP, e.g.
  `https://discovery.example.org/wayf`.
- **Federation metadata URL** - the signed aggregate, e.g.
  `https://metadata.example.org/entities/federation`.
- **Federation metadata signing certificate** - the **trust anchor** (below).

Everything else - the SP entityID, the attribute mapping, the SP keypair for
encrypted assertions - is shared with the single-IdP mode.

#### The trust anchor is everything

The federation metadata is fetched over the network, so it is trusted only after
its XML signature verifies against the certificate pinned in the *Federation
metadata signing certificate* field, and an identity provider is only ever
resolved from the **verified** document. An IdP that is not in the verified
metadata can never be used - neither to redirect the user to, nor to accept a
response from. Skipping that check would let anyone able to intercept the fetch
inject a rogue IdP and forge logins.

Obtain the trust anchor **out of band** from the federation operator - not from
the metadata itself - and cross-check its fingerprint against their published
value. A metadata-signing key rollover is handled by pasting the old and the new
certificate together (a PEM bundle). The same signature profile as for assertions
applies: exclusive canonicalization, an enveloped signature and SHA-256; a
federation that signs its metadata with SHA-1 or a different transform set is out
of scope.

The verified metadata is cached in memory and refreshed automatically. A newly
fetched document whose `validUntil` is malformed or expired is rejected, and a
stale cached document is never served after its signed `validUntil`. Press
*Verify federation* in the dialog to fetch and verify the metadata and report
how many identity providers it yields before saving.

#### Restricting the identity provider list (discovery filter)

By default the discovery service lists every IdP in the federation. The optional
**Discovery service parameters** field is appended to the discovery URL verbatim.
Many federations accept a `filter` (or similar) parameter here that restricts
the listed IdPs - obtain the value from the federation operator and paste it in
URL-ready:

```
filter=eyAgImFsbG93SG9zdGVsIjogdHJ1ZSB9
```

This is the only federation-specific setting; the field is an opaque pass-through,
so another federation's discovery parameters go in exactly the same place.

## User provisioning and identity linking

Each external identity (an OIDC `sub`, an LDAP DN) is linked to exactly one
local user account through the *Login identities* table in the user dialog.
**One user can hold identities at many providers** and log in through any of
them - this also allows converting a local account to OIDC (link the identity,
optionally remove the local password) and back.

What happens when an unknown identity logs in depends on the provider's
*Provisioning* setting:

- **Linked users only** (default): the login is rejected until an
  administrator links the identity to a user. Recommended for public IdPs.
- **Auto-create, admin approves**: a new user is created with the provider's
  organization and default roles in the *pending* state; login is blocked with
  "awaiting administrator approval" until an admin approves the user in
  *Access Management → Users*.
- **Auto-create active**: as above, but the user is active immediately
  (for trusted corporate IdPs).

An optional **allowed e-mail domains** filter further restricts auto-creation.
If the reported username collides with an existing account, the login is
rejected - an administrator resolves this by linking the identity to the
existing account.

Users can be **disabled** at any time; this blocks new logins and invalidates
existing sessions on their next request.

## Two-factor authentication and passkeys

- Any user can enroll **TOTP** (authenticator app) and register **passkeys**
  in the user menu under *Security*.
- **A factor the user enrolled is always demanded**, no matter which provider
  they signed in with. A second factor belongs to the user, not to the provider:
  skipping it for redirect logins would leave the external path weaker than the
  local one, and whoever held the account at the identity provider could pick
  that path to walk around it.
- **Four levels can require a second factor, and they are OR-ed** - whichever is
  strictest wins, and no level can relax another:

  | Level | Where |
  |-------|-------|
  | site | *Access Management → Security* |
  | organization | the organization dialog |
  | login method | the provider dialog |
  | user | the user dialog |

  A user caught by any of them and holding no factor sets one up at their next
  login, choosing between an authenticator app and - where the site accepts
  passkeys as a second factor - registering a passkey there and then. Registering
  it *is* the factor (the authenticator has just verified them), so the login
  completes without a further step. See `mfa_required()` in
  [auth_manager](../managers/auth_manager.py).
- A redirect login (OIDC/OAuth2/SAML) is mid-browser-redirect when the challenge
  is raised, so it cannot be answered with a JSON body. The core stores the
  result behind an opaque one-time redemption handle in an HttpOnly cookie; the
  GUI exchanges it through the same-origin redemption endpoint and then runs
  the same TOTP/passkey step a form login would have run.
- When passkey sign-in is enabled in *Access Management → Security*, the login
  page offers passwordless "Sign in with a passkey" (discoverable credentials).
  Whether a passkey may also satisfy the *second-factor* step is a separate
  switch in the same place. With it off, TOTP is the only accepted second factor,
  and a user who owns nothing but passkeys is sent through TOTP enrollment.
- Administrators can reset a user's MFA (*Reset MFA* in the user dialog) as a
  recovery path; `manage.py account` remains available for CLI recovery.
- WebAuthn requires a secure context: HTTPS, or plain HTTP only on localhost.
  The relying-party ID must match the site's domain.
- Passkeys are **not** an identity provider: they are credentials owned by
  users. The site-wide relying-party configuration (enable switch, rp_id,
  rp_name, allowed origins) lives in *Access Management → Security*, and the
  public `/auth/methods` endpoint reports it as a `passkey_enabled` flag rather
  than as a login method.

## Deprecated environment-based configuration

`TARANIS_NG_AUTHENTICATOR=keycloak|openid` (with the related `KEYCLOAK_*`/
`OIDC_*` variables) and the gui env variables
`VITE_APP_TARANIS_NG_LOGIN_URL`/`VITE_APP_TARANIS_NG_LOGOUT_URL` keep working
but are **deprecated** - prefer creating an OIDC provider in the GUI.
`TARANIS_NG_AUTHENTICATOR=password|ldap` is superseded by database providers:
the migration seeds an enabled "Local accounts" provider, and an LDAP provider
from `LDAP_SERVER`/`LDAP_BASE_DN` when `TARANIS_NG_AUTHENTICATOR=ldap` was set
(place the CA certificate for LDAP in this folder as `ldap_ca.pem` before the
migration, configure the current Core/Compose certificate path explicitly, or
paste it into the provider's *CA certificate* field afterwards).
