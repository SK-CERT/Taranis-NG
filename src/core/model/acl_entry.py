"""ACL Entry Model."""

from sqlalchemy import or_, orm, and_
from marshmallow import fields, post_load

from managers.db_manager import db
from model.role import Role
from model.user import User
from shared.schema.role import RoleIdSchema
from shared.schema.user import UserIdSchema
from shared.schema.acl_entry import ACLEntrySchema, ACLEntryPresentationSchema, ItemType


class NewACLEntrySchema(ACLEntrySchema):
    """New ACL Entry Schema.

    This schema is used to create a new ACL Entry.
    Attributes:
        users (list): List of users that have access to the ACL Entry.
        roles (list): List of roles that have access to the ACL Entry.
    """

    users = fields.Nested(UserIdSchema, many=True)
    roles = fields.Nested(RoleIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Create a new ACL Entry.

        Args:
            data (dict): Data to create the new ACL Entry.
        Returns:
            ACLEntry: New ACL Entry object.
        """
        return ACLEntry(**data)


class ACLEntry(db.Model):
    """ACL Entry Model.

    This model represents an ACL Entry in the database.

    Attributes:
        id (int): ACL Entry ID.
        name (str): ACL Entry name.
        description (str): ACL Entry description.
        item_type (ItemType): ACL Entry item type.
        item_id (str): ACL Entry item ID.
        everyone (bool): ACL Entry everyone flag.
        users (list): List of users that have access to the ACL Entry.
        roles (list): List of roles that have access to the ACL Entry.
        see (bool): ACL Entry see flag.
        access (bool): ACL Entry access flag.
        modify (bool): ACL Entry modify flag.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String())

    item_type = db.Column(db.Enum(ItemType))
    item_id = db.Column(db.String(64))

    everyone = db.Column(db.Boolean)
    users = db.relationship("User", secondary="acl_entry_user")
    roles = db.relationship("Role", secondary="acl_entry_role")

    see = db.Column(db.Boolean)
    access = db.Column(db.Boolean)
    modify = db.Column(db.Boolean)

    def __init__(self, id, name, description, item_type, item_id, everyone, users, see, access, modify, roles):
        """Create a new ACL Entry."""
        self.id = None
        self.name = name
        self.description = description
        self.item_type = item_type
        self.item_id = item_id
        self.everyone = everyone
        self.see = see
        self.access = access
        self.modify = modify

        self.users = []
        for user in users:
            self.users.append(User.find_by_id(user.id))

        self.roles = []
        for role in roles:
            self.roles.append(Role.find(role.id))

        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct ACL Entry."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-lock-check"

    @classmethod
    def find(cls, id):
        """Find ACL Entry by ID.

        Args:
            id (int): ACL Entry ID.
        Returns:
            ACLEntry: ACL Entry object.
        """
        acl = db.session.get(cls, id)
        return acl

    @classmethod
    def get_all(cls):
        """Get all ACL Entries.

        Returns:
            list: List of ACL Entries.
        """
        return cls.query.order_by(db.asc(ACLEntry.name)).all()

    @classmethod
    def get(cls, search):
        """Get ACL Entries.

        Args:
            search (str): Search string.
        Returns:
            list: List of ACL Entries.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(ACLEntry.name.ilike(search_string), ACLEntry.description.ilike(search_string)))

        return query.order_by(db.asc(ACLEntry.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Get all ACL Entries in JSON format.

        Args:
            search (str): Search string.
        Returns:
            dict: JSON object with the ACL Entries.
        """
        acls, count = cls.get(search)
        acl_schema = ACLEntryPresentationSchema(many=True)
        return {"total_count": count, "items": acl_schema.dump(acls)}

    @classmethod
    def add_new(cls, data):
        """Add a new ACL Entry.

        Args:
            data (dict): Data to create the new ACL Entry.
        """
        new_acl_schema = NewACLEntrySchema()
        acl = new_acl_schema.load(data)
        db.session.add(acl)
        db.session.commit()

    @classmethod
    def update(cls, acl_id, data):
        """Update an ACL Entry.

        Args:
            acl_id (int): ACL Entry ID.
            data (dict): Data to update the ACL Entry.
        """
        schema = NewACLEntrySchema()
        updated_acl = schema.load(data)
        acl = db.session.get(cls, acl_id)
        acl.name = updated_acl.name
        acl.description = updated_acl.description
        acl.item_type = updated_acl.item_type
        acl.item_id = updated_acl.item_id
        acl.everyone = updated_acl.everyone
        acl.see = updated_acl.see
        acl.access = updated_acl.access
        acl.modify = updated_acl.modify
        acl.users = updated_acl.users
        acl.roles = updated_acl.roles
        db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete an ACL Entry.

        Args:
            id (int): ACL Entry ID.
        """
        acl = db.session.get(cls, id)
        db.session.delete(acl)
        db.session.commit()

    @classmethod
    def apply_query(cls, query, user, see, access, modify):
        """Apply Query.

        This method is used to apply the query to the ACL Entry.

        Args:
            query (Query): Query to apply.
            user (User): User object.
            see (bool): See flag.
            access (bool): Access flag.
            modify (bool): Modify flag.
        Returns:
            Query: Query with the applied ACL Entry.
        """
        roles = []
        for role in user.roles:
            roles.append(role.id)

        query = query.outerjoin(ACLEntryUser, and_(ACLEntryUser.acl_entry_id == ACLEntry.id, ACLEntryUser.user_id == user.id))

        query = query.outerjoin(ACLEntryRole, ACLEntryRole.acl_entry_id == ACLEntry.id)

        if see is False and access is False and modify is False:
            return query.filter(
                or_(ACLEntry.id.is_(None), ACLEntry.everyone.is_(True), ACLEntryUser.user_id == user.id, ACLEntryRole.role_id.in_(roles))
            )

        if see:
            return query.filter(
                or_(
                    ACLEntry.id.is_(None),
                    and_(
                        ACLEntry.see.is_(True),
                        or_(ACLEntry.everyone.is_(True), ACLEntryUser.user_id == user.id, ACLEntryRole.role_id.in_(roles)),
                    ),
                )
            )
        if access:
            return query.filter(
                or_(
                    ACLEntry.id.is_(None),
                    and_(
                        ACLEntry.access.is_(True),
                        or_(ACLEntry.everyone.is_(True), ACLEntryUser.user_id == user.id, ACLEntryRole.role_id.in_(roles)),
                    ),
                )
            )

        if modify:
            return query.filter(
                or_(
                    ACLEntry.id.is_(None),
                    and_(
                        ACLEntry.modify.is_(True),
                        or_(ACLEntry.everyone.is_(True), ACLEntryUser.user_id == user.id, ACLEntryRole.role_id.in_(roles)),
                    ),
                )
            )


class ACLEntryUser(db.Model):
    """ACL Entry User Model.

    This model represents the relationship between ACL Entry and User in the database.

    Attributes:
        acl_entry_id (int): ACL Entry ID.
        user_id (int): User ID.
    """

    acl_entry_id = db.Column(db.Integer, db.ForeignKey("acl_entry.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)


class ACLEntryRole(db.Model):
    """ACL Entry Role Model.

    This model represents the relationship between ACL Entry and Role in the database.

    Attributes:
        acl_entry_id (int): ACL Entry ID.
        role_id (int): Role ID.
    """

    acl_entry_id = db.Column(db.Integer, db.ForeignKey("acl_entry.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)
