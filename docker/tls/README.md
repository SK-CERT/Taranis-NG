# A directory for certificates and private keys

Mounted into Traefik as `/opt/certs`. Put PEM files here if you want to serve your
own certificates instead of getting them from ACME.

Traefik does **not** scan this directory - it has no such feature. Files here are
used only if something declares them. Two ways to do that:

## One certificate for everything (no files needed)

Configuration -> Application Settings -> Routing & TLS, "Default certificate":
paste the PEM chain and the private key. It is stored in the database (key
encrypted at rest), handed to Traefik directly, and served for every hostname with
no more specific match - the app and all public webs. Use a certificate whose SANs
cover them, or a wildcard.

## A certificate per hostname

Put the PEM pairs here, then add a gitignored file next to `fallback.yml`, e.g.
`docker/traefik/dynamic/certificates.yml`:

```yaml
tls:
  certificates:
    - certFile: /opt/certs/taranis.example.com.crt
      keyFile: /opt/certs/taranis.example.com.key
    - certFile: /opt/certs/cyberfeed.example.com.crt
      keyFile: /opt/certs/cyberfeed.example.com.key
```

Traefik matches these by SNI, so each hostname gets its own. Picked up within a
second, no restart. Do not put `tls.options` or `tls.stores` in that file - those
are not namespaced per provider, and a second definition breaks every router with
`unknown TLS options: default`.

## Either way

Clear `TRAEFIK_CERT_RESOLVER` in `.env`, and the per-web resolver in each web's
dialog. A router with a resolver set asks ACME for a certificate, which takes
precedence over anything configured here.

## Keeping the keys safe

Keep private keys out of version control and restrict their filesystem
permissions. Replacing a certificate does not alter application accounts,
satellite keys, presets, or other installation state.

The certificate must cover `TARANIS_NG_HOSTNAME`, and clients must trust its
issuer when HSTS is enabled. Merely placing a self-signed certificate here does
not make it trusted, and can make the site inaccessible after the browser has
cached the current one-year HSTS policy.
