"""Permission model module."""

from typing import Any

from managers.db_manager import db
from shared.schema.role import PermissionSchema
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError


class Permission(db.Model):
    """Permission model.

    Attributes:
        id (str): The unique identifier of the permission.
        name (str): The name of the permission.
        description (str): The description of the permission.
    """

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    @classmethod
    def find(cls, permission_id: str) -> "Permission | None":
        """Retrieve a permission record from the database by its ID.

        Args:
            permission_id (str): The ID of the permission to retrieve.

        Returns:
            Permission | None: The permission object if found, otherwise None.
        """
        return db.session.get(cls, permission_id)

    @classmethod
    def add(cls, id: str, name: str, description: str) -> None:  # noqa: A002
        """Add a new permission to the database.

        Args:
            id (str): The unique identifier of the permission.
            name (str): The name of the permission.
            description (str): The description of the permission
        """
        permission = cls.find(id)
        if permission is None:
            permission = Permission()
            permission.id = id
            permission.name = name
            permission.description = description
            db.session.add(permission)
        else:
            permission.name = name
            permission.description = description
        try:
            db.session.commit()
        except IntegrityError:
            # Another process (e.g. the scheduler vs. a gunicorn worker during
            # the first boot after an upgrade) inserted the same permission
            # concurrently; theirs is identical, so keep it.
            db.session.rollback()

    @classmethod
    def get_all(cls) -> list["Permission"]:
        """Retrieve all permissions from the database.

        Returns:
            list[Permission]: A list of all permissions in the database.
        """
        return cls.query.order_by(db.asc(Permission.id)).all()

    @classmethod
    def get(cls, search: str | None) -> tuple[list["Permission"], int]:
        """Retrieve all permissions from the database.

        Args:
            search (str | None): The search string to filter the permissions by.

        Returns:
            tuple[list[Permission], int]: A tuple containing a list of permissions and total count.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(Permission.name.ilike(search_string), Permission.description.ilike(search_string)))

        return query.order_by(db.asc(Permission.id)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None) -> dict[str, Any]:
        """Retrieve all permissions from the database as JSON.

        Args:
            search (str | None): The search string to filter the permissions by.

        Returns:
            dict[str, Any]: A dictionary containing the total count of permissions and a list of permissions.
        """
        permissions, count = cls.get(search)
        permissions_schema = PermissionSchema(many=True)
        return {"total_count": count, "items": permissions_schema.dump(permissions)}
