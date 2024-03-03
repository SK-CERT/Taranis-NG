#! /usr/bin/env python
"""This script is used to manage user accounts, roles, and collectors in the Taranis-NG application."""

from os import abort, getenv, read
import random
import socket
import string
import time
import logging
import click
from flask import Flask
import traceback

from managers import db_manager
from model import user, role, permission, collectors_node, collector
from model import apikey
from remote.collectors_api import CollectorsApi

app = Flask(__name__)
app.config.from_object("config.Config")
app.logger = logging.getLogger("gunicorn.error")
app.logger.level = logging.INFO

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


@app.cli.command("account")
@click.option("--list", "-l", "opt_list", is_flag=True)
@click.option("--create", "-c", "opt_create", is_flag=True)
@click.option("--edit", "-e", "opt_edit", is_flag=True)
@click.option("--delete", "-d", "opt_delete", is_flag=True)
@click.option("--username", "opt_username")
@click.option("--name", "opt_name", default="")
@click.option("--password", "opt_password")
@click.option("--roles", "opt_roles")
def account_management(opt_list, opt_create, opt_edit, opt_delete, opt_username, opt_name, opt_password, opt_roles):
    """Manage user accounts.

    Args:
        opt_list (bool): List all user accounts.
        opt_create (bool): Create a new user account.
        opt_edit (bool): Edit an existing user account.
        opt_delete (bool): Delete an existing user account.
        opt_username (str): Username of the user account.
        opt_name (str): Name of the user.
        opt_password (str): Password of the user account.
        opt_roles (str): Roles assigned to the user account.
    """
    if opt_list:
        users = user.User.get_all()
        for us in users:
            roles = []
            for r in us.roles:
                roles.append(r.id)
            print("Id: {}\n\tUsername: {}\n\tName: {}\n\tRoles: {}".format(us.id, us.username, us.name, roles))
        exit()

    if opt_create:
        if not opt_username or not opt_password or not opt_roles:
            app.logger.critical("Username, password or role not specified!")
            abort()

        if user.User.find(opt_username):
            app.logger.critical("User already exists!")
            abort()

        opt_roles = opt_roles.split(",")
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

        new_user = user.User(-1, opt_username, opt_name, opt_password, None, roles, None)
        db_manager.db.session.add(new_user)
        db_manager.db.session.commit()

        print("User '{}' with id {} created.".format(opt_name, new_user.id))

    if opt_edit:
        if not opt_username:
            app.logger.critical("Username not specified!")
            abort()
        if not opt_password or not opt_roles:
            app.logger.critical("Please specify a new password or role id!")
            abort()

        if not user.User.find(opt_username):
            app.logger.critical("User does not exist!")
            abort()

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
                    app.logger.critical("The specified role '{}' does not exist!".format(ro))
                    abort()

                roles.append(r)

    if opt_delete:
        if not opt_username:
            app.logger.critical("Username not specified!")
            abort()

        u = user.User.find(opt_username)
        if not u:
            app.logger.critical("User does not exist!")
            abort()

        user.User.delete(u.id)
        print("The user '{}' has been deleted.".format(opt_username))


@app.cli.command("role")
@click.option("--list", "-l", "opt_list", is_flag=True)
@click.option("--create", "-c", "opt_create", is_flag=True)
@click.option("--edit", "-e", "opt_edit", is_flag=True)
@click.option("--delete", "-d", "opt_delete", is_flag=True)
@click.option("--filter", "-f", "opt_filter")
@click.option("--id", "opt_id")
@click.option("--name", "opt_name")
@click.option("--description", "opt_description", default="")
@click.option("--permissions", "opt_permissions")
def role_management(opt_list, opt_create, opt_edit, opt_delete, opt_filter, opt_id, opt_name, opt_description, opt_permissions):
    """Manage roles.

    Args:
        opt_list (bool): List all roles.
        opt_create (bool): Create a new role.
        opt_edit (bool): Edit an existing role.
        opt_delete (bool): Delete an existing role.
        opt_filter (str): Filter roles by name.
        opt_id (str): ID of the role.
        opt_name (str): Name of the role.
        opt_description (str): Description of the role.
        opt_permissions (str): Permissions assigned to the role.
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
            print("Id: {}\n\tName: {}\n\tDescription: {}\n\tPermissions: {}".format(ro.id, ro.name, ro.description, perms))
        exit()

    if opt_create:
        if not opt_name or not opt_permissions:
            app.logger.critical("Role name or permissions not specified!")
            abort()

        opt_permissions = opt_permissions.split(",")
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

        print("Role '{}' with id {} created.".format(opt_name, new_role.id))

    if opt_edit:
        if not opt_id or not opt_name:
            app.logger.critical("Role id or name not specified!")
            abort()
        if not opt_name or not opt_description or not opt_permissions:
            app.logger.critical("Please specify a new name, description or permissions!")
            abort()

    if opt_delete:
        if not opt_id or not opt_name:
            app.logger.critical("Role id or name not specified!")
            abort()


@app.cli.command("collector")
@click.option("--list", "-l", "opt_list", is_flag=True)
@click.option("--create", "-c", "opt_create", is_flag=True)
@click.option("--edit", "-e", "opt_edit", is_flag=True)
@click.option("--delete", "-d", "opt_delete", is_flag=True)
@click.option("--update", "-u", "opt_update", is_flag=True)
@click.option("--all", "-a", "opt_all", is_flag=True)
@click.option("--show-api-key", "opt_show_api_key", is_flag=True)
@click.option("--id", "opt_id")
@click.option("--name", "opt_name")
@click.option("--description", "opt_description", default="")
@click.option("--api-url", "opt_api_url")
@click.option("--api-key", "opt_api_key")
def collector_management(
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
    """Manage collectors.

    Args:
        opt_list (bool): List all collectors.
        opt_create (bool): Create a new collector.
        opt_edit (bool): Edit an existing collector.
        opt_delete (bool): Delete an existing collector.
        opt_update (bool): Update collectors.
        opt_all (bool): Update all collectors.
        opt_show_api_key (bool): Show API key in the output.
        opt_id (str): ID of the collector.
        opt_name (str): Name of the collector.
        opt_description (str): Description of the collector.
        opt_api_url (str): API URL of the collector.
        opt_api_key (str): API key of the collector.
    """
    if opt_list:
        collector_nodes = collectors_node.CollectorsNode.get_all()

        for node in collector_nodes:
            capabilities = []
            sources = []
            for c in node.collectors:
                capabilities.append(c.type)
                for s in c.sources:
                    sources.append("{} ({})".format(s.name, s.id))
            print(
                "Id: {}\n\tName: {}\n\tURL: {}\n\t{}Created: {}\n\tLast seen: {}\n\tCapabilities: {}\n\tSources: {}".format(
                    node.id,
                    node.name,
                    node.api_url,
                    "API key: {}\n\t".format(node.api_key) if opt_show_api_key else "",
                    node.created,
                    node.last_seen,
                    capabilities,
                    sources,
                )
            )
        exit()

    if opt_create:
        if not opt_name or not opt_api_url or not opt_api_key:
            app.logger.critical("Please specify the collector node name, API url and key!")
            abort()

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
            print("Retrying [{}/{}]...".format(retries, max_retries))

        if status_code != 200:
            print("Cannot create a new collector node!")
            print("Response from collector: {}".format(collectors_info))
            abort()

        collectors = collector.Collector.create_all(collectors_info)
        node = collectors_node.CollectorsNode.add_new(data, collectors)
        collectors_info, status_code = CollectorsApi(opt_api_url, opt_api_key).get_collectors_info(node.id)

        print("Collector node '{}' with id {} created.".format(opt_name, node.id))

    if opt_edit:
        if not opt_id or not opt_name:
            app.logger.critical("Collector node id or name not specified!")
            abort()
        if not opt_name or not opt_description or not opt_api_url or not opt_api_key:
            app.logger.critical("Please specify a new name, description, API url or key!")
            abort()

    if opt_delete:
        if not opt_id or not opt_name:
            app.logger.critical("Collector node id or name not specified!")
            abort()

    if opt_update:
        if not opt_all and not opt_id and not opt_name:
            app.logger.critical("Collector node id or name not specified!")
            app.logger.critical("If you want to update all collectors, pass the --all parameter.")
            abort()

        nodes = None
        if opt_id:
            nodes = [collectors_node.CollectorsNode.get_by_id(opt_id)]
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
                print("Collector node {} updated.".format(node.id))
            else:
                print("Unable to update collector node {}.\n\tResponse: [{}] {}.".format(node.id, status_code, collectors_info))


@app.cli.command("dictionary")
@click.option("--upload-cve", is_flag=True)
@click.option("--upload-cpe", is_flag=True)
def dictionary_management(upload_cve, upload_cpe):
    """Manage the dictionaries by uploading and loading CVE and CPE files.

    This function uploads the CVE and CPE files and loads the dictionaries accordingly.
    If `upload_cve` is True, it uploads the CVE file and loads the CVE dictionary.
    If `upload_cpe` is True, it uploads the CPE file and loads the CPE dictionary.

    Arguments:
        upload_cve (bool): Indicates whether to upload the CVE file and load the CVE dictionary.
        upload_cpe (bool): Indicates whether to upload the CPE file and load the CPE dictionary.
    """
    from model import attribute

    if upload_cve:
        cve_update_file = getenv("CVE_UPDATE_FILE")
        if cve_update_file is None:
            app.logger.critical("CVE_UPDATE_FILE is undefined")
            abort()

        upload_to(cve_update_file)
        try:
            attribute.Attribute.load_dictionaries("cve")
        except Exception:
            app.logger.debug(traceback.format_exc())
            app.logger.critical("File structure was not recognized!")
            abort()

    if upload_cpe:
        cpe_update_file = getenv("CPE_UPDATE_FILE")
        if cpe_update_file is None:
            app.logger.critical("CPE_UPDATE_FILE is undefined")
            abort()

        upload_to(cpe_update_file)
        try:
            attribute.Attribute.load_dictionaries("cpe")
        except Exception:
            app.logger.debug(traceback.format_exc())
            app.logger.critical("File structure was not recognized!")
            abort()

    app.logger.error("Dictionary was uploaded.")
    exit()


def upload_to(filename):
    """Upload a file to the specified filename.

    Arguments:
        filename (str): The name of the file to upload.
    """
    try:
        with open(filename, "wb") as out_file:
            while True:
                chunk = read(0, 131072)
                if not chunk:
                    break
                out_file.write(chunk)
    except Exception:
        app.logger.debug(traceback.format_exc())
        app.logger.critical("Upload failed!")
        abort()


@app.cli.command("apikey")
@click.option("--list", "-l", "opt_list", is_flag=True)
@click.option("--create", "-c", "opt_create", is_flag=True)
@click.option("--delete", "-d", "opt_delete", is_flag=True)
@click.option("--name", "-n", "opt_name")
@click.option("--user", "-u", "opt_user")
@click.option("--expires", "-e", "opt_expires")
def api_keys_management(opt_list, opt_create, opt_delete, opt_name, opt_user, opt_expires):
    """Manage API keys.

    This function provides functionality to list, create, and delete API keys.

    Arguments:
        opt_list (bool): If True, list all existing API keys.
        opt_create (bool): If True, create a new API key.
        opt_delete (bool): If True, delete an existing API key.
        opt_name (str): The name of the API key.
        opt_user (str): The user associated with the API key.
        opt_expires (str): The expiration date of the API key.
    """
    if opt_list:
        apikeys = apikey.ApiKey.get_all()
        for k in apikeys:
            print(
                "Id: {}\n\tName: {}\n\tKey: {}\n\tCreated: {}\n\tUser id: {}\n\tExpires: {}".format(
                    k.id, k.name, k.key, k.created_at, k.user_id, k.expires_at
                )
            )
        exit()

    if opt_create:
        if not opt_name:
            app.logger.critical("Name not specified!")
            abort()

        if apikey.ApiKey.find_by_name(opt_name):
            app.logger.critical("Name already exists!")
            abort()

        if not opt_user:
            app.logger.critical("User not specified!")
            abort()

        u = None
        if opt_user:
            u = user.User.find(opt_user)
            if not u:
                app.logger.critical("The specified user '{}' does not exist!".format(opt_user))
                abort()

        data = {
            # 'id': None,
            "name": opt_name,
            "key": "".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=40)),
            "user_id": u.id,
            "expires_at": opt_expires if opt_expires else None,
        }

        k = apikey.ApiKey.add_new(data)
        print("ApiKey '{}' with id {} created.".format(opt_name, k.id))

    if opt_delete:
        if not opt_name:
            app.logger.critical("Name not specified!")
            abort()

        k = apikey.ApiKey.find_by_name(opt_name)
        if not k:
            app.logger.critical("Name not found!")
            abort()

        apikey.ApiKey.delete(k.id)
        print("ApiKey '{}' has been deleted.".format(opt_name))


if __name__ == "__main__":
    app.run()
