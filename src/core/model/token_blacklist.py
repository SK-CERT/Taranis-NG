"""Model for tracking blacklisted JWT identifiers."""

from datetime import datetime

from managers.db_manager import db


class TokenBlacklist(db.Model):
    """SQLAlchemy model storing blacklisted JWT ids.

    Attributes:
        id: Primary key.
        token: The JWT identifier (jti) string.
        created: Timestamp when the entry was created.
    """

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(), nullable=False)
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

    @classmethod
    def add(cls, jwt_id: str) -> None:
        """Add a JWT id to the blacklist and commit the change.

        Args:
            jwt_id: The JWT id to add.

        Returns:
            None
        """
        db.session.add(TokenBlacklist(jwt_id))
        db.session.commit()

    @classmethod
    def is_blacklisted(cls, jwt_id: str) -> bool:
        """Check whether a JWT id is present in the blacklist.

        Args:
            jwt_id: The JWT id to check.

        Returns:
            True if the id is blacklisted, otherwise False.
        """
        return db.session.query(db.exists().where(TokenBlacklist.token == jwt_id)).scalar()

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
