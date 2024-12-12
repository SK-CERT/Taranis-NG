"""Module containing functions to log the activities of the core."""

import logging.handlers
import os
import re
from shared.log import TaranisLogger
import hashlib
from logging import getLogger
from flask import request
from managers.db_manager import db
from model.log_record import LogRecord
from base64 import b64encode, b64decode
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes


# setup logger level
taranis_logging_level_str = os.environ.get("TARANIS_LOG_LEVEL", "DEBUG")
modules_logging_level_str = os.environ.get("MODULES_LOG_LEVEL", "WARNING")

logger = TaranisLogger(taranis_logging_level_str, modules_logging_level_str, True, os.environ.get("SYSLOG_ADDRESS"))

logging_level = getattr(logging, taranis_logging_level_str.upper(), logging.INFO)
# setup Flask logger
gunicorn_logger = getLogger("gunicorn.error")
gunicorn_logger.setLevel(logging_level)

# setup syslog logger
sys_logger = logging.getLogger("SysLogger")
sys_logger.setLevel(logging_level)


# LOG_SENSITIVE_DATA=no (or undefined) - remove sensitive data
# LOG_SENSITIVE_DATA=encrypt:abcdefg - encrypt the sensitive data with supplied passphrase
# LOG_SENSITIVE_DATA=yes - log all data as-is
def sensitive_value(value):
    """Encrypt or mask sensitive data based on the logging mode.

    Args:
        value (str): The sensitive data to be encrypted or masked.
    Returns:
        (str): The encrypted string if logging mode is set to 'encrypt', the masked string if logging mode is set to 'no',
          or the original value if logging mode is set to 'yes'.
    """
    logging_mode = os.environ.get("LOG_SENSITIVE_DATA", "no")
    if logging_mode.lower() == "yes":
        return value
    elif logging_mode.startswith("encrypt:"):
        key = logging_mode.split(":")[1]
        salt = get_random_bytes(AES.block_size)
        private_key = hashlib.scrypt(key.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        cipher_config = AES.new(private_key, AES.MODE_GCM)
        cipher_text, tag = cipher_config.encrypt_and_digest(bytes(value, "utf-8"))
        encryptedDict = {
            "cipher_text": b64encode(cipher_text).decode("utf-8"),
            "salt": b64encode(salt).decode("utf-8"),
            "nonce": b64encode(cipher_config.nonce).decode("utf-8"),
            "tag": b64encode(tag).decode("utf-8"),
        }
        encryptedString = f"{encryptedDict['cipher_text']}*{encryptedDict['salt']}*{encryptedDict['nonce']}*{encryptedDict['tag']}"
        return encryptedString
    else:
        return "•••••"


# source: https://github.com/gdavid7/cryptocode/blob/main/cryptocode.py
# TODO: add a command line wrapper around this function
def decrypt(enc_dict, password):
    """Decrypt the given encrypted dictionary using the provided password.

    Args:
        enc_dict (str): The encrypted dictionary in the format "cipher_text*salt*nonce*tag".
        password (str): The password used to generate the private key.
    Returns:
        (str): The decrypted text.
    """
    enc_dict = enc_dict.split("*")
    try:
        enc_dict = {
            "cipher_text": enc_dict[0],
            "salt": enc_dict[1],
            "nonce": enc_dict[2],
            "tag": enc_dict[3],
        }

        # decode the dictionary entries from base64
        salt = b64decode(enc_dict["salt"])
        cipher_text = b64decode(enc_dict["cipher_text"])
        nonce = b64decode(enc_dict["nonce"])
        tag = b64decode(enc_dict["tag"])

        # generate the private key from the password and salt
        private_key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)

        # create the cipher config
        cipher = AES.new(private_key, AES.MODE_GCM, nonce=nonce)

        # decrypt the cipher text
        decrypted = cipher.decrypt_and_verify(cipher_text, tag)
    except:  # noqa: E722
        return False

    return decrypted.decode("UTF-8")


def generate_escaped_data(request_data):
    """Generate escaped data from the given request data.

    Prepare the "data" argument for logging: use request.body or supplied parameter, strip whitespace, truncate to 4k of text

    Args:
        request_data: The request data to generate escaped data from.
    Returns:
        data (str): The generated escaped data.
    """
    if request_data is None:
        request_data = request.data

    if request_data is None:
        return ""

    data = str(request_data)[:4096]
    data = re.sub(r"\s+", " ", data)
    data = re.sub(r"(^\s+)|(\s+$)", "", data)
    return data


def resolve_ip_address():
    """Resolve the IP address of the client making the request.

    Returns:
        ip_address (str): The IP address of the client.
    """
    headers_list = request.headers.getlist("X-Forwarded-For")
    ip_address = headers_list[0] if headers_list else request.remote_addr
    return ip_address


def resolve_method():
    """Return the HTTP method of the current request.

    Returns:
        (str): The HTTP method of the current request.
    """
    return request.method


def resolve_resource():
    """Resolve the resource path by removing any trailing question mark from the request's full path.

    Returns:
        (str): The resolved resource path.
    """
    fp_len = len(request.full_path)
    if request.full_path[fp_len - 1] == "?":
        return request.full_path[: fp_len - 1]
    else:
        return request.full_path


def store_activity(activity_type, activity_detail, request_data=None):
    """Store an activity record in the log.

    Args:
        activity_type (str): The type of activity.
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    LogRecord.store(
        resolve_ip_address(),
        None,
        None,
        None,
        None,
        None,
        activity_type,
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_user_activity(user, activity_type, activity_detail, request_data=None):
    """Store a user activity record in the log.

    Args:
        user (User): The user associated with the activity.
        activity_type (str): The type of activity.
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    LogRecord.store(
        resolve_ip_address(),
        user.id,
        user.name,
        None,
        None,
        None,
        activity_type,
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_access_error_activity(user, activity_detail, request_data=None):
    """Store an access error activity record in the log.

    Args:
        user (User): The user associated with the activity.
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    ip = resolve_ip_address()
    log_text = f"TARANIS NG Access Error (IP: {ip}, User ID: {user.id}, User Name: {user.name}, Method: {resolve_method()},"
    f" Resource: {resolve_resource()}, Activity Detail: {activity_detail}, Activity Data: {generate_escaped_data(request_data)})"
    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception() as ex:
            logger.debug(ex)

    print(log_text)
    db.session.rollback()
    LogRecord.store(
        ip,
        user.id,
        user.name,
        None,
        None,
        None,
        "ACCESS_ERROR",
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_data_error_activity(user, activity_detail, request_data=None):
    """Store a data error activity record in the log.

    Args:
        user (User): The user associated with the activity.
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = f"TARANIS NG Data Error (IP: {ip}, User ID: {user.id}, User Name: {user.name}, Method: {resolve_method()},"
    f" Resource: {resolve_resource()}, Activity Detail: {activity_detail}, Activity Data: {generate_escaped_data(request_data)})"

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception() as ex:
            logger.debug(ex)

    print(log_text)
    LogRecord.store(
        ip,
        user.id,
        user.name,
        None,
        None,
        None,
        "DATA_ERROR",
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_data_error_activity_no_user(activity_detail, request_data=None):
    """Store a data error activity record in the log without a user.

    Args:
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = f"TARANIS NG Public Access Data Error (IP: {ip}, Method: {resolve_method()}, Resource: {resolve_resource()},"
    f" Activity Detail: {activity_detail}, Activity Data: {generate_escaped_data(request_data)})"
    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception() as ex:
            logger.debug(ex)

    print(log_text)
    LogRecord.store(
        ip,
        None,
        None,
        None,
        None,
        None,
        "PUBLIC_ACCESS_DATA_ERROR",
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_auth_error_activity(activity_detail, request_data=None):
    """Store an authentication error activity record in the log.

    Args:
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    db.session.rollback()
    log_text = f"TARANIS NG Auth Error (Method: {resolve_method()}, Resource: {resolve_resource()}, Activity Detail: {activity_detail},"
    f" Activity Data: {generate_escaped_data(request_data)})"
    if sys_logger is not None:
        try:
            sys_logger.error(log_text)
        except Exception() as ex:
            logger.debug(ex)

    print(log_text)
    LogRecord.store(
        resolve_ip_address(),
        None,
        None,
        None,
        None,
        None,
        "AUTH_ERROR",
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_user_auth_error_activity(user, activity_detail, request_data=None):
    """Store a user authentication error activity record in the log.

    Args:
        user (User): The user associated with the activity.
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = f"TARANIS NG Auth Critical (IP: {ip}, User ID: {user.id}, User Name: {user.name}, Method: {resolve_method()},"
    f" Resource: {resolve_resource()}, Activity Detail: {activity_detail}, Activity Data: {generate_escaped_data(request_data)})"
    if sys_logger is not None:
        try:
            sys_logger.error(log_text)
        except Exception() as ex:
            logger.debug(ex)

    print(log_text)
    LogRecord.store(
        ip,
        user.id,
        user.name,
        None,
        None,
        None,
        "AUTH_ERROR",
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_system_activity(system_id, system_name, activity_type, activity_detail, request_data=None):
    """Store a system activity record in the log.

    Args:
        system_id (int): The ID of the system.
        system_name (str): The name of the system.
        activity_type (str): The type of activity.
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    LogRecord.store(
        resolve_ip_address(),
        None,
        None,
        system_id,
        system_name,
        None,
        activity_type,
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )


def store_system_error_activity(system_id, system_name, activity_type, activity_detail, request_data=None):
    """Store a system error activity record in the log.

    Args:
        system_id (int): The ID of the system.
        system_name (str): The name of the system.
        activity_type (str): The type of activity.
        activity_detail (str): The details of the activity.
        request_data (dict, optional): The data associated with the request.
    """
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = f"TARANIS NG System Critical (System ID: {ip}, System Name: {system_id}, Activity Type: {system_name},"
    f" Method: {resolve_method()}, Resource: {resolve_resource()}, Activity Detail: {activity_detail},"
    f" Activity Data: {generate_escaped_data(request_data)})"
    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception() as ex:
            logger.debug(ex)

    print(log_text)
    LogRecord.store(
        resolve_ip_address(),
        None,
        None,
        system_id,
        system_name,
        None,
        activity_type,
        resolve_resource(),
        activity_detail,
        resolve_method(),
        generate_escaped_data(request_data),
    )
