import os
import socket
import logging
import logging.handlers
import traceback


module_id = os.environ.get("MODULE_ID", None)
logger = None


def initialize(app):
    sys_log_handler = None
    if "SYSLOG_ADDRESS" in os.environ:
        try:
            syslog_address = os.getenv("SYSLOG_ADDRESS")
            syslog_port = int(os.getenv("SYSLOG_PORT"), 514)
            sys_log_handler = logging.handlers.SysLogHandler(
                address=(syslog_address, syslog_port), socktype=socket.SOCK_STREAM
            )
        except Exception as ex:
            log_debug("Unable to connect to syslog server!")
            log_debug(ex)

    for logger in (
        app.logger,
        logging.getLogger("gunicorn.error"),
        logging.getLogger("sqlalchemy"),
    ):
        logger.setLevel(logging.INFO)

        if os.environ.get("DEBUG", "false").lower() == "true":
            logger.setLevel(logging.DEBUG)

        if sys_log_handler:
            logger.addHandler(sys_log_handler)

    app.logger.handlers = logging.getLogger("gunicorn.error").handlers
    logger = app.logger


def log_debug(message):
    formatted_message = f"[{module_id}] {message}"
    logger.debug(formatted_message)


def log_debug_trace(message=None):
    formatted_message = f"[{module_id}] {message}"
    formatted_message_exc = f"[{module_id}] {traceback.format_exc()}"

    if message:
        logger.debug(formatted_message)
    logger.debug(formatted_message_exc)


def log_info(message):
    formatted_message = f"[{module_id}] {message}"
    logger.info(formatted_message)


def log_critical(message):
    formatted_message = f"[{module_id}] {message}"
    logger.critical(formatted_message)
