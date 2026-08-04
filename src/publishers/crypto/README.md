# Publisher signing and encryption material

Place publisher certificates and keys in this directory only when message
signing or encryption is configured.

- S/MIME signing accepts a PEM file containing the certificate and private key.
- S/MIME encryption uses the recipient certificate.
- OpenPGP signing uses an armored private key.
- OpenPGP encryption uses an armored recipient public key.

Configure encrypted signing-key passwords through Taranis NG configuration.
Never commit private keys or passwords. Restrict file permissions, mount only
the material required by the publisher, and define a rotation and backup
procedure appropriate for the deployment.
