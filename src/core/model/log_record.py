"""Activity log records with UTC creation timestamps."""

from managers.db_manager import db
from shared.datetime_utils import utc_now


class LogRecord(db.Model):
    """An activity entry identifying the actor, resource, and associated request metadata."""

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=utc_now)

    ip_address = db.Column(db.String())

    user_id = db.Column(db.String())
    user_name = db.Column(db.String())

    system_id = db.Column(db.String())
    system_name = db.Column(db.String())

    module_id = db.Column(db.String())

    activity_type = db.Column(db.String())
    activity_resource = db.Column(db.String())
    activity_detail = db.Column(db.String())

    activity_method = db.Column(db.String(8))
    activity_data = db.Column(db.String(4096))

    def __init__(
        self,
        ip_address: str | None,
        user_id: str | int | None,
        user_name: str | None,
        system_id: str | int | None,
        system_name: str | None,
        module_id: str | None,
        activity_type: str | None,
        activity_resource: str | None,
        activity_detail: str | None,
        activity_method: str | None,
        activity_data: str | None,
    ) -> None:
        """Build an unsaved entry; its UTC timestamp is assigned when inserted.

        Args:
            ip_address: Originating client address, when available.
            user_id: User identifier as supplied by the caller, or None for anonymous activity.
            user_name: Name of the user associated with the activity, when known.
            system_id: Identifier of the originating system, when applicable.
            system_name: Name of the originating system, when known.
            module_id: Module that handled the activity, when known.
            activity_type: Category used to classify the recorded action.
            activity_resource: Resource path associated with the action.
            activity_detail: Human-readable explanation of the activity.
            activity_method: HTTP method used for the request, when known.
            activity_data: Request data already prepared for logging by the caller.
        """
        self.id = None
        self.ip_address = ip_address
        self.user_id = user_id
        self.user_name = user_name
        self.system_id = system_id
        self.system_name = system_name
        self.module_id = module_id
        self.activity_type = activity_type
        self.activity_resource = activity_resource
        self.activity_detail = activity_detail
        self.activity_method = activity_method
        self.activity_data = activity_data

    @classmethod
    def store(
        cls,
        ip_address: str | None,
        user_id: str | int | None,
        user_name: str | None,
        system_id: str | int | None,
        system_name: str | None,
        module_id: str | None,
        activity_type: str | None,
        activity_resource: str | None,
        activity_detail: str | None,
        activity_method: str | None,
        activity_data: str | None,
    ) -> None:
        """Add one activity entry and commit it through the current database session.

        Args:
            ip_address: Originating client address, when available.
            user_id: User identifier as supplied by the caller, or None for anonymous activity.
            user_name: Name of the user associated with the activity, when known.
            system_id: Identifier of the originating system, when applicable.
            system_name: Name of the originating system, when known.
            module_id: Module that handled the activity, when known.
            activity_type: Category used to classify the recorded action.
            activity_resource: Resource path associated with the action.
            activity_detail: Human-readable explanation of the activity.
            activity_method: HTTP method used for the request, when known.
            activity_data: Request data already prepared for logging by the caller.

        Returns:
            None: The entry is committed without returning the stored record.
        """
        log_record = LogRecord(
            ip_address,
            user_id,
            user_name,
            system_id,
            system_name,
            module_id,
            activity_type,
            activity_resource,
            activity_detail,
            activity_method,
            activity_data,
        )
        db.session.add(log_record)
        db.session.commit()
