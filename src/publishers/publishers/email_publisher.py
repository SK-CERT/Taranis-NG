import datetime
import smtplib
from email.message import EmailMessage
from email.contentmanager import ContentManager
from base64 import b64decode
from M2Crypto import BIO, SMIME, X509
import gnupg
import ssl
import os
import ast
from managers import log_manager
import traceback
from .base_publisher import BasePublisher
from shared.schema.parameter import Parameter, ParameterType


class EMAILPublisher(BasePublisher):
    """_summary_.

    Arguments:
        BasePublisher -- _description_

    Returns:
        _description_
    """

    type = "EMAIL_PUBLISHER"
    name = "EMAIL Publisher"
    description = "Publisher for publishing by email"

    parameters = [
        Parameter(0, "SMTP_SERVER", "SMTP server", "SMTP server for sending emails", ParameterType.STRING),
        Parameter(0, "SMTP_SERVER_PORT", "SMTP server port", "SMTP server port for sending emails", ParameterType.STRING),
        Parameter(
            0, "SMTP_CONNECTION_ENCRYPTION", "SMTP connection encryption", "SMTP connection encryption (TLS/STARTTLS)", ParameterType.STRING
        ),
        Parameter(0, "EMAIL_USERNAME", "Email username", "Username for email account", ParameterType.STRING),
        Parameter(0, "EMAIL_PASSWORD", "Email password", "Password for email account", ParameterType.STRING),
        Parameter(0, "EMAIL_RECIPIENT", "Email recipient", "Email address of recipient", ParameterType.STRING),
        Parameter(0, "EMAIL_SUBJECT", "Email subject", "Text of email subject", ParameterType.STRING),
        Parameter(0, "EMAIL_MESSAGE", "Email message", "Text of email message", ParameterType.STRING),
        Parameter(0, "EMAIL_SMIME_SIGN", "S/MIME signature", "Do you want to use S/MIME signature (yes/no)?", ParameterType.STRING),
        Parameter(0, "EMAIL_SMIME_CERT", "S/MIME certificate", "Filename of the public key for S/MIME signature", ParameterType.STRING),
        Parameter(0, "EMAIL_SMIME_KEY", "S/MIME key", "Filename of the private key for S/MIME signature", ParameterType.STRING),
        Parameter(0, "EMAIL_SMIME_ENCRYPT", "S/MIME encryption", "Do you want use email S/MIME encryption (yes/no)", ParameterType.STRING),
        Parameter(0, "EMAIL_SMIME_ENCRYPT_CERT", "S/MIME encryption certificate", "Certificate for S/MIME encryption", ParameterType.STRING),
        Parameter(0, "EMAIL_PGP_SIGN", "PGP signature", "Do you want use email PGP signature (yes/no)?", ParameterType.STRING),
        Parameter(0, "EMAIL_PGP_PRIVATE_KEY", "PGP private key", "Filename of the private key for PGP signature", ParameterType.STRING),
        Parameter(0, "EMAIL_PGP_ENCRYPT", "PGP encryption", "Do you want use email PGP encryption (yes/no)?", ParameterType.STRING),
        Parameter(0, "EMAIL_PGP_PUBLIC_KEY", "PGP public key", "Filename of the public key for PGP encryption", ParameterType.STRING),

    ]

    parameters.extend(BasePublisher.parameters)

    def publish(self, publisher_input):
        """_summary_.

        Arguments:
            publisher_input -- _description_

        Returns:
            _description_
        """
        smtp_server = publisher_input.parameter_values_map["SMTP_SERVER"]
        smtp_server_port = publisher_input.parameter_values_map["SMTP_SERVER_PORT"]
        smtp_connection_encryption = publisher_input.parameter_values_map["SMTP_CONNECTION_ENCRYPTION"]
        email_user = publisher_input.parameter_values_map["EMAIL_USERNAME"]
        email_password = publisher_input.parameter_values_map["EMAIL_PASSWORD"]
        email_recipients = publisher_input.parameter_values_map["EMAIL_RECIPIENT"]
        email_subject = publisher_input.parameter_values_map["EMAIL_SUBJECT"]
        email_message = publisher_input.parameter_values_map["EMAIL_MESSAGE"]
        email_smime_sign = publisher_input.parameter_values_map["EMAIL_SMIME_SIGN"]
        smime_pem_cert = publisher_input.parameter_values_map["EMAIL_SMIME_CERT"]
        smime_pem_key = publisher_input.parameter_values_map["EMAIL_SMIME_KEY"]
        email_smime_encrypt = publisher_input.parameter_values_map["EMAIL_SMIME_ENCRYPT"]
        smime_pem_encrypt_cert = publisher_input.parameter_values_map["EMAIL_SMIME_ENCRYPT_CERT"]
        email_pgp_sign = publisher_input.parameter_values_map["EMAIL_PGP_SIGN"]
        pgp_private_key = publisher_input.parameter_values_map["EMAIL_PGP_PRIVATE_KEY"]
        email_pgp_encrypt = publisher_input.parameter_values_map["EMAIL_PGP_ENCRYPT"]
        pgp_public_key = publisher_input.parameter_values_map["EMAIL_PGP_PUBLIC_KEY"]
        # email_smime_password = publisher_input.parameter_values_map["EMAIL_SMIME_PASSWORD"]
        # email_smime_password = "5gc3E7yoGZJmppbdQp@RdcpZSTpE77EU"
        # email_pgp_password = "!uSYt7isrCV6yo#UNXT88*f%ygbLt$my"
        add_attachment = False
        now = datetime.datetime.now().strftime("%d-%m-%Y_%H:%M")
        if publisher_input.mime_type:
            attachment_mimetype = publisher_input.mime_type
            if "/" in attachment_mimetype:
                maintype, subtype = attachment_mimetype.split("/", 1)
                add_attachment = True
                if attachment_mimetype == "text/plain":
                    extension = "txt"
                else:
                    extension = subtype
        else:
            attachment_mimetype = None

        if publisher_input.data:
            if attachment_mimetype != "email":
                attachment_data = publisher_input.data[:]
            else:
                attachment_data = ast.literal_eval(publisher_input.data)
                email_subject = b64decode(attachment_data["subject"]).decode().replace("\n", "").replace("\r", "")
                email_message = b64decode(attachment_data["body"]).decode()
        else:
            attachment_data = None

        log_manager.log_critical("EMAIL SENDER LOADED")
        email_recipients = email_recipients.split(",")

        client_key_path = os.path.join("crypto", "tls.key")
        client_cert_path = os.path.join("crypto", "tls.crt")
        try:
            tls_context = ssl.create_default_context()
            tls_context.load_cert_chain(client_cert_path, keyfile=client_key_path)
            tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
        except Exception as error:
            BasePublisher.print_exception(self, error)
            tls_context = None

        # try:
        #     smime_p12_path = os.path.join("crypto", "usercert.p12")
        # except:
        #     log_manager.log_critical("No S/MIME PKS12 cert")
        #     smime_p12_path = None

        # Checks for S/MIME signature
        smime_pem_cert_path = os.path.join("crypto", smime_pem_cert)
        smime_pem_key_path = os.path.join("crypto", smime_pem_key)
        if email_smime_sign.lower() == "yes":
            if not os.path.exists(smime_pem_key_path):
                raise FileNotFoundError("S/MIME PEM private key is missing")
            elif not os.path.exists(smime_pem_cert_path):
                raise FileNotFoundError("S/MIME PEM certificate is missing")
            else:
                email_smime_sign = True
        else:
            email_smime_sign = False
            smime_pem_key_path = None
            smime_pem_cert_path = None

        # Checks for S/MIME encryption
        smime_pem_encrypt_cert_path = os.path.join("crypto", smime_pem_encrypt_cert)
        if email_smime_encrypt.lower() == "yes":
            if not os.path.exists(smime_pem_encrypt_cert_path):
                raise FileNotFoundError("S/MIME PEM certificate for encryption is missing")
            else:
                email_smime_encrypt = True
                smime_pem_encrypt_cert_path = [smime_pem_encrypt_cert_path]
        else:
            email_smime_encrypt = False
            smime_pem_encrypt_cert_path = None

        gpg = gnupg.GPG()
        gpg.encoding = "utf-8"
        if email_pgp_sign.lower() == "yes":
            pgp_private_key_path = os.path.join("crypto", pgp_private_key)
            try:
                with open(pgp_private_key_path, "r") as key_file:
                    log_manager.log_critical("OPENED PRIVATE PGP KEY")
                    key_data = key_file.read()
                    imported_key = gpg.import_keys(key_data)

                # Get the key fingerprint
                gpg_private_key_id = imported_key.fingerprints[0]
                log_manager.log_critical("GOT PRIVATE PGP KEY ID")
            except Exception as error:
                log_manager.log_critical("No PRIVATE PGP key")
                log_manager.log_critical(error)
                gpg_private_key_id = None
                email_pgp_sign = False
        else:
            email_pgp_sign = False

        if email_pgp_encrypt.lower() == "yes":
            pgp_public_key_path = os.path.join("crypto", pgp_public_key)
            try:
                with open(pgp_public_key_path, "r") as key_file:
                    log_manager.log_critical("OPENED PUBLIC KEY")
                    key_data = key_file.read()
                    imported_key = gpg.import_keys(key_data)

                # Get the key fingerprint
                gpg_public_key_id = imported_key.fingerprints[0]
                log_manager.log_critical("GOT PUBLIC PGP KEY ID")
            except:
                log_manager.log_critical("No PUBLIC PGP key")
                gpg_public_key_id = None
                email_pgp_encrypt = False
        else:
            email_pgp_encrypt = False

        def smime_sign_encrypt(from_addr, to_addrs, subject, msg, from_key, from_cert=None, to_certs=None):
            try:
                msg_bytes = msg.as_bytes()
                msg_bio = BIO.MemoryBuffer(msg_bytes)
                s = SMIME.SMIME()
                if from_key:
                    # if sign
                    s.load_key(from_key, from_cert)
                    if to_certs:
                        # if encrypt, sign the email
                        p7 = s.sign(msg_bio, flags=SMIME.PKCS7_TEXT)
                    else:
                        # sign the email with detached signature
                        p7 = s.sign(msg_bio, flags=SMIME.PKCS7_TEXT | SMIME.PKCS7_DETACHED)
                    msg_bio = BIO.MemoryBuffer(msg_bytes)  # Recreate because sign() has consumed it.

                if to_certs:
                    # if encrypt
                    sk = X509.X509_Stack()
                    for x in to_certs:
                        sk.push(X509.load_cert(x))
                    s.set_x509_stack(sk)
                    s.set_cipher(SMIME.Cipher("aes_256_cbc"))
                    tmp_bio = BIO.MemoryBuffer()
                    if from_key:
                        # if sign, write signed message to tmp_bio
                        s.write(tmp_bio, p7)
                    else:
                        # if w/o signature, write message to tmp_bio
                        tmp_bio.write(msg_bytes)
                    # encrypt message
                    p7 = s.encrypt(tmp_bio)
                out = BIO.MemoryBuffer()
                recipients = ", ".join(to_addrs)
                out.write(f"From: {from_addr}\r\n")
                out.write(f"To: {recipients}\r\n")
                out.write(f"Subject: {subject}\r\n")
                if to_certs:
                    s.write(out, p7)
                else:
                    if from_key:
                        s.write(out, p7, msg_bio)
                        out.close()
                    else:
                        out.write("\r\n")
                        out.write(msg_bytes)
                out.close()
                return out.read()
            except:
                log_manager.log_critical(traceback.format_exc())

        def sign_and_encrypt_message(from_addr, to_addrs, subject, msg, gpg, private_key=None, public_key=None):
            try:
                if private_key:
                    gpg.import_keys(private_key)
                    msg = gpg.sign(msg).data
                if public_key:
                    gpg.import_keys(public_key)
                    msg = gpg.encrypt(msg, to_addrs)
                return str(msg)
            except:
                log_manager.log_critical(traceback.format_exc())

        def get_server(connection_encryption, port, tls_context):
            """Connect and login to SMTP server.

            Arguments:
                connection_encryption -- TLS, STARTTLS or None
                tls_context -- TLS context
                port -- port used for connection

            Returns:
                smtplib.SMTP() or smtplib.SMTP_SSL() object
            """
            if connection_encryption == "TLS" and tls_context:
                server = smtplib.SMTP_SSL(smtp_server, port, context=tls_context)
                server.ehlo_or_helo_if_needed()

            else:
                server = smtplib.SMTP(smtp_server, port)
                server.ehlo_or_helo_if_needed()
                server.starttls(context=tls_context)
                server.ehlo_or_helo_if_needed()

            if email_user and email_password:
                server.login(email_user, email_password)

            return server

        def create_email(from_address, to_address, subject):
            """Create minimal email message.

            Arguments:
                from_address -- sender email address
                to_address -- recipient email address
                subject -- subject of the email

            Returns:
                EmailMessage() object
            """
            msg = EmailMessage()
            msg["From"] = from_address
            msg["To"] = ", ".join(to_address)
            msg["Subject"] = subject
            return msg

        try:
            msg = create_email(email_user, email_recipients, email_subject)
            msg.set_content(email_message)
            msg_str = msg.as_string()
            if add_attachment:
                # if email should have an attachment
                msg.add_attachment(b64decode(attachment_data), maintype=maintype, subtype=subtype, filename=f"file_{now}.{extension}")
                msg_str = msg.as_string()
            if email_smime_sign or email_smime_encrypt:
                # if email should be signed or encrypted by S/MIME
                log_manager.log_critical("GOING TO SIGN IT")
                msg_str = smime_sign_encrypt(
                    email_user, email_recipients, email_subject, msg, smime_pem_key_path, smime_pem_cert_path, smime_pem_encrypt_cert_path
                )
                log_manager.log_critical("SMIME SIGNED")
            elif email_pgp_sign or email_pgp_encrypt:
                log_manager.log_critical("GOING TO PGP SIGN IT")
                msg_str = sign_and_encrypt_message(
                    email_user, email_recipients, email_subject, msg, gpg, private_key=pgp_private_key, public_key=pgp_public_key_path
                )

            log_manager.log_critical(msg_str)
            server = get_server(smtp_connection_encryption, smtp_server_port, tls_context)
            log_manager.log_critical("CONNECTED TO SERVER")
            server.sendmail(email_user, email_recipients, msg_str)

            log_manager.log_critical("MESSAGE SENT")
            server.quit()

        # except Exception as error:
        #     BasePublisher.print_exception(self, error)
        except:
            log_manager.log_critical(traceback.format_exc())
