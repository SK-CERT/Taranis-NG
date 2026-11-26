"""Model for tracking blacklisted JWT identifiers."""

from datetime import datetime

from managers.db_manager import db

# A logged-out sign-in is stored under its session id with this prefix. A jti is a bare UUID, so
# the two kinds of entry can never collide in the one column.
SESSION_PREFIX = "sid:"


class TokenBlacklist(db.Model):
    """SQLAlchemy model storing blacklisted JWT ids.

    Attributes:
        id: Primary key.
        token: The JWT identifier (jti) string, or ``sid:<session id>`` for a whole sign-in.
        created: Timestamp when the entry was created.
    """

    id = db.Column(db.Integer, primary_key=True)
    # Looked up on every authenticated request.
    token = db.Column(db.String(), nullable=False, index=True)
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, jwt_id: str) -> None:
        """Create a new blacklist entry.

        Args:
            jwt_id: The JWT id to blacklist.

        Returns:
            None
        """
        self.id = None
        self.token = jwt_id

    @staticmethod
    def _entries(jwt_id: str | None, session_id: str | None) -> list[str]:
        """The stored values standing for a token's jti and its sign-in's session id."""
        session_entry = f"{SESSION_PREFIX}{session_id}" if session_id else None
        return [entry for entry in (jwt_id, session_entry) if entry]

    @classmethod
    def add(cls, jwt_id: str, session_id: str | None = None) -> None:
        """Add a JWT id to the blacklist, with every token of its sign-in, and commit the change.

        Args:
            jwt_id: The JWT id to add.
            session_id: The sign-in's session id; its other tokens (earlier or refreshed ones,
                another tab's) are refused from now on too.

        Returns:
            None
        """
        for entry in cls._entries(jwt_id, session_id):
            db.session.add(TokenBlacklist(entry))
        db.session.commit()

    @classmethod
    def is_blacklisted(cls, jwt_id: str | None, session_id: str | None = None) -> bool:
        """Check whether a JWT id, or the sign-in it belongs to, is present in the blacklist.

        Args:
            jwt_id: The JWT id to check.
            session_id: The token's session id.

        Returns:
            True if the id or the session is blacklisted, otherwise False.
        """
        entries = cls._entries(jwt_id, session_id)
        if not entries:
            return False
        return db.session.query(db.exists().where(TokenBlacklist.token.in_(entries))).scalar()

    @classmethod
    def delete_older(cls, check_time: datetime) -> None:
        """Delete blacklist entries older than `check_time` and commit.

        Args:
            check_time: Datetime threshold; entries older than this are removed.

        Returns:
            None
        """
        db.session.query(TokenBlacklist).filter(TokenBlacklist.created < check_time).delete()
        db.session.commit()
