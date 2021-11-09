from flask import request
from flask_restful import Resource, reqparse

from managers import sse_manager
from managers.auth_manager import api_key_required
from model import osint_source, news_item, collectors_node


class OSINTSourcesForCollectors(Resource):

    @api_key_required
    def get(self, collector_id):
        parser = reqparse.RequestParser()
        parser.add_argument("api_key")
        parser.add_argument("collector_type")
        parameters = parser.parse_args()

        node = collectors_node.CollectorsNode.get_by_id(collector_id)
        if not node:
            return '', 404

        node.updateLastSeen()

        return osint_source.OSINTSource.get_all_for_collector_json(node, parameters.collector_type)


class AddNewsItems(Resource):

    @api_key_required
    def post(self):
        osint_source_ids = news_item.NewsItemAggregate.add_news_items(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


def initialize(api):
    api.add_resource(OSINTSourcesForCollectors, "/api/v1/collectors/<string:collector_id>/osint-sources")
    api.add_resource(AddNewsItems, "/api/v1/collectors/news-items")
