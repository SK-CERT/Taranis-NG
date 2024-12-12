#! /usr/bin/env python
"""
This script initializes and runs the application.

It performs the following steps:
1. Patches standard library modules to make them cooperative using `gevent.monkey.patch_all()`.
2. Imports the `create_app` function from the `app` module.
3. Creates an instance of the application by calling `create_app()`.

Modules:
    gevent.monkey: Provides the `patch_all` function to make the standard library cooperative.
    app: Contains the `create_app` function to initialize the application.

Functions:
    create_app: Initializes and returns an instance of the application.
"""

from gevent import monkey

monkey.patch_all()

from app import create_app  # noqa: E402

app = create_app()
