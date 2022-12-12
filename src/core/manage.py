#! /usr/bin/env python

from os import abort, getenv, read
import random
import socket
import string
import time
import logging
from flask import Flask
from flask_script import Manager,Command
from flask_script.commands import Option
import traceback

from managers import db_manager
from model import *
from model import apikey
from remote.collectors_api import CollectorsApi

app = Flask(__name__)
app.config.from_object('config.Config')
manager = Manager(app=app)
app.logger = logging.getLogger('gunicorn.error')
app.logger.level = logging.INFO

db_manager.initialize(app)

# wait for the database to be ready
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((app.config.get('DB_URL'), 5432))
        s.close()
        break
    except socket.error as ex:
        time.sleep(0.1)

# user account management
class AccountManagement(Command):

    option_list = (
        Option('--list', '-l', dest='opt_list', action='store_true'),
        Option('--create', '-c', dest='opt_create', action='store_true'),
        Option('--edit', '-e', dest='opt_edit', action='store_true'),
        Option('--delete', '-d', dest='opt_delete', action='store_true'),
        Option('--username', dest='opt_username'),
        Option('--name', dest='opt_name', default=""),
        Option('--password', dest='opt_password'),
        Option('--roles', dest='opt_roles'),
    )

    def run(self, opt_list, opt_create, opt_edit, opt_delete, opt_username, opt_name, opt_password, opt_roles):

        if (opt_list):
            users = user.User.get_all()
            for us in users:
                roles = []
                for r in us.roles:
                    roles.append(r.id)
                print('Id: {}\n\tUsername: {}\n\tName: {}\n\tRoles: {}'.format(us.id, us.username, us.name, roles))
            exit()

        if (opt_create):
            if (not opt_username or not opt_password or not opt_roles):
                app.logger.critical("Username, password or role not specified!")
                abort()

            if user.User.find(opt_username):
                app.logger.critical("User already exists!")
                abort()

            opt_roles = opt_roles.split(',')
            roles = []

            for ro in opt_roles:
                r = None
                try:
                    r = role.Role.find(int(ro))
                except Exception:
                    r = role.Role.find_by_name(ro)

                if not r:
                    app.logger.critical("The specified role '{}' does not exist!".format(ro))
                    abort()

                roles.append(r)

        if (opt_edit):
            if (not opt_username):
                app.logger.critical("Username not specified!")
                abort()
            if (not opt_password or not opt_roles):
                app.logger.critical("Please specify a new password or role id!")
                abort()

            if not user.User.find(opt_username):
                app.logger.critical("User does not exist!")
                abort()

            if (opt_roles):
                opt_roles = opt_roles.split(',')
                roles = []

                for ro in opt_roles:
                    r = None
                    try:
                        r = role.Role.find(int(ro))
                    except Exception:
                        r = role.Role.find_by_name(ro)

                    if not r:
                        app.logger.critical("The specified role '{}' does not exist!".format(ro))
                        abort()

                    roles.append(r)

        if (opt_delete):
            if (not opt_username):
                app.logger.critical("Username not specified!")
                abort()

            u = user.User.find(opt_username)
            if not u:
                app.logger.critical("User does not exist!")
                abort()

            user.User.delete(u.id)
            print('The user \'{}\' has been deleted.'.format(opt_username))


# role management
class RoleManagement(Command):

    option_list = (
        Option('--list', '-l', dest='opt_list', action='store_true'),
        Option('--create', '-c', dest='opt_create', action='store_true'),
        Option('--edit', '-e', dest='opt_edit', action='store_true'),
        Option('--delete', '-d', dest='opt_delete', action='store_true'),
        Option('--filter', '-f', dest='opt_filter'),
        Option('--id', dest='opt_id'),
        Option('--name', dest='opt_name'),
        Option('--description', dest='opt_description', default=""),
        Option('--permissions', dest='opt_permissions'),
    )

    def run(self, opt_list, opt_create, opt_edit, opt_delete, opt_filter, opt_id, opt_name, opt_description, opt_permissions):

        if (opt_list):
            roles = None
            if (opt_filter):
                roles = role.Role.get(opt_filter)[0]
            else:
                roles = role.Role.get_all()

            for ro in roles:
                perms = []
                for p in ro.permissions:
                    perms.append(p.id)
                print('Id: {}\n\tName: {}\n\tDescription: {}\n\tPermissions: {}'.format(ro.id, ro.name, ro.description, perms))
            exit()

        if (opt_create):
            if (not opt_name or not opt_permissions):
                app.logger.critical("Role name or permissions not specified!")
                abort()

            opt_permissions = opt_permissions.split(',')
            perms = []

            for pe in opt_permissions:
                p = permission.Permission.find(pe)

                if not p:
                    app.logger.critical("The specified permission '{}' does not exist!".format(pe))
                    abort()

                perms.append(p)

            new_role = role.Role(-1, opt_name, opt_description, perms)
            db_manager.db.session.add(new_role)
            db_manager.db.session.commit()

            print('Role \'{}\' with id {} created.'.format(opt_name, new_role.id))

        if (opt_edit):
            if (not opt_id or not opt_name):
                app.logger.critical("Role id or name not specified!")
                abort()
            if (not opt_name or not opt_description or not opt_permissions):
                app.logger.critical("Please specify a new name, description or permissions!")
                abort()

        if (opt_delete):
            if (not opt_id or not opt_name):
                app.logger.critical("Role id or name not specified!")
                abort()

# collector management
class CollectorManagement(Command):

    option_list = (
        Option('--list', '-l', dest='opt_list', action='store_true'),
        Option('--create', '-c', dest='opt_create', action='store_true'),
        Option('--edit', '-e', dest='opt_edit', action='store_true'),
        Option('--delete', '-d', dest='opt_delete', action='store_true'),
        Option('--update', '-u', dest='opt_update', action='store_true'),
        Option('--all', '-a', dest='opt_all', action='store_true'),
        Option('--show-api-key', dest='opt_show_api_key', action='store_true'),
        Option('--id', dest='opt_id'),
        Option('--name', dest='opt_name'),
        Option('--description', dest='opt_description', default=""),
        Option('--api-url', dest='opt_api_url'),
        Option('--api-key', dest='opt_api_key'),
    )

    def run(self, opt_list, opt_create, opt_edit, opt_delete, opt_update, opt_all, opt_show_api_key, opt_id, opt_name, opt_description, opt_api_url, opt_api_key):
        if (opt_list):
            collector_nodes = collectors_node.CollectorsNode.get_all()

            for node in collector_nodes:
                capabilities = []
                sources = []
                for c in node.collectors:
                    capabilities.append(c.type)
                    for s in c.sources:
                        sources.append('{} ({})'.format(s.name, s.id))
                print('Id: {}\n\tName: {}\n\tURL: {}\n\t{}Created: {}\n\tLast seen: {}\n\tCapabilities: {}\n\tSources: {}'.format(node.id, node.name, node.api_url, 'API key: {}\n\t'.format(node.api_key) if opt_show_api_key else '', node.created, node.last_seen, capabilities, sources))
            exit()

        if (opt_create):
            if (not opt_name or not opt_api_url or not opt_api_key):
                app.logger.critical("Please specify the collector node name, API url and key!")
                abort()

            data = {
                'id': '',
                'name': opt_name,
                'description': opt_description if opt_description else '',
                'api_url': opt_api_url,
                'api_key': opt_api_key,
                'collectors': [],
                'status': '0'
            }

            print('Trying to contact a new collector node...')
            retries, max_retries = 0, 30
            while retries < max_retries:
                try:
                    collectors_info, status_code = CollectorsApi(opt_api_url, opt_api_key).get_collectors_info("")
                    break;
                except:
                    collectors_info = 'Collector unavailable'
                    status_code = 0
                    time.sleep(1)
                retries += 1
                print('Retrying [{}/{}]...'.format(retries, max_retries))


            if status_code != 200:
                print('Cannot create a new collector node!')
                print('Response from collector: {}'.format(collectors_info))
                abort()

            collectors = collector.Collector.create_all(collectors_info)
            node = collectors_node.CollectorsNode.add_new(data, collectors)
            collectors_info, status_code = CollectorsApi(opt_api_url, opt_api_key).get_collectors_info(node.id)

            print('Collector node \'{}\' with id {} created.'.format(opt_name, node.id))

        if (opt_edit):
            if (not opt_id or not opt_name):
                app.logger.critical("Collector node id or name not specified!")
                abort()
            if (not opt_name or not opt_description or not opt_api_url or not opt_api_key):
                app.logger.critical("Please specify a new name, description, API url or key!")
                abort()

        if (opt_delete):
            if (not opt_id or not opt_name):
                app.logger.critical("Collector node id or name not specified!")
                abort()

        if (opt_update):
            if (not opt_all and not opt_id and not opt_name):
                app.logger.critical("Collector node id or name not specified!")
                app.logger.critical("If you want to update all collectors, pass the --all parameter.")
                abort()

            nodes = None
            if opt_id:
                nodes = [ collectors_node.CollectorsNode.get_by_id(opt_id) ]
                if not nodes:
                    app.logger.critical("Collector node does not exit!")
                    abort()
            elif opt_name:
                nodes, count = collectors_node.CollectorsNode.get(opt_name)
                if not count:
                    app.logger.critical("Collector node does not exit!")
                    abort()
            else:
                nodes, count = collectors_node.CollectorsNode.get(None)
                if not count:
                    app.logger.critical("No collector nodes exist!")
                    abort()

            for node in nodes:
                # refresh collector node id
                collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)
                if status_code == 200:
                    print('Collector node {} updated.'.format(node.id))
                else:
                    print('Unable to update collector node {}.\n\tResponse: [{}] {}.'.format(node.id, status_code, collectors_info))


# dictionary management
class DictionaryManagement(Command):

    option_list = (
        Option('--upload-cve', dest='opt_cve', action='store_true'),
        Option('--upload-cpe', dest='opt_cpe', action='store_true'),
    )

    def run(self, opt_cve, opt_cpe):
        from model import attribute

        if (opt_cve):
            cve_update_file = getenv('CVE_UPDATE_FILE')
            if cve_update_file is None:
                app.logger.critical("CVE_UPDATE_FILE is undefined")
                abort()

            self.upload_to(cve_update_file)
            try:
                attribute.Attribute.load_dictionaries('cve')
            except Exception:
                app.logger.debug(traceback.format_exc())
                app.logger.critical("File structure was not recognized!")
                abort()

        if (opt_cpe):
            cpe_update_file = getenv('CPE_UPDATE_FILE')
            if cpe_update_file is None:
                app.logger.critical("CPE_UPDATE_FILE is undefined")
                abort()

            self.upload_to(cpe_update_file)
            try:
                attribute.Attribute.load_dictionaries('cpe')
            except Exception:
                app.logger.debug(traceback.format_exc())
                app.logger.critical("File structure was not recognized!")
                abort()

        app.logger.error("Dictionary was uploaded.")
        exit()

    def upload_to(self, filename):
        try:
            with open(filename, 'wb') as out_file:
                while True:
                    chunk = read(0, 131072)
                    if not chunk:
                        break
                    out_file.write(chunk)
        except Exception:
            app.logger.debug(traceback.format_exc())
            app.logger.critical("Upload failed!")
            abort()

# ApiKeys management
class ApiKeysManagement(Command):

    option_list = (
        Option('--list', '-l', dest='opt_list', action='store_true'),
        Option('--create', '-c', dest='opt_create', action='store_true'),
        Option('--delete', '-d', dest='opt_delete', action='store_true'),
        Option('--name', '-n', dest='opt_name'),
        Option('--user', '-u', dest='opt_user'),
        Option('--expires', '-e', dest='opt_expires')
    )


    def run(self, opt_list, opt_create, opt_delete, opt_name, opt_user, opt_expires):

        if (opt_list):
            apikeys = apikey.ApiKey.get_all()
            for k in apikeys:
                print('Id: {}\n\tName: {}\n\tKey: {}\n\tCreated: {}\n\tUser id: {}\n\tExpires: {}'.format(k.id, k.name, k.key, k.created_at, k.user_id, k.expires_at))
            exit()

        if (opt_create):
            if (not opt_name):
                app.logger.critical("Name not specified!")
                abort()

            if apikey.ApiKey.find_by_name(opt_name):
                app.logger.critical("Name already exists!")
                abort()

            if (not opt_user):
                app.logger.critical("User not specified!")
                abort()

            u = None
            if opt_user:
                u = user.User.find(opt_user)
                if not u:
                    app.logger.critical("The specified user '{}' does not exist!".format(opt_user))
                    abort()

            data = {
                #'id': None,
                'name': opt_name,
                'key': ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=40)),
                'user_id': u.id,
                'expires_at': opt_expires if opt_expires else None
            }

            k = apikey.ApiKey.add_new(data)
            print('ApiKey \'{}\' with id {} created.'.format(opt_name, k.id))

        if (opt_delete):
            if (not opt_name):
                app.logger.critical("Name not specified!")
                abort()

            k = apikey.ApiKey.find_by_name(opt_name)
            if not k:
                app.logger.critical("Name not found!")
                abort()

            apikey.ApiKey.delete(k.id)
            print('ApiKey \'{}\' was deleted.'.format(opt_name))


manager.add_command('account', AccountManagement)
manager.add_command('role', RoleManagement)
manager.add_command('collector', CollectorManagement)
manager.add_command('dictionary', DictionaryManagement)
manager.add_command('apikey', ApiKeysManagement)

if __name__ == '__main__':
    manager.run()
