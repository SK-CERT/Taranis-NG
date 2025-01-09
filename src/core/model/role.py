"""Role model."""

from marshmallow import fields, post_load
from sqlalchemy import func, or_, orm

from managers.db_manager import db
from model.permission import Permission
from shared.schema.role import RoleSchemaBase, PermissionIdSchema, RolePresentationSchema


class NewRoleSchema(RoleSchemaBase):
    """New Role schema.

    Attributes:
        permissions (list): List of permissions.
    """

    permissions = fields.Nested(PermissionIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Return a new Role object.

        Args:
            data (dict): Data to create a new Role object.
        Returns:
            Role: New Role object.
        """
        return Role(**data)


class Role(db.Model):
    """Role model.

    Attributes:
        id (int): Role ID.
        name (str): Role name.
        description (str): Role description.
        permissions (list): List of permissions.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String())

    permissions = db.relationship(Permission, secondary="role_permission")

    def __init__(self, id, name, description, permissions):
        """Initialize a new Role object."""
        self.id = None
        self.name = name
        self.description = description
        self.permissions = []
        for permission in permissions:
            self.permissions.append(Permission.find(permission.id))

        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-account-arrow-right"

    @classmethod
    def find(cls, role_id):
        """Find a role by ID.

        Args:
            role_id (int): Role ID.
        Returns:
            Role: Role object.
        """
        role = db.session.get(cls, role_id)
        return role

    @classmethod
    def find_by_name(cls, role_name):
        """Find a role by name.

        Args:
            role_name (str): Role name.
        Returns:
            Role: Role object.
        """
        role = cls.query.filter_by(name=role_name).first()
        return role

    @classmethod
    def get_all(cls):
        """Get all roles.

        Returns:
            list: List of roles.
        """
        return cls.query.order_by(db.asc(Role.name)).all()

    @classmethod
    def get(cls, search):
        """Get roles.

        Args:
            search (str): Search string.
        Returns:
            tuple: Roles and count.
        """
        query = cls.query

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(or_(func.lower(Role.name).like(search_string), func.lower(Role.description).like(search_string)))

        return query.order_by(db.asc(Role.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Get all roles in JSON format.

        Args:
            search (str): Search string.
        Returns:
            dict: Roles in JSON format.
        """
        roles, count = cls.get(search)
        roles_schema = RolePresentationSchema(many=True)
        return {"total_count": count, "items": roles_schema.dump(roles)}

    @classmethod
    def add_new(cls, data):
        """Add a new role.

        Args:
            data (dict): Data to create a new role.
        """
        new_role_schema = NewRoleSchema()
        role = new_role_schema.load(data)
        db.session.add(role)
        db.session.commit()

    def get_permissions(self):
        """Get all permissions.

        Returns:
            set: Set of all permissions.
        """
        all_permissions = set()
        for permission in self.permissions:
            all_permissions.add(permission.id)

        return all_permissions

    @classmethod
    def update(cls, role_id, data):
        """Update a role.

        Args:
            role_id (int): Role ID.
            data (dict): Data to update a role.
        """
        schema = NewRoleSchema()
        updated_role = schema.load(data)
        role = db.session.get(cls, role_id)
        role.name = updated_role.name
        role.description = updated_role.description
        role.permissions = updated_role.permissions
        db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete a role.

        Args:
            id (int): Role ID.
        """
        role = db.session.get(cls, id)
        db.session.delete(role)
        db.session.commit()


class RolePermission(db.Model):
    """Role Permission model.

    Attributes:
        role_id (int): Role ID.
        permission_id (str): Permission ID.
    """

    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id"), primary_key=True)
