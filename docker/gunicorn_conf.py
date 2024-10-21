"""This module contains the configuration settings for Gunicorn.

The following environment variables are used:
- WORKERS_PER_CORE: Number of workers per CPU core. Default is 2.
- WEB_CONCURRENCY: Number of worker processes. Default is 1.
- HOST: The host IP address to bind to. Default is 0.0.0.0.
- PORT: The port number to bind to. Default is 80.
- BIND: The bind address and port. If not provided, it will use the host and port values.
- MODULES_LOG_LEVEL: The log level. Default is 'WARNING'.

The module defines the following variables:
- loglevel: The log level to be used by Gunicorn.
- workers: The number of worker processes.
- bind: The bind address and port.
- keepalive: The keepalive timeout.
- errorlog: The error log file. '-' means stderr.

For debugging and testing purposes, the module also defines the following variables:
- log_data: A dictionary containing the log level, number of workers, bind address and port, workers per core, host, and port.
"""

from __future__ import print_function

import multiprocessing
import os

workers_per_core_str = os.getenv("WORKERS_PER_CORE", "2")
web_concurrency_str = os.getenv("WEB_CONCURRENCY", "1")
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "80")
bind_env = os.getenv("BIND", None)
use_loglevel = os.getenv("MODULES_LOG_LEVEL", "WARNING")
if bind_env:
    use_bind = bind_env
else:
    use_bind = f"{host}:{port}"

cores = multiprocessing.cpu_count()
workers_per_core = float(workers_per_core_str)
default_web_concurrency = workers_per_core * cores
if web_concurrency_str:
    web_concurrency = int(web_concurrency_str)
    assert web_concurrency > 0
else:
    web_concurrency = int(default_web_concurrency)

# Gunicorn config variables
loglevel = use_loglevel.lower()
workers = web_concurrency
bind = use_bind
keepalive = 120
errorlog = "-"

# For debugging and testing
log_data = {
    "loglevel": loglevel,
    "workers": workers,
    "bind": bind,
    # Additional, non-gunicorn variables
    "workers_per_core": workers_per_core,
    "host": host,
    "port": port,
}
if loglevel.lower() == "debug":
    print(log_data)
