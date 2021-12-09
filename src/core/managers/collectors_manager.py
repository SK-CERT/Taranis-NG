from model.collector import Collector
from model.collectors_node import CollectorsNode
from model.osint_source import OSINTSource
from remote.collectors_api import CollectorsApi
from schema.collectors_node import CollectorsNode as CollectorNodeSchema


def add_collectors_node(data):
    node = CollectorNodeSchema.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info("")

    if status_code == 200:
        collectors = Collector.create_all(collectors_info)
        node = CollectorsNode.add_new(data, collectors)

        collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)

    return status_code


def update_collectors_node(node_id, data):
    node = CollectorNodeSchema.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)
    if status_code == 200:
        collectors = Collector.create_all(collectors_info)
        CollectorsNode.update(node_id, data, collectors)

    return status_code


def add_osint_source(data):
    osint_source = OSINTSource.add_new(data)
    refresh_collector(osint_source.collector)


def update_osint_source(osint_source_id, data):
    osint_source, default_group = OSINTSource.update(osint_source_id, data)
    refresh_collector(osint_source.collector)
    return osint_source, default_group


def delete_osint_source(osint_source_id):
    osint_source = OSINTSource.find(osint_source_id)
    collector = osint_source.collector
    OSINTSource.delete(osint_source_id)
    refresh_collector(collector)


def refresh_collector(collector):
    return CollectorsApi(collector.node.api_url, collector.node.api_key).refresh_collector(collector.type)
