import logging.handlers
import os
import re
import socket
import traceback
import hashlib
from logging import getLogger
from flask import request
from managers.db_manager import db
from model.log_record import LogRecord
from base64 import b64encode, b64decode
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes

# setup Flask logger
gunicorn_logger = getLogger('gunicorn.error')
gunicorn_logger.setLevel(logging.INFO)

# setup syslog logger
sys_logger = logging.getLogger('SysLogger')
sys_logger.setLevel(logging.INFO)

# custom module ID to append to log messages
if "MODULE_ID" in os.environ:
    module_id = os.environ.get("MODULE_ID")
else:
    module_id = None

# increase logging level
if "DEBUG" in os.environ and os.environ.get("DEBUG").lower() == "true":
    gunicorn_logger.setLevel(logging.DEBUG)
    sys_logger.setLevel(logging.DEBUG)



# alter the sensitive value for logging, based on LOG_SENSITIVE_DATA env variable:
#
# LOG_SENSITIVE_DATA=no (or undefined) - remove sensitive data
# LOG_SENSITIVE_DATA=encrypt:abcdefg - encrypt the sensitive data with supplied passphrase
# LOG_SENSITIVE_DATA=yes - log all data as-is
def sensitive_value(value):
    logging_mode = os.environ.get('LOG_SENSITIVE_DATA', 'no')
    if logging_mode.lower() == 'yes':
        return value
    elif logging_mode.startswith('encrypt:'):
        key = logging_mode.split(':')[1]
        salt = get_random_bytes(AES.block_size)
        private_key = hashlib.scrypt(key.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
        cipher_config = AES.new(private_key, AES.MODE_GCM)
        cipher_text, tag = cipher_config.encrypt_and_digest(bytes(value, 'utf-8'))
        encryptedDict = {
            'cipher_text': b64encode(cipher_text).decode('utf-8'),
            'salt': b64encode(salt).decode('utf-8'),
            'nonce': b64encode(cipher_config.nonce).decode('utf-8'),
            'tag': b64encode(tag).decode('utf-8'),
        }
        encryptedString = encryptedDict['cipher_text'] + '*' + encryptedDict['salt'] + '*' + encryptedDict['nonce'] + '*' + encryptedDict['tag']
        return encryptedString
    else:
        return '•••••'


# used to decrypt the encrypted secrets from the logs
# source: https://github.com/gdavid7/cryptocode/blob/main/cryptocode.py
# TODO: add a command line wrapper around this function
def decrypt(enc_dict, password):
    enc_dict = enc_dict.split('*')
    try:
        enc_dict = {
            'cipher_text': enc_dict[0],
            'salt': enc_dict[1],
            'nonce': enc_dict[2],
            'tag': enc_dict[3],
            }

        # decode the dictionary entries from base64
        salt = b64decode(enc_dict['salt'])
        cipher_text = b64decode(enc_dict['cipher_text'])
        nonce = b64decode(enc_dict['nonce'])
        tag = b64decode(enc_dict['tag'])

        # generate the private key from the password and salt
        private_key = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)

        # create the cipher config
        cipher = AES.new(private_key, AES.MODE_GCM, nonce=nonce)

        # decrypt the cipher text
        decrypted = cipher.decrypt_and_verify(cipher_text, tag)
    except:
        return False

    return decrypted.decode('UTF-8')

# prepare the "data" argument for logging: use request.body or supplied
# parameter, strip whitespace, truncate to 4k of text
def generate_escaped_data(request_data):
    if request_data is None:
        request_data = request.data

    if request_data is None:
        return ''

    data = str(request_data)[:4096]
    data = re.sub(r'\s+', ' ', data)
    data = re.sub(r'(^\s+)|(\s+$)', '', data)
    return data



# send a debug message
def log_debug(message):
    formatted_message = "[{}] {}".format(module_id,message)
    gunicorn_logger.debug(formatted_message)
    if sys_logger:
        sys_logger.debug(formatted_message)

# send a debug message
def log_debug_trace(message = None):
    formatted_message1 = "[{}] {}".format(module_id,message)
    formatted_message2 = "[{}] {}".format(module_id,traceback.format_exc())

    if message:
        gunicorn_logger.debug(formatted_message1)
    gunicorn_logger.debug(formatted_message2)
    if sys_logger:
        if message:
            sys_logger.debug(formatted_message1)
        sys_logger.debug(formatted_message2)

# send an info message
def log_info(message):
    formatted_message = "[{}] {}".format(module_id,message)
    gunicorn_logger.info(formatted_message)
    if sys_logger:
        sys_logger.info(formatted_message)

# send an warning message
def log_warning(message):
    formatted_message = "[{}] {}".format(module_id,message)
    gunicorn_logger.warning(formatted_message)
    if sys_logger:
        sys_logger.warning(formatted_message)

# send a critical message
def log_critical(message):
    formatted_message = "[{}] {}".format(module_id,message)
    gunicorn_logger.critical(formatted_message)
    if sys_logger:
        sys_logger.critical(formatted_message)

# try to connect syslog logger
if "SYSLOG_URL" in os.environ and "SYSLOG_PORT" in os.environ:
    try:
        sys_log_handler = logging.handlers.SysLogHandler(
            address=(os.environ["SYSLOG_URL"], int(os.environ["SYSLOG_PORT"])),
            socktype=socket.SOCK_STREAM)
        sys_logger.addHandler(sys_log_handler)
    except Exception as ex:
        sys_logger = None
        log_debug("Unable to connect to syslog server!")
        log_debug(ex)
elif "SYSLOG_ADDRESS" in os.environ:
    try:
        sys_log_handler = logging.handlers.SysLogHandler(address=os.environ["SYSLOG_ADDRESS"])
        sys_logger.addHandler(sys_log_handler)
    except Exception as ex:
        sys_logger = None
        log_debug("Unable to connect to syslog server!")
        log_debug(ex)


def resolve_ip_address():
    headers_list = request.headers.getlist("X-Forwarded-For")
    ip_address = headers_list[0] if headers_list else request.remote_addr
    return ip_address


def resolve_method():
    return request.method


def resolve_resource():
    fp_len = len(request.full_path)
    if request.full_path[fp_len - 1] == '?':
        return request.full_path[:fp_len - 1]
    else:
        return request.full_path


def store_activity(activity_type, activity_detail, request_data = None):
    LogRecord.store(resolve_ip_address(), None, None, None, None, module_id, activity_type, resolve_resource(),
                    activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_user_activity(user, activity_type, activity_detail, request_data = None):
    LogRecord.store(resolve_ip_address(), user.id, user.name, None, None, module_id, activity_type, resolve_resource(),
                    activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_access_error_activity(user, activity_detail, request_data = None):
    ip = resolve_ip_address()
    log_text = "TARANIS NG Access Error (IP: {}, User ID: {}, User Name: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        user.id,
        user.name,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data(request_data))

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    db.session.rollback()
    LogRecord.store(ip, user.id, user.name, None, None, module_id, "ACCESS_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_data_error_activity(user, activity_detail, request_data = None):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG Data Error (IP: {}, User ID: {}, User Name: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        user.id,
        user.name,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data(request_data))

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(ip, user.id, user.name, None, None, module_id, "DATA_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_data_error_activity_no_user(activity_detail, request_data = None):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG Public Access Data Error (IP: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data(request_data))

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(ip, None, None, None, None, module_id, "PUBLIC_ACCESS_DATA_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_auth_error_activity(activity_detail, request_data = None):
    db.session.rollback()
    log_text = "TARANIS NG Auth Error (Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data(request_data))

    if sys_logger is not None:
        try:
            sys_logger.error(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(resolve_ip_address(), None, None, None, None, module_id, "AUTH_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_user_auth_error_activity(user, activity_detail, request_data = None):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG Auth Critical (IP: {}, User ID: {}, User Name: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        user.id,
        user.name,
        resolve_method(),
        resolve_resource(),
        activity_detail, generate_escaped_data(request_data))
    if sys_logger is not None:
        try:
            sys_logger.error(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(ip, user.id, user.name, None, None, module_id, "AUTH_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_system_activity(system_id, system_name, activity_type, activity_detail, request_data = None):
    LogRecord.store(resolve_ip_address(), None, None, system_id, system_name, module_id, activity_type,
                    resolve_resource(), activity_detail, resolve_method(), generate_escaped_data(request_data))


def store_system_error_activity(system_id, system_name, activity_type, activity_detail, request_data = None):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG System Critical (System ID: {}, System Name: {}, Activity Type: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        system_id,
        system_name,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data(request_data))

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(resolve_ip_address(), None, None, system_id, system_name, module_id, activity_type,
                    resolve_resource(), activity_detail, resolve_method(), generate_escaped_data(request_data))
