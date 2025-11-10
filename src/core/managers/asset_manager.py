"""Asset Manager to handle asset-related operations."""

import threading

from managers import publishers_manager
from managers.db_manager import db
from model.asset import Asset
from model.publisher_preset import PublisherPreset
from model.state_system import StateManager


def remove_vulnerability(report_item_id: int) -> None:
    """Remove vulnerability from assets."""
    Asset.remove_vulnerability(report_item_id)
    db.session.commit()


def report_item_changed(report_item: object) -> None:
    """Handle report item changes."""
    if StateManager.has_state("report_item", report_item.id, "completed"):
        cpes = [cpe.value for cpe in report_item.report_item_cpes]

        assets = Asset.get_by_cpe(cpes)

        notification_groups = set()

        for asset in assets:
            asset.add_vulnerability(report_item)
            notification_groups.add(asset.asset_group)

        db.session.commit()

        publisher_preset = PublisherPreset.find_for_notifications()
        if publisher_preset is not None:

            class NotificationThread(threading.Thread):
                @classmethod
                def run(cls) -> None:
                    for notification_group in notification_groups:
                        for template in notification_group.templates:
                            recipients = [recipient.email for recipient in template.recipients]
                            publishers_manager.publish(publisher_preset, None, template.message_title, template.message_body, recipients)

            notification_thread = NotificationThread()
            notification_thread.start()
