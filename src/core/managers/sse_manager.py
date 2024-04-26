from flask import request, abort
# from flask_sse import sse
from managers.sse import SSE
from datetime import datetime
import os

from managers import auth_manager, bots_manager, time_manager, remote_manager
from model.remote import RemoteAccess


# def use_sse():
#     return os.getenv("REDIS_URL") is not None

class SSEManager:
    def __init__(self):
        self.report_item_locks: dict = {}
        self.sse = SSE()
        self.report_item_locks_last_check_time = datetime.now()

    def news_items_updated(self):
        self.sse.publish({}, type='news-items-updated')

    def report_items_updated(self):
        self.sse.publish({}, type='report-items-updated')

    def report_item_updated(self, data):
        self.sse.publish(data, type='report-item-updated')

    def remote_access_disconnect(self, data):
        self.sse.publish(data, type='remote_access_disconnect', channel='remote')

    def remote_access_news_items_updated(self, osint_source_ids):
        remote_access_event_ids = RemoteAccess.get_relevant_for_news_items(osint_source_ids)
        self.sse.publish(remote_access_event_ids, type='remote_access_news_items_updated', channel='remote')

    def remote_access_report_items_updated(self, report_item_type_id):
        remote_access_event_ids = RemoteAccess.get_relevant_for_report_item(report_item_type_id)
        self.sse.publish(remote_access_event_ids, type='remote_access_report_items_updated', channel='remote')

    # @sse.before_request
    # def connect():
    #     if request.args.get('jwt') is not None:
    #         if auth_manager.decode_user_from_jwt(request.args.get('jwt')) is None:
    #             abort(403)
    #     elif request.args.get('api_key') is not None:
    #         if bots_manager.verify_api_key(request.args.get('api_key')) is False:
    #             abort(403)
    #     elif request.args.get('access_key') is not None and request.args.get('channel') is not None:
    #         if request.args.get('channel') == 'remote':
    #             if remote_manager.verify_access_key(request.args.get('access_key')) is False:
    #                 abort(403)
    #     else:
    #         abort(403)

    def report_item_lock(self, report_item_id, field_id, user_id):
        if report_item_id in self.report_item_locks:
            report_item = self.report_item_locks[report_item_id]
        else:
            report_item = {}
            self.report_item_locks[report_item_id] = report_item

        if field_id not in report_item or report_item[field_id] is None:
            report_item[field_id] = {'user_id': user_id, 'lock_time': datetime.now()}
            self.sse.publish({'report_item_id': int(report_item_id), 'field_id': field_id, 'user_id': user_id},
                             type='report-item-locked')

    def report_item_unlock(self, report_item_id, field_id, user_id):
        if report_item_id in self.report_item_locks:
            report_item = self.report_item_locks[report_item_id]

            if field_id in report_item:
                report_item[field_id] = None

        self.sse.publish({'report_item_id': int(report_item_id), 'field_id': field_id, 'user_id': user_id},
                         type='report-item-unlocked')

    def report_item_hold_lock(self, report_item_id, field_id, user_id):
        if report_item_id in self.report_item_locks:
            report_item = self.report_item_locks[report_item_id]
            if field_id in report_item and report_item[field_id] is not None:
                if report_item[field_id]['user_id'] == user_id:
                    report_item[field_id]['lock_time'] = datetime.now()

    def check_report_item_locks(self, app):
        # global report_item_locks_last_check_time
        for key in self.report_item_locks:
            for field_key in self.report_item_locks[key]:
                if self.report_item_locks[key][field_key] is not None:
                    if self.report_item_locks[key][field_key]['lock_time'] < self.report_item_locks_last_check_time:
                        self.report_item_locks[key][field_key] = None
                        with app.app_context():
                            self.sse.publish({'report_item_id': int(key), 'field_id': field_key, 'user_id': -1},
                                             type='report-item-unlocked')

        self.report_item_locks_last_check_time = datetime.now()


sse_manager = SSEManager()


def initialize(app):
    time_manager.schedule_job_minutes(1, sse_manager.check_report_item_locks, app)
