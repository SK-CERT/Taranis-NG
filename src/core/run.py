#! /usr/bin/env python

# patch things
from gevent import monkey
monkey.patch_all()
from psycogreen import gevent as g
g.patch_psycopg()


from app import create_app

app = create_app()
