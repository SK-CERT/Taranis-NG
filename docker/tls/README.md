# A directory for certificates and private keys

**Audience:** Docker deployment operators. This file describes certificate
placement only; see the [Docker deployment guide](../README.md#tls-modes) for
hostname, port, trust, HSTS, and evaluation-mode requirements.

If you wish to use Taranis NG with custom certificates, place them here in PEM format.
Traefik will pick them up automatically.

The names of the files should be in the form `www.example.com.crt` and `www.example.com.key`.

The certificate must cover `TARANIS_NG_HOSTNAME`, and clients must trust its
issuer when HSTS is enabled. Merely placing a self-signed certificate here does
not make it trusted and can make the site inaccessible after the browser caches
the current one-year HSTS policy.

Keep private keys out of version control and restrict their filesystem
permissions. Certificate replacement does not alter application accounts,
satellite keys, presets, or other installation state.
