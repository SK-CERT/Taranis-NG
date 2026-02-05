"""Remote API endpoints."""

from flask import request
from flask_restful import Resource
from managers.auth_manager import api_key_required
from model import news_item, report_item


class RemoteConnect(Resource):
    """Resource for handling remote connection.

    Methods:
        get(remote_node): Connects to the remote node.
    """

    @api_key_required("remote")
    def get(self, remote_node=None):
        """Connect to the remote node.

        Parameters:
            remote_node: The remote node to connect to.

        Returns:
            The result of the connection attempt.
        """
        return remote_node.connect()


class RemoteDisconnect(Resource):
    """Resource for handling remote disconnection.

    Methods:
        get(remote_node): Disconnects from the remote node.
    """

    @api_key_required("remote")
    def get(self, remote_node=None):
        """Disconnect from the remote node.

        Parameters:
            remote_node: The remote node to disconnect from.

        Returns:
            The result of the disconnection attempt.
        """
        return remote_node.disconnect()


class RemoteSyncNewsItems(Resource):
    """Resource for syncing news items with the remote node.

    Methods:
        get(remote_node): Retrieves news items for synchronization.
        put(remote_node): Updates the news items synchronization status.
    """

    @api_key_required("remote")
    def get(self, remote_node=None):
        """Retrieve news items for synchronization.

        Parameters:
            remote_node: The remote node to sync news items with.

        Returns:
            A dictionary containing the last sync time and the news items.
        """
        news_items, last_sync_time = news_item.NewsItemData.get_for_sync(remote_node.last_synced_news_items, remote_node.osint_sources)
        return {"last_sync_time": format(last_sync_time), "news_items": news_items}

    @api_key_required("remote")
    def put(self, remote_node=None):
        """Update the news items synchronization status.

        Parameters:
            remote_node: The remote node to update news items sync status.

        Returns:
            None
        """
        remote_node.update_news_items_sync(request.json)


class RemoteSyncReportItems(Resource):
    """Resource for syncing report items with the remote node.

    Methods:
        get(remote_node): Retrieves report items for synchronization.
        put(remote_node): Updates the report items synchronization status.
    """

    @api_key_required("remote")
    def get(self, remote_node=None):
        """Retrieve report items for synchronization.

        Parameters:
            remote_node: The remote node to sync report items with.

        Returns:
            A dictionary containing the last sync time and the report items.
        """
        report_items, last_sync_time = report_item.ReportItem.get_for_sync(
            remote_node.last_synced_report_items,
            remote_node.report_item_types,
        )
        return {"last_sync_time": format(last_sync_time), "report_items": report_items}

    @api_key_required("remote")
    def put(self, remote_node=None):
        """Update the report items synchronization status.

        Parameters:
            remote_node: The remote node to update report items sync status.

        Returns:
            None
        """
        remote_node.update_report_items_sync(request.json)


def initialize(api):
    """Initialize the API by adding resources for remote operations.

    Parameters:
        api: The Flask-Restful API object.
    """
    api.add_resource(RemoteConnect, "/api/v1/remote/connect")
    api.add_resource(RemoteDisconnect, "/api/v1/remote/disconnect")
    api.add_resource(RemoteSyncNewsItems, "/api/v1/remote/sync-news-items")
    api.add_resource(RemoteSyncReportItems, "/api/v1/remote/sync-report-items")
