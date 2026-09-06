# Custom presenter templates

Place operator-managed presenter templates in this directory or mount them at
the corresponding container path. Use unique filenames so application updates
cannot collide with bundled templates.

Keep secrets out of templates and version control. Back up custom templates
before upgrading or replacing presenter storage.

Mail headers templates for the MESSAGE presenter belong here too. A headers template
must never emit a header the publisher owns - `To`, `Cc`, `Bcc`, `From`, `Subject`,
`Reply-To`, `Date`, `Message-ID`, `MIME-Version`, `Content-*` or the trace headers.
Those are refused with a warning rather than sent, because a `Bcc` header would add a
real recipient. See "Custom e-mail headers" in `docs/howto.md`.
