"""Persistence for legacy audit records with UTC creation timestamps."""

from managers.db_manager import db
from shared.datetime_utils import utc_now


class AuditRecord(db.Model):
    """A legacy audit entry identifying the actor and resource associated with an action."""

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=utc_now)

    ip_address = db.Column(db.String())

    user_id = db.Column(db.String())
    user_name = db.Column(db.String())

    system_id = db.Column(db.String())
    system_name = db.Column(db.String())

    activity_type = db.Column(db.String())
    activity_resource = db.Column(db.String())
    activity_detail = db.Column(db.String())

    def __init__(
        self,
        ip_address: str | None,
        user_id: str | int | None,
        user_name: str | None,
        system_id: str | int | None,
        system_name: str | None,
        activity_type: str | None,
        activity_resource: str | None,
        activity_detail: str | None,
    ) -> None:
        """Build an unsaved entry; its UTC timestamp is assigned when inserted.

        Args:
            ip_address: Originating client address, when available.
            user_id: User identifier as supplied by the caller, or None for anonymous activity.
            user_name: Name of the user associated with the activity, when known.
            system_id: Identifier of the originating system, when applicable.
            system_name: Name of the originating system, when known.
            activity_type: Category used to classify the recorded action.
            activity_resource: Resource path associated with the action.
            activity_detail: Human-readable explanation of the activity.
        """
        self.id = None
        self.ip_address = ip_address
        self.user_id = user_id
        self.user_name = user_name
        self.system_id = system_id
        self.system_name = system_name
        self.activity_type = activity_type
        self.activity_resource = activity_resource
        self.activity_detail = activity_detail

    @classmethod
    def store(
        cls,
        ip_address: str | None,
        user_id: str | int | None,
        user_name: str | None,
        system_id: str | int | None,
        system_name: str | None,
        activity_type: str | None,
        activity_resource: str | None,
        activity_detail: str | None,
    ) -> None:
        """Add one activity entry and commit it through the current database session.

        Args:
            ip_address: Originating client address, when available.
            user_id: User identifier as supplied by the caller, or None for anonymous activity.
            user_name: Name of the user associated with the activity, when known.
            system_id: Identifier of the originating system, when applicable.
            system_name: Name of the originating system, when known.
            activity_type: Category used to classify the recorded action.
            activity_resource: Resource path associated with the action.
            activity_detail: Human-readable explanation of the activity.

        Returns:
            None: The entry is committed without returning the stored record.
        """
        audit_record = AuditRecord(ip_address, user_id, user_name, system_id, system_name, activity_type, activity_resource, activity_detail)
        db.session.add(audit_record)
        db.session.commit()
