"""Talking to the collector nodes: registering them, and driving the OSINT sources they collect."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from model.collector import Collector
from model.collectors_node import CollectorsNode
from model.osint_source import OSINTSource
from remote.collectors_api import CollectorsApi
from shared.schema.collectors_node import CollectorsNode as CollectorNodeSchema
from shared.schema.osint_source import OSINTSourceExportRoot, OSINTSourceExportRootSchema

if TYPE_CHECKING:
    from model.osint_source import OSINTSourceGroup


def add_collectors_node(data: dict) -> HTTPStatus:
    """Register a collectors node and the collectors it reports.

    Args:
        data (dict): The node as submitted from the GUI.

    Returns:
        (HTTPStatus): The status of asking the node what it can collect.
    """
    node = CollectorNodeSchema.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info("")

    if status_code == HTTPStatus.OK:
        collectors = Collector.create_all(collectors_info)
        node = CollectorsNode.add_new(data, collectors)

        collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)

    return status_code


def update_collectors_node(node_id: str, data: dict) -> HTTPStatus:
    """Update a collectors node and re-read the collectors it reports.

    Args:
        node_id (str): The node to update.
        data (dict): The node as submitted from the GUI.

    Returns:
        (HTTPStatus): The status of asking the node what it can collect.
    """
    node = CollectorNodeSchema.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)
    if status_code == HTTPStatus.OK:
        collectors = Collector.create_all(collectors_info)
        CollectorsNode.update(node_id, data, collectors)

    return status_code


def add_osint_source(data: dict) -> None:
    """Create an OSINT source and collect it once, so it is not empty until its first schedule.

    Args:
        data (dict): The source as submitted from the GUI.
    """
    osint_source = OSINTSource.add_new(data)
    # Reschedule without collecting everything, then collect just the source that was added.
    refresh_collector(osint_source.collector, collect_now=False)
    collect_osint_source(osint_source.id)


def update_osint_source(osint_source_id: str, data: dict) -> tuple[OSINTSource, OSINTSourceGroup]:
    """Update an OSINT source and reschedule its collector.

    Args:
        osint_source_id (str): The source to update.
        data (dict): The source as submitted from the GUI.

    Returns:
        (tuple): The updated source and the default group it was moved out of, if any.
    """
    osint_source, default_group = OSINTSource.update(osint_source_id, data)
    # Applying the edit does not require collecting every source of this type; the play button on
    # the source is how an operator asks for a collection.
    refresh_collector(osint_source.collector, collect_now=False)
    return osint_source, default_group


def delete_osint_source(osint_source_id: str) -> None:
    """Delete an OSINT source and drop it from its collector's schedule.

    Args:
        osint_source_id (str): The source to delete.
    """
    osint_source = OSINTSource.find(osint_source_id)
    collector = osint_source.collector
    OSINTSource.delete(osint_source_id)
    refresh_collector(collector, collect_now=False)


def refresh_collector(collector: Collector, *, collect_now: bool = True) -> HTTPStatus:
    """Ask a collector node to re-read its sources and rebuild their schedule.

    Args:
        collector (Collector): The collector to refresh.
        collect_now (bool): Whether the node should also collect every source straight away.

    Returns:
        (HTTPStatus): The node's response status.
    """
    api = CollectorsApi(collector.node.api_url, collector.node.api_key)
    return api.refresh_collector(collector.type, collect_now=collect_now)


def set_osint_source_enabled(osint_source_id: str, *, enabled: bool) -> tuple[dict, HTTPStatus]:
    """Switch a source on or off, and reschedule the collector so it takes effect.

    A run already in progress is not interrupted; there is no mechanism to cancel one.

    Args:
        osint_source_id (str): The source to switch.
        enabled (bool): Whether the collector should collect it.

    Returns:
        (tuple): Empty body and OK, or NOT_FOUND when the source does not exist.
    """
    osint_source = OSINTSource.find(osint_source_id)
    if not osint_source:
        return {"error": "OSINT source not found"}, HTTPStatus.NOT_FOUND

    OSINTSource.set_enabled(osint_source_id, enabled)
    # Reschedule only: a disabled source loses its job, an enabled one gets it back. Collecting
    # every source of the type just because one was switched is not what the operator asked for.
    refresh_collector(osint_source.collector, collect_now=False)
    return {}, HTTPStatus.OK


def collect_osint_source(osint_source_id: str) -> tuple[dict, HTTPStatus]:
    """Ask the collector node to collect one source now.

    The source is only marked as collecting once the node confirms it started a run: marking it
    beforehand would leave it stuck looking busy whenever the node refused.

    Args:
        osint_source_id (str): The source to collect.

    Returns:
        (tuple): The node's answer. ACCEPTED when a run started, CONFLICT when one was already
            in progress, BAD_REQUEST when the source is switched off.
    """
    osint_source = OSINTSource.find(osint_source_id)
    if not osint_source:
        return {"error": "OSINT source not found"}, HTTPStatus.NOT_FOUND
    if not osint_source.enabled:
        return {"error": "OSINT source is disabled"}, HTTPStatus.BAD_REQUEST

    collector = osint_source.collector
    body, status_code = CollectorsApi(collector.node.api_url, collector.node.api_key).collect_source(
        collector.type,
        osint_source_id,
    )
    if status_code == HTTPStatus.ACCEPTED:
        OSINTSource.mark_collection_started(osint_source_id)
    return body, status_code


def export_osint_sources(input_data: dict | None) -> bytes:
    """Serialize OSINT sources for download, without their proxy settings.

    Args:
        input_data (dict): Optionally a "selection" of source ids; everything when absent.

    Returns:
        (bytes): The export document.
    """
    osint_sources = OSINTSource.get_all()
    if input_data is not None and "selection" in input_data:
        data = [osint_source for osint_source in osint_sources if osint_source.id in input_data["selection"]]
    else:
        data = osint_sources

    schema = OSINTSourceExportRootSchema()
    export_data = schema.dump(OSINTSourceExportRoot(1, data))

    for osint_source in export_data["data"]:
        for parameter_value in osint_source["parameter_values"]:
            # A proxy is specific to the installation that exported it, and may carry credentials.
            if parameter_value["parameter"]["key"] == "PROXY_SERVER":
                parameter_value["value"] = ""

    return json.dumps(export_data).encode("utf-8")


def import_osint_sources(collectors_node_id: str, file: Any) -> None:  # noqa: ANN401
    """Create OSINT sources from an export document.

    Args:
        collectors_node_id (str): The node that will collect the imported sources.
        file: The uploaded export document.
    """
    collectors_node = CollectorsNode.get_by_id(collectors_node_id)

    file_data = file.read()
    json_data = json.loads(file_data.decode("utf8"))
    schema = OSINTSourceExportRootSchema()
    import_data = schema.load(json_data)

    collectors = set()
    for osint_source in import_data.data:
        collector = collectors_node.find_collector_by_type(osint_source.collector.type)
        if collector is not None:
            collectors.add(collector)
            OSINTSource.import_new(osint_source, collector)

    for collector in collectors:
        # An import of many sources would otherwise collect every one of them at once.
        refresh_collector(collector, collect_now=False)
