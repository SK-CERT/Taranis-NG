EMAIL_PUBLISHER:
Test for gmail.com
Parameters:
SMTP_SERVER:		        smtp.gmail.com
SMTP_SERVER_PORT:           465
EMAIL_USERNAME:		        jakuboviejanko2@gmail.com
EMAIL_PASSWORD:		        tara2020nis
EMAIL_RECIPIENT:	        addr1, addr2
EMAIL_SUBJECT:
EMAIL_MESSAGE:
EMAIL_ENCRYPTION:           yes/no

Using email encryption:
- if email_encryption is set to YES, email will be send encrypted,
- it is necessary to install gnupgp on the computer in order to create a sender's private and public key,
- in home directory, there will be created new subdirectory .gnupg, after generating the keys (pgp --gen-key),
- the private key and public key will be store in this directory,
- the encryption is done by the sender's private key and the recipient's public key, so each email must be encrypted separately. For this reason, sender has to have the public key from every recipient,
- the decryption is done on recipient side by recipient's private key and sender's public key. Every recipient has to have sender's public key to decrypt email.




TWITTER_PUBLISHER:
API_KEY:			        uQKMfhfPSzQXTylLIRNVbw8zR
API_KEY_SECRET :		    AzlDY3mnYJtrPVQ0P7vhatxAPBDgVB2WeEdQnAN4DpJQQSa50Z
ACCESS_TOKEN:		        1237764183980204038-Fspeu8qsmOHb9qdqoic9Pg57CK1fDa
ACCESS_TOKEN_SECRET:	    bIOdBPexdDrJBeNJoR7mhCAjHXcSOz12cZQV2qrMXGfk6

Twitter account:
username:                   ferkokubicek@gmail.com
heslo:                      taranis-ng



WORDPRESS_PUBLISHER:
WP_URL:
WP_USER:
WP_PYTHON_APP_SECRET:



FTP_PUBLISHER:
FTP_URL:



MISP_PUBLISHER:
MISP_URL:
MISP_API_KEY:
