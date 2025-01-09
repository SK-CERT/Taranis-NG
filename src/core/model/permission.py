"""Permission model module."""

from sqlalchemy import func, or_

from managers.db_manager import db
from shared.schema.role import PermissionSchema


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
    def find(cls, permission_id):
        """Retrieve a permission record from the database by its ID.

        Args:
            permission_id (int): The ID of the permission to retrieve.
        Returns:
            Permission: The permission object if found, otherwise None.
        """
        permission = db.session.get(cls, permission_id)
        return permission

    @classmethod
    def add(cls, id, name, description):
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
        db.session.commit()

    @classmethod
    def get_all(cls):
        """Retrieve all permissions from the database.

        Returns:
            list: A list of all permissions in the database.
        """
        return cls.query.order_by(db.asc(Permission.id)).all()

    @classmethod
    def get(cls, search):
        """Retrieve all permissions from the database.

        Args:
            search (str): The search string to filter the permissions by.
        Returns:
            list: A list of all permissions in the database.
        """
        query = cls.query

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(or_(func.lower(Permission.name).like(search_string), func.lower(Permission.description).like(search_string)))

        return query.order_by(db.asc(Permission.id)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Retrieve all permissions from the database as JSON.

        Args:
            search (str): The search string to filter the permissions by.
        Returns:
            dict: A dictionary containing the total count of permissions and a list of permissions.
        """
        permissions, count = cls.get(search)
        permissions_schema = PermissionSchema(many=True)
        return {"total_count": count, "items": permissions_schema.dump(permissions)}
