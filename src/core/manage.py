#! /usr/bin/env python

"""Module for managing the application from the command line."""

import os
import random
import socket
import string
import time

# import logging
from flask import Flask
from flask_script import Manager, Command
from flask_script.commands import Option
import traceback

from managers import db_manager
from model import user, role, collector, collectors_node, permission, osint_source  # noqa: F401
from model import apikey
from remote.collectors_api import CollectorsApi
from shared.log import TaranisLogger


app = Flask(__name__)
app.config.from_object("config.Config")
manager = Manager(app=app)
logging_level_str = os.environ.get("LOG_LEVEL", "INFO")
logger = TaranisLogger(logging_level_str, True, True, os.environ.get("SYSLOG_ADDRESS"))

db_manager.initialize(app)

# wait for the database to be ready
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((app.config.get("DB_URL"), 5432))
        s.close()
        break
    except socket.error:
        time.sleep(0.1)


class AccountManagement(Command):
    """Manage user accounts.

    Arguments:
        Command -- _description_
    """

    option_list = (
        Option("--list", "-l", dest="opt_list", action="store_true"),
        Option("--create", "-c", dest="opt_create", action="store_true"),
        Option("--edit", "-e", dest="opt_edit", action="store_true"),
        Option("--delete", "-d", dest="opt_delete", action="store_true"),
        Option("--username", dest="opt_username"),
        Option("--name", dest="opt_name", default=""),
        Option("--password", dest="opt_password"),
        Option("--roles", dest="opt_roles"),
    )

    def run(self, opt_list, opt_create, opt_edit, opt_delete, opt_username, opt_name, opt_password, opt_roles):
        """Run the command.

        Arguments:
            opt_list -- list all user accounts
            opt_create -- create a new user account
            opt_edit -- edit an existing user account
            opt_delete -- delete a user account
            opt_username -- specify the username
            opt_name -- specify the user's name
            opt_password -- specify the user's password
            opt_roles -- specify a list of roles, divided by a comma (,), that the user belongs to
        """
        if opt_list:
            users = user.User.get_all()
            for us in users:
                roles = []
                for r in us.roles:
                    roles.append(r.id)
                print(f"Id: {us.id}\n\tUsername: {us.username}\n\tName: {us.name}\n\tRoles: {roles}")
            exit()

        if opt_create:
            if not opt_username or not opt_password or not opt_roles:
                logger.critical("Username, password or role not specified!")
                os.abort()

            if user.User.find(opt_username):
                logger.critical("User already exists!")
                os.abort()

            opt_roles = opt_roles.split(",")
            roles = []
            for ro in opt_roles:
                r = None
                try:
                    r = role.Role.find(int(ro))
                except Exception:
                    r = role.Role.find_by_name(ro)

                if not r:
                    logger.critical(f"The specified role '{ro}' does not exist!")
                    os.abort()

                roles.append(r)

            new_user = user.User(-1, opt_username, opt_name, opt_password, None, roles, None)
            db_manager.db.session.add(new_user)
            db_manager.db.session.commit()

            print(f"User '{opt_name}' with id {new_user.id} created.")

        if opt_edit:
            if not opt_username:
                logger.critical("Username not specified!")
                os.abort()
            if not opt_password or not opt_roles:
                logger.critical("Please specify a new password or role id!")
                os.abort()

            if not user.User.find(opt_username):
                logger.critical("User does not exist!")
                os.abort()

            if opt_roles:
                opt_roles = opt_roles.split(",")
                roles = []

                for ro in opt_roles:
                    r = None
                    try:
                        r = role.Role.find(int(ro))
                    except Exception:
                        r = role.Role.find_by_name(ro)

                    if not r:
                        logger.critical(f"The specified role '{ro}' does not exist!")
                        os.abort()

                    roles.append(r)

        if opt_delete:
            if not opt_username:
                logger.critical("Username not specified!")
                os.abort()

            u = user.User.find(opt_username)
            if not u:
                logger.critical("User does not exist!")
                os.abort()

            user.User.delete(u.id)
            print(f"The user '{opt_username}' has been deleted.")


class RoleManagement(Command):
    """Manage user roles.

    Arguments:
        Command -- _description_
    """

    option_list = (
        Option("--list", "-l", dest="opt_list", action="store_true"),
        Option("--create", "-c", dest="opt_create", action="store_true"),
        Option("--edit", "-e", dest="opt_edit", action="store_true"),
        Option("--delete", "-d", dest="opt_delete", action="store_true"),
        Option("--filter", "-f", dest="opt_filter"),
        Option("--id", dest="opt_id"),
        Option("--name", dest="opt_name"),
        Option("--description", dest="opt_description", default=""),
        Option("--permissions", dest="opt_permissions"),
    )

    def run(self, opt_list, opt_create, opt_edit, opt_delete, opt_filter, opt_id, opt_name, opt_description, opt_permissions):
        """Run the command.

        Arguments:
            opt_list -- list all roles
            opt_create -- create a new role
            opt_edit -- edit an existing role
            opt_delete -- delete a role
            opt_filter -- filter roles by their name or description
            opt_id -- specify the role id (in combination with --edit or --delete)
            opt_name -- specify the role name
            opt_description -- specify the role description (default is "")
            opt_permissions -- specify a list of permissions, divided with a comma (,), that the role would allow
        """
        if opt_list:
            roles = None
            if opt_filter:
                roles = role.Role.get(opt_filter)[0]
            else:
                roles = role.Role.get_all()

            for ro in roles:
                perms = []
                for p in ro.permissions:
                    perms.append(p.id)
                print(f"Id: {ro.id}\n\tName: {ro.name}\n\tDescription: {ro.description}\n\tPermissions: {perms}")
            exit()

        if opt_create:
            if not opt_name or not opt_permissions:
                logger.critical("Role name or permissions not specified!")
                os.abort()

            opt_permissions = opt_permissions.split(",")
            perms = []

            for pe in opt_permissions:
                p = permission.Permission.find(pe)

                if not p:
                    logger.critical(f"The specified permission '{pe}' does not exist!")
                    os.abort()

                perms.append(p)

            new_role = role.Role(-1, opt_name, opt_description, perms)
            db_manager.db.session.add(new_role)
            db_manager.db.session.commit()

            print(f"Role '{opt_name}' with id {new_role.id} created.")

        if opt_edit:
            if not opt_id or not opt_name:
                logger.critical("Role id or name not specified!")
                os.abort()
            if not opt_name or not opt_description or not opt_permissions:
                logger.critical("Please specify a new name, description or permissions!")
                os.abort()

        if opt_delete:
            if not opt_id or not opt_name:
                logger.critical("Role id or name not specified!")
                os.abort()


class CollectorManagement(Command):
    """Manage collector nodes.

    Arguments:
        Command -- _description_
    """

    option_list = (
        Option("--list", "-l", dest="opt_list", action="store_true"),
        Option("--create", "-c", dest="opt_create", action="store_true"),
        Option("--edit", "-e", dest="opt_edit", action="store_true"),
        Option("--delete", "-d", dest="opt_delete", action="store_true"),
        Option("--update", "-u", dest="opt_update", action="store_true"),
        Option("--all", "-a", dest="opt_all", action="store_true"),
        Option("--show-api-key", dest="opt_show_api_key", action="store_true"),
        Option("--id", dest="opt_id"),
        Option("--name", dest="opt_name"),
        Option("--description", dest="opt_description", default=""),
        Option("--api-url", dest="opt_api_url"),
        Option("--api-key", dest="opt_api_key"),
    )

    def run(
        self,
        opt_list,
        opt_create,
        opt_edit,
        opt_delete,
        opt_update,
        opt_all,
        opt_show_api_key,
        opt_id,
        opt_name,
        opt_description,
        opt_api_url,
        opt_api_key,
    ):
        """Run the command.

        Arguments:
            opt_list -- list all collector nodes
            opt_create -- create a new node
            opt_edit -- edit an existing node
            opt_delete -- delete a node
            opt_update -- re-initialize collector node
            opt_all -- update all collector nodes (in combination with --update)
            opt_show_api_key -- show API key in plaintext (in combination with --list)
            opt_id -- specify the node id (in combination with --edit, --delete or --update)
            opt_name -- specify the node name
            opt_description -- specify the collector description (default is "")
            opt_api_url -- specify the collector node API url
            opt_api_key -- specify the collector node API key
        """
        if opt_list:
            collector_nodes = collectors_node.CollectorsNode.get_all()

            for node in collector_nodes:
                capabilities = []
                sources = []
                for c in node.collectors:
                    capabilities.append(c.type)
                    for s in c.sources:
                        sources.append(f"{s.name} ({s.id})")
                if opt_show_api_key:
                    api_key_str = f"API key: {node.api_key}\n\t"
                else:
                    api_key_str = ""
                print(
                    f"Id: {node.id}\n\tName: {node.name}\n\tURL: {node.api_url}\n\t{api_key_str}Created: {node.created}\n\t"
                    f"Last seen: {node.last_seen}\n\tCapabilities: {capabilities}\n\tSources: {sources}"
                )
            exit()

        if opt_create:
            if not opt_name or not opt_api_url or not opt_api_key:
                logger.critical("Please specify the collector node name, API url and key!")
                os.abort()

            data = {
                "id": "",
                "name": opt_name,
                "description": opt_description if opt_description else "",
                "api_url": opt_api_url,
                "api_key": opt_api_key,
                "collectors": [],
                "status": "0",
            }

            print("Trying to contact a new collector node...")
            retries, max_retries = 0, 30
            while retries < max_retries:
                try:
                    collectors_info, status_code = CollectorsApi(opt_api_url, opt_api_key).get_collectors_info("")
                    break
                except:  # noqa: E722
                    collectors_info = "Collector unavailable"
                    status_code = 0
                    time.sleep(1)
                retries += 1
                print(f"Retrying [{retries}/{max_retries}]...")

            if status_code != 200:
                print("Cannot create a new collector node!")
                print(f"Response from collector: {collectors_info}")
                os.abort()

            collectors = collector.Collector.create_all(collectors_info)
            node = collectors_node.CollectorsNode.add_new(data, collectors)
            collectors_info, status_code = CollectorsApi(opt_api_url, opt_api_key).get_collectors_info(node.id)

            print(f"Collector node '{opt_name}' with id {node.id} created.")

        if opt_edit:
            if not opt_id or not opt_name:
                logger.critical("Collector node id or name not specified!")
                os.abort()
            if not opt_name or not opt_description or not opt_api_url or not opt_api_key:
                logger.critical("Please specify a new name, description, API url or key!")
                os.abort()

        if opt_delete:
            if not opt_id or not opt_name:
                logger.critical("Collector node id or name not specified!")
                os.abort()

        if opt_update:
            if not opt_all and not opt_id and not opt_name:
                logger.critical("Collector node id or name not specified!")
                logger.critical("If you want to update all collectors, pass the --all parameter.")
                os.abort()

            nodes = None
            if opt_id:
                nodes = [collectors_node.CollectorsNode.get_by_id(opt_id)]
                if not nodes:
                    logger.critical("Collector node does not exit!")
                    os.abort()
            elif opt_name:
                nodes, count = collectors_node.CollectorsNode.get(opt_name)
                if not count:
                    logger.critical("Collector node does not exit!")
                    os.abort()
            else:
                nodes, count = collectors_node.CollectorsNode.get(None)
                if not count:
                    logger.critical("No collector nodes exist!")
                    os.abort()

            for node in nodes:
                # refresh collector node id
                collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)
                if status_code == 200:
                    print(f"Collector node {node.id} updated.")
                else:
                    print(f"Unable to update collector node {node.id}.\n\tResponse: [{status_code}] {collectors_info}.")


class DictionaryManagement(Command):
    """Manage dictionaries.

    Arguments:
        Command -- _description_
    """

    option_list = (
        Option("--upload-cve", dest="opt_cve", action="store_true"),
        Option("--upload-cpe", dest="opt_cpe", action="store_true"),
        Option("--upload-cwe", dest="opt_cwe", action="store_true"),
    )

    def run(self, opt_cve, opt_cpe, opt_cwe):
        """Run the command.

        Arguments:
            opt_cve -- upload the CPE dictionary (expected on STDIN in XML format) to the path indicated by CPE_UPDATE_FILE environment
              variable, and update the database from that file.
            opt_cpe -- upload the CVE dictionary (expected on STDIN in XML format) to the path indicated by CVE_UPDATE_FILE environment
              variable, and update the database from that file.
            opt_cwe -- upload the CWE dictionary (expected on STDIN in XML format) to the path indicated by CWE_UPDATE_FILE environment
              variable, and update the database from that file.
        """
        from model import attribute

        if opt_cve:
            cve_update_file = os.getenv("CVE_UPDATE_FILE")
            if cve_update_file is None:
                logger.critical("CVE_UPDATE_FILE is undefined")
                os.abort()

            self.upload_to(cve_update_file)
            try:
                attribute.Attribute.load_dictionaries("cve")
            except Exception:
                logger.debug(traceback.format_exc())
                logger.critical("File structure was not recognized!")
                os.abort()

        if opt_cpe:
            cpe_update_file = os.getenv("CPE_UPDATE_FILE")
            if cpe_update_file is None:
                logger.critical("CPE_UPDATE_FILE is undefined")
                os.abort()

            self.upload_to(cpe_update_file)
            try:
                attribute.Attribute.load_dictionaries("cpe")
            except Exception:
                logger.debug(traceback.format_exc())
                logger.critical("File structure was not recognized!")
                os.abort()

        if opt_cwe:
            cwe_update_file = os.getenv("CWE_UPDATE_FILE")
            if cwe_update_file is None:
                logger.critical("CWE_UPDATE_FILE is undefined")
                os.abort()

            self.upload_to(cwe_update_file)
            try:
                attribute.Attribute.load_dictionaries("cwe")
            except Exception:
                logger.debug(traceback.format_exc())
                logger.critical("File structure was not recognized!")
                os.abort()

        logger.info("Dictionary was uploaded.")
        exit()

    def upload_to(self, filename):
        """Upload the file to the specified path.

        Arguments:
            filename -- path specified by the environment variable
        """
        try:
            with open(filename, "wb") as out_file:
                while True:
                    chunk = os.read(0, 131072)
                    if not chunk:
                        break
                    out_file.write(chunk)
        except Exception:
            logger.debug(traceback.format_exc())
            logger.critical("Upload failed!")
            os.abort()


class ApiKeysManagement(Command):
    """Manage API keys.

    Arguments:
        Command -- _description_
    """

    option_list = (
        Option("--list", "-l", dest="opt_list", action="store_true"),
        Option("--create", "-c", dest="opt_create", action="store_true"),
        Option("--delete", "-d", dest="opt_delete", action="store_true"),
        Option("--name", "-n", dest="opt_name"),
        Option("--user", "-u", dest="opt_user"),
        Option("--expires", "-e", dest="opt_expires"),
    )

    def run(self, opt_list, opt_create, opt_delete, opt_name, opt_user, opt_expires):
        """Run the command.

        Arguments:
            opt_list -- list all apikeys
            opt_create -- create a new apikey
            opt_delete -- delete a apikey
            opt_name -- specify the apikey name
            opt_user -- specify the user's name
            opt_expires -- specify the apikey expiration datetime
        """
        if opt_list:
            apikeys = apikey.ApiKey.get_all()
            for k in apikeys:
                print(
                    f"Id: {k.id}\n\tName: {k.name}\n\tKey: {k.key}\n\tCreated: {k.created_at}\n\tUser id: {k.user_id}\n\t"
                    f"Expires: {k.expires_at}"
                )
            exit()

        if opt_create:
            if not opt_name:
                logger.critical("Name not specified!")
                os.abort()

            if apikey.ApiKey.find_by_name(opt_name):
                logger.critical("Name already exists!")
                os.abort()

            if not opt_user:
                logger.critical("User not specified!")
                os.abort()

            u = None
            if opt_user:
                u = user.User.find(opt_user)
                if not u:
                    logger.critical(f"The specified user '{opt_user}' does not exist!")
                    os.abort()

            data = {
                # 'id': None,
                "name": opt_name,
                "key": "".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=40)),
                "user_id": u.id,
                "expires_at": opt_expires if opt_expires else None,
            }

            k = apikey.ApiKey.add_new(data)
            print(f"ApiKey '{opt_name}' with id {k.id} created.")

        if opt_delete:
            if not opt_name:
                logger.critical("Name not specified!")
                os.abort()

            k = apikey.ApiKey.find_by_name(opt_name)
            if not k:
                logger.critical("Name not found!")
                os.abort()

            apikey.ApiKey.delete(k.id)
            print(f"ApiKey '{opt_name}' has been deleted.")


manager.add_command("account", AccountManagement)
manager.add_command("role", RoleManagement)
manager.add_command("collector", CollectorManagement)
manager.add_command("dictionary", DictionaryManagement)
manager.add_command("apikey", ApiKeysManagement)

if __name__ == "__main__":
    manager.run()
