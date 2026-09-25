# Security response headers for the GUI.
#
# In an include file because nginx does not inherit add_header into a location
# block that declares one of its own - and "location /assets/" and
# "location = /index.html" both set Cache-Control. Declaring these once at server
# level silently dropped them for exactly the requests that matter, so
# default.conf includes this file in those blocks as well.
#
# No Strict-Transport-Security here: Traefik sends it, from a middleware edited in
# the GUI. It terminates TLS and so knows whether the browser trusted the
# certificate; this container, on plain HTTP behind it, cannot.

add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Robots-Tag "noindex, nofollow, noarchive, nosnippet, noimageindex, notranslate" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Permissions-Policy "accelerometer=(), ambient-light-sensor=(),
 autoplay=(), battery=(), camera=(), cross-origin-isolated=(), display-capture=(),
 document-domain=(), encrypted-media=(), execution-while-not-rendered=(), execution-while-out-of-viewport=(),
 fullscreen=(), geolocation=(), gyroscope=(), keyboard-map=(), magnetometer=(), microphone=(), midi=(),
 navigation-override=(), payment=(), picture-in-picture=(), publickey-credentials-create=(self),
 publickey-credentials-get=(self), screen-wake-lock=(),
 sync-xhr=(), usb=(), web-share=(), xr-spatial-tracking=(), clipboard-read=(), clipboard-write=(), gamepad=(),
 speaker-selection=(), conversion-measurement=(), focus-without-user-activation=(), hid=(), idle-detection=(),
 interest-cohort=(), serial=(), sync-script=(), trust-token-redemption=(), window-placement=(), vertical-scroll=()" always;
add_header Referrer-Policy "strict-origin" always;
# Both external origins the GUI uses (fonts.googleapis.com, fonts.gstatic.com) send
# "cross-origin-resource-policy: cross-origin", so require-corp does not block them.
add_header Cross-Origin-Embedder-Policy "require-corp" always;
add_header Cross-Origin-Resource-Policy "same-origin" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
# blob: in img-src is required: the public-web dialog previews uploaded images
# through URL.createObjectURL (see components/config/public-web/NewPublicWeb.vue).
add_header Content-Security-Policy "default-src 'self'; font-src https://fonts.gstatic.com:443 'self';
 script-src 'self' 'unsafe-eval' 'unsafe-inline'; script-src-elem 'self' 'unsafe-inline';
 style-src-attr 'self' 'unsafe-inline'; style-src-elem https://fonts.googleapis.com:443 'self' 'unsafe-inline';
 img-src 'self' data: blob:;
 frame-ancestors 'self'; frame-src 'self'" always;
