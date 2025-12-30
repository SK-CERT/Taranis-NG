#!/usr/bin/env python

"""Module for managing the application from the command line."""
# from typing import TYPE_CHECKING

# if TYPE_CHECKING:
#     from flask.app import Flask

import random
import string
import time
from http import HTTPStatus
from os import abort, getenv, read
from pathlib import Path

import click
from flask import Flask
from flask.cli import FlaskGroup
from managers import db_manager
from managers.log_manager import logger
from model import (  # noqa: F401  Don't remove 'osint_source' and bot_preset reference otherwise relationship problems
    apikey,
    attribute,
    bot,
    bot_preset,
    bots_node,
    collector,
    collectors_node,
    osint_source,
    parameter,
    permission,
    role,
    user,
)
from remote.bots_api import BotsApi
from remote.collectors_api import CollectorsApi

from shared.config_bot import ConfigBot
from shared.config_collector import ConfigCollector


def create_app() -> Flask:
    """Create and configure the Flask application.

    This function initializes the Flask application, loads the configuration
    from the 'config.Config' class, and initializes the database manager.
    It also waits for the database to be ready before returning the app instance.

    Returns:
        Flask: The initialized Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object("config.Config")
    db_manager.initialize(app)
    db_manager.wait_for_db(app)

    @app.teardown_appcontext
    def shutdown_session(exception: BaseException | None) -> None:  # noqa: ARG001
        db_manager.db.session.remove()
        db_manager.db.engine.dispose()

    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli() -> None:
    """Command Line Interface (CLI) entry point for the application.

    This function does not implement any functionality.
    """


@cli.command()
@click.option("--list", "-l", "opt_list", is_flag=True)
@click.option("--create", "-c", "opt_create", is_flag=True)
@click.option("--edit", "-e", "opt_edit", is_flag=True)
@click.option("--delete", "-d", "opt_delete", is_flag=True)
@click.option("--username", "opt_username")
@click.option("--name", "opt_name", default="")
@click.option("--password", "opt_password")
@click.option("--roles", "opt_roles")
def account(
    opt_list: bool,
    opt_create: bool,
    opt_edit: bool,
    opt_delete: bool,
    opt_username: str,
    opt_name: str,
    opt_password: str,
    opt_roles: str,
) -> None:
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
        ordered_users = sorted(users, key=lambda x: x.id)
        for us in ordered_users:
            roles = [r.id for r in us.roles]
            logger.info(f"Id: {us.id}\n\tUsername: {us.username}\n\tName: {us.name}\n\tRoles: {roles}")

    if opt_create:
        if not opt_username or not opt_password or not opt_roles:
            logger.error("Username, password or role not specified!")
            abort()

        if user.User.find(opt_username):
            logger.warning("User already exists!")
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
                logger.error(f"The specified role '{ro}' does not exist!")
                abort()

            roles.append(r)

        new_user = user.User(-1, opt_username, opt_name, opt_password, None, roles, None)
        db_manager.db.session.add(new_user)
        db_manager.db.session.commit()

        logger.info(f"User '{opt_name}' with id {new_user.id} created.")

    if opt_edit:
        if not opt_username:
            logger.error("Username not specified!")
            abort()
        if not opt_password or not opt_roles:
            logger.error("Please specify a new password or role id!")
            abort()

        if not user.User.find(opt_username):
            logger.error("User does not exist!")
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
                    logger.error(f"The specified role '{ro}' does not exist!")
                    abort()

                roles.append(r)

    if opt_delete:
        if not opt_username:
            logger.error("Username not specified!")
            abort()

        u = user.User.find(opt_username)
        if not u:
            logger.error("User does not exist!")
            abort()

        user.User.delete(u.id)
        logger.info(f"The user '{opt_username}' has been deleted.")


@cli.command("role")
@click.option("--list", "-l", "opt_list", is_flag=True)
@click.option("--create", "-c", "opt_create", is_flag=True)
@click.option("--edit", "-e", "opt_edit", is_flag=True)
@click.option("--delete", "-d", "opt_delete", is_flag=True)
@click.option("--filter", "-f", "opt_filter")
@click.option("--id", "opt_id")
@click.option("--name", "opt_name")
@click.option("--description", "opt_description", default="")
@click.option("--permissions", "opt_permissions")
def role_management(
    opt_list: bool,
    opt_create: bool,
    opt_edit: bool,
    opt_delete: bool,
    opt_filter: str,
    opt_id: str,
    opt_name: str,
    opt_description: str,
    opt_permissions: str,
) -> None:
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
        roles = role.Role.get(opt_filter)[0] if opt_filter else role.Role.get_all()
        for ro in roles:
            perms = [p.id for p in ro.permissions]
            logger.info(f"Id: {ro.id}\n\tName: {ro.name}\n\tDescription: {ro.description}\n\tPermissions: {perms}")

    if opt_create:
        if not opt_name or not opt_permissions:
            logger.error("Role name or permissions not specified!")
            abort()

        opt_permissions = opt_permissions.split(",")
        perms = []

        for pe in opt_permissions:
            p = permission.Permission.find(pe)

            if not p:
                logger.error(f"The specified permission '{pe}' does not exist!")
                abort()

            perms.append(p)

        new_role = role.Role(-1, opt_name, opt_description, perms)
        db_manager.db.session.add(new_role)
        db_manager.db.session.commit()

        logger.info(f"Role '{opt_name}' with id {new_role.id} created.")

    if opt_edit:
        if not opt_id or not opt_name:
            logger.error("Role id or name not specified!")
            abort()
        if not opt_name or not opt_description or not opt_permissions:
            logger.error("Please specify a new name, description or permissions!")
            abort()

    if opt_delete and (not opt_id or not opt_name):
        logger.error("Role id or name not specified!")
        abort()


@cli.command("collector")
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
    opt_list: bool,
    opt_create: bool,
    opt_edit: bool,
    opt_delete: bool,
    opt_update: bool,
    opt_all: bool,
    opt_show_api_key: bool,
    opt_id: str,
    opt_name: str,
    opt_description: str,
    opt_api_url: str,
    opt_api_key: str,
) -> None:
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
                sources.extend(f"{s.name} ({s.id})" for s in c.sources)
            api_key_str = f"API key: {node.api_key}\n\t" if opt_show_api_key else ""
            logger.info(
                f"Id: {node.id}\n\tName: {node.name}\n\tURL: {node.api_url}\n\t{api_key_str}Created: {node.created}\n\t"
                f"Last seen: {node.last_seen}\n\tCapabilities: {capabilities}\n\tSources: {sources}",
            )
        # We need use print here, because the prestart_core.sh relies on the output
        print(f"Total: {len(collector_nodes)}")  # noqa: T201

    if opt_create:
        if not opt_name or not opt_api_url or not opt_api_key:
            logger.error("Please specify the collector node name, API url and key!")
            abort()

        if collectors_node.CollectorsNode.get_by_name(opt_name):
            logger.warning(f"Collector node '{opt_name}' already exists!")
            abort()

        node = collectors_node.CollectorsNode("", opt_name, opt_description, opt_api_url, opt_api_key)
        modules = ConfigCollector().modules
        for mod in modules:
            col = collector.Collector(mod.name, mod.description, mod.type, [])
            for par in mod.parameters:
                col.parameters.append(parameter.Parameter(par.key, par.name, par.description, par.type, par.default_value))
            node.collectors.append(col)

        db_manager.db.session.add(node)
        db_manager.db.session.commit()
        logger.info(f"Collector node '{opt_name}' created.")

        logger.debug("Trying to contact a new collector node...")
        attempt, retries, delay = 0, 5, 1
        while attempt < retries:
            try:
                collectors_info, status_code = CollectorsApi(opt_api_url, opt_api_key).get_collectors_info(node.id)
                break
            except Exception as error:
                attempt += 1
                logger.warning(f"Attempt ({attempt}/{retries}): {error}")
                status_code = 0
                if attempt != retries:  # don't wait last attempt
                    time.sleep(delay)
                delay *= 2

        if status_code == HTTPStatus.OK:
            logger.info(f"Collector node '{opt_name}' registered.")
        else:
            logger.error(
                "Unable to register a new collector node! Wait until the new Collector container starts and register it manually.\n"
                f"1) running 'python manage.py collector --update --name \"{opt_name}\"'\n"
                "2) from the Taranis configuration screen (just re-save the record)",
            )

    if opt_edit:
        if not opt_id or not opt_name:
            logger.error("Collector node id or name not specified!")
            abort()
        if not opt_name or not opt_description or not opt_api_url or not opt_api_key:
            logger.error("Please specify a new name, description, API url or key!")
            abort()

    if opt_delete and not opt_name:
        logger.error("Collector node id or name not specified!")
        abort()

    if opt_update:
        if not opt_all and not opt_id and not opt_name:
            logger.error("Collector node id or name not specified!\nIf you want to update all collectors, pass the --all parameter.")
            abort()

        nodes = None
        if opt_id:
            nodes = [collectors_node.CollectorsNode.get_by_id(opt_id)]
            if not nodes:
                logger.error(f"Collector node '{opt_id}' does not exit!")
                abort()
        elif opt_name:
            nodes, count = collectors_node.CollectorsNode.get(opt_name)
            if not count:
                logger.error(f"Collector node '{opt_name}' does not exit!")
                abort()
        else:
            nodes, count = collectors_node.CollectorsNode.get(None)
            if not count:
                logger.error("No collector nodes exist!")
                abort()

        for node in nodes:
            # refresh collector node id
            try:
                collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)
                if status_code == HTTPStatus.OK:
                    logger.info(f"Collector node '{node.name}' updated.")
                else:
                    logger.error(f"Unable to update collector node '{node.name}'.\n\tResponse: [{status_code}] {collectors_info}.")
            except Exception as ex:
                logger.exception(f"Unable to update collector node '{node.name}'\n{ex}")


@cli.command("bot")
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
def bot_management(
    opt_list: bool,
    opt_create: bool,
    opt_edit: bool,
    opt_delete: bool,
    opt_update: bool,
    opt_all: bool,
    opt_show_api_key: bool,
    opt_id: str,
    opt_name: str,
    opt_description: str,
    opt_api_url: str,
    opt_api_key: str,
) -> None:
    """Manage bots.

    Args:
        opt_list (bool): List all bots.
        opt_create (bool): Create a new bot.
        opt_edit (bool): Edit an existing bot.
        opt_delete (bool): Delete an existing bot.
        opt_update (bool): Update bots.
        opt_all (bool): Update all bots.
        opt_show_api_key (bool): Show API key in the output.
        opt_id (str): ID of the bot.
        opt_name (str): Name of the bot.
        opt_description (str): Description of the bot.
        opt_api_url (str): API URL of the bot.
        opt_api_key (str): API key of the bot.
    """
    if opt_list:
        bot_nodes = bots_node.BotsNode.get_all()

        for node in bot_nodes:
            capabilities = []
            presets = []
            for c in node.bots:
                capabilities.append(c.type)
                presets.extend(f"{s.name} ({s.id})" for s in c.presets)
            api_key_str = f"API key: {node.api_key}\n\t" if opt_show_api_key else ""
            logger.info(
                f"Id: {node.id}\n\tName: {node.name}\n\tURL: {node.api_url}\n\t{api_key_str}Created: {node.created}\n\t"
                f"Last seen: {node.last_seen}\n\tCapabilities: {capabilities}\n\tPresets: {presets}",
            )
        # We need use print here, because the prestart_core.sh relies on the output
        print(f"Total: {len(bot_nodes)}")  # noqa: T201

    if opt_create:
        if not opt_name or not opt_api_url or not opt_api_key:
            logger.error("Please specify the bot node name, API url and key!")
            abort()

        if bots_node.BotsNode.get_by_name(opt_name):
            logger.warning(f"Bot node '{opt_name}' already exists!")
            abort()

        node = bots_node.BotsNode(opt_id, opt_name, opt_description, opt_api_url, opt_api_key)
        modules = ConfigBot().modules
        for mod in modules:
            bott = bot.Bot(mod.name, mod.description, mod.type, [])
            for par in mod.parameters:
                bott.parameters.append(parameter.Parameter(par.key, par.name, par.description, par.type, par.default_value))
            node.bots.append(bott)

        db_manager.db.session.add(node)
        db_manager.db.session.commit()
        logger.info(f"Bot node '{opt_name}' created.")

        logger.debug("Trying to contact a new bot node...")
        attempt, retries, delay = 0, 5, 1
        while attempt < retries:
            try:
                bots_info, status_code = BotsApi(opt_api_url, opt_api_key).get_bots_info()
                break
            except Exception as error:
                attempt += 1
                logger.warning(f"Attempt ({attempt}/{retries}): {error}")
                status_code = 0
                if attempt != retries:  # don't wait last attempt
                    time.sleep(delay)
                delay *= 2

        if status_code == HTTPStatus.OK:
            logger.info(f"Bot node '{opt_name}' registered.")
        else:
            logger.error(
                "Unable to register a new bot node! Wait until the new Bot container starts and register it manually.\n"
                f"1) running 'python manage.py bot --update --name \"{opt_name}\"'\n"
                "2) from the Taranis configuration screen (just re-save the record)",
            )

    if opt_edit:
        if not opt_id or not opt_name:
            logger.error("Bot node id or name not specified!")
            abort()
        if not opt_name or not opt_description or not opt_api_url or not opt_api_key:
            logger.error("Please specify a new name, description, API url or key!")
            abort()

    if opt_delete and not opt_name:
        logger.error("Bot node id or name not specified!")
        abort()

    if opt_update:
        if not opt_all and not opt_id and not opt_name:
            logger.error("Bot node id or name not specified!\nIf you want to update all bots, pass the --all parameter.")
            abort()

        nodes = None
        if opt_id:
            nodes = [bots_node.BotsNode.get_by_id(opt_id)]
            if not nodes:
                logger.error(f"Bot node '{opt_id}' does not exit!")
                abort()
        elif opt_name:
            nodes, count = bots_node.BotsNode.get(opt_name)
            if not count:
                logger.error(f"Bot node '{opt_name}' does not exit!")
                abort()
        else:
            nodes, count = bots_node.BotsNode.get(None)
            if not count:
                logger.error("No bot nodes exist!")
                abort()

        for node in nodes:
            # refresh bot node id
            try:
                bots_info, status_code = BotsApi(node.api_url, node.api_key).get_bots_info(node.id)
                if status_code == HTTPStatus.OK:
                    logger.info(f"Bot node '{node.name}' updated.")
                else:
                    logger.error(f"Unable to update bot node '{node.name}'.\n\tResponse: [{status_code}] {bots_info}.")
            except Exception as error:
                logger.exception(f"Unable to update bot node '{node.name}'\n{error}")


@cli.command("dictionary")
@click.option("--upload-cve", "opt_cve", is_flag=True)
@click.option("--upload-cpe", "opt_cpe", is_flag=True)
@click.option("--upload-cwe", "opt_cwe", is_flag=True)
def dictionary_management(opt_cve: bool, opt_cpe: bool, opt_cwe: bool) -> None:
    """Manage the dictionaries by uploading and loading CVE, CPE and CWE files.

    Args:
        opt_cve (bool): Indicates whether to upload the CVE file and load the CVE dictionary.
        opt_cpe (bool): Indicates whether to upload the CPE file and load the CPE dictionary.
        opt_cwe (bool): Indicates whether to upload the CWE file and load the CWE dictionary.
    """
    if opt_cve:
        cve_update_file = getenv("CVE_UPDATE_FILE")
        if cve_update_file is None:
            logger.error("CVE_UPDATE_FILE is undefined")
            abort()

        upload_to(cve_update_file)
        try:
            attribute.Attribute.load_dictionaries("cve")
        except Exception as ex:
            logger.exception(f"File structure was not recognized: {ex}")
            abort()

    if opt_cpe:
        cpe_update_file = getenv("CPE_UPDATE_FILE")
        if cpe_update_file is None:
            logger.error("CPE_UPDATE_FILE is undefined")
            abort()

        upload_to(cpe_update_file)
        try:
            attribute.Attribute.load_dictionaries("cpe")
        except Exception as ex:
            logger.exception(f"File structure was not recognized: {ex}")
            abort()

    if opt_cwe:
        cwe_update_file = getenv("CWE_UPDATE_FILE")
        if cwe_update_file is None:
            logger.error("CWE_UPDATE_FILE is undefined")
            abort()

        upload_to(cwe_update_file)
        try:
            attribute.Attribute.load_dictionaries("cwe")
        except Exception as ex:
            logger.exception(f"File structure was not recognized: {ex}")
            abort()

    logger.info("Dictionary was uploaded.")


def upload_to(filename: str) -> None:
    """Upload a file to the specified filename.

    Args:
        filename (str): The name of the file to upload.
    """
    try:
        with Path(filename).open("wb") as out_file:
            while True:
                chunk = read(0, 131072)
                if not chunk:
                    break
                out_file.write(chunk)
    except Exception as ex:
        logger.exception(f"Upload failed: {ex}")
        abort()


@cli.command("apikey")
@click.option("--list", "-l", "opt_list", is_flag=True)
@click.option("--create", "-c", "opt_create", is_flag=True)
@click.option("--delete", "-d", "opt_delete", is_flag=True)
@click.option("--name", "-n", "opt_name")
@click.option("--user", "-u", "opt_user")
@click.option("--expires", "-e", "opt_expires")
def api_keys_management(opt_list: bool, opt_create: bool, opt_delete: bool, opt_name: str, opt_user: str, opt_expires: str) -> None:
    """Manage API keys.

    This function provides functionality to list, create, and delete API keys.

    Args:
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
            logger.info(
                f"Id: {k.id}\n\tName: {k.name}\n\tKey: {k.key}\n\tCreated: {k.created_at}\n\tUser id: {k.user_id}\n\tExpires: {k.expires_at}",
            )

    if opt_create:
        if not opt_name:
            logger.error("Name not specified!")
            abort()

        if apikey.ApiKey.find_by_name(opt_name):
            logger.error("Name already exists!")
            abort()

        if not opt_user:
            logger.error("User not specified!")
            abort()

        u = None
        if opt_user:
            u = user.User.find(opt_user)
            if not u:
                logger.error(f"The specified user '{opt_user}' does not exist!")
                abort()

        data = {
            # 'id': None,
            "name": opt_name,
            "key": "".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=40)),  # noqa: S311
            "user_id": u.id,
            "expires_at": opt_expires if opt_expires else None,
        }

        k = apikey.ApiKey.add_new(data)
        logger.info(f"ApiKey '{opt_name}' with id {k.id} created.")

    if opt_delete:
        if not opt_name:
            logger.error("Name not specified!")
            abort()

        k = apikey.ApiKey.find_by_name(opt_name)
        if not k:
            logger.error("Name not found!")
            abort()

        apikey.ApiKey.delete(k.id)
        logger.info(f"ApiKey '{opt_name}' has been deleted.")


if __name__ == "__main__":
    cli()
