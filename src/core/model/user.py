"""User module for the model representing a user in the system."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.user import User

from managers.db_manager import db
from marshmallow import EXCLUDE, Schema, fields, post_load
from model.organization import Organization
from model.permission import Permission
from model.role import Role
from model.word_list import WordList
from sqlalchemy import or_, orm
from werkzeug.security import generate_password_hash

from shared.schema.organization import OrganizationIdSchema
from shared.schema.role import PermissionIdSchema, RoleIdSchema
from shared.schema.user import HotkeySchema, UserPresentationSchema, UserSchemaBase
from shared.schema.word_list import WordListSchema


class Hotkey(db.Model):
    """Represents a hotkey for a user.

    Attributes:
        id (int): The unique identifier for the hotkey.
        key (str): The key associated with the hotkey.
        alias (str): The alias for the hotkey.
        user_id (int): The foreign key referencing the user.

    Args:
        db.Model: The base class for all models in the application.
    """

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String)
    alias = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __init__(self, key: str, alias: str) -> None:
        """Initialize a User object."""
        self.id = None
        self.key = key
        self.alias = alias

    @classmethod
    def get_json(cls, user: User) -> dict:
        """Return the JSON representation of a user's hotkeys.

        Args:
            cls (class): The class object.
            user (User): The user object.

        Returns:
            dict: The JSON representation of the user's hotkeys.
        """
        schema = HotkeySchema(many=True)
        return schema.dump(user.hotkeys)

    @classmethod
    def update(cls, user: User, data: dict) -> dict:
        """Update the user's hotkeys with the provided data.

        Args:
            cls (class): The class object.
            user (User): The user object to update the hotkeys for.
            data (dict): The data containing the updated hotkeys information.

        Returns:
            dict: The updated hotkeys information in JSON format.
        """
        schema = NewHotkeySchema(many=True)
        updated_data = schema.load(data)
        user.hotkeys = updated_data
        db.session.commit()

        return cls.get_json(user)


class NewHotkeySchema(HotkeySchema):
    """Represents a schema for creating a new hotkey."""

    @post_load
    def make(self, data: dict, **kwargs) -> Hotkey:  # noqa: ANN003, ARG002
        """Create a new Hotkey instance based on the given data.

        Args:
            data (dict): A dictionary containing the data for the Hotkey.
            **kwargs: Additional keyword arguments.

        Returns:
            Hotkey: A new Hotkey instance.
        """
        return Hotkey(**data)


class User(db.Model):
    """User class represents a user in the system.

    Attributes:
        id (int): The unique identifier of the user.
        username (str): The username of the user.
        name (str): The name of the user.
        password (str): The password of the user.
        organizations (list): The organizations the user belongs to.
        roles (list): The roles assigned to the user.
        permissions (list): The permissions granted to the user.
        title (str): The title of the user.
        subtitle (str): The subtitle of the user.
        tag (str): The tag associated with the user.
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(), nullable=False)
    password = db.Column(db.String(), nullable=False)

    organizations = db.relationship("Organization", secondary="user_organization")
    roles = db.relationship(Role, secondary="user_role")
    permissions = db.relationship(Permission, secondary="user_permission", lazy="joined")
    hotkeys = db.relationship(Hotkey, cascade="all, delete-orphan", lazy="joined")
    word_lists = db.relationship(WordList, secondary="user_word_list", lazy="joined")

    def __init__(
        self,
        id: int,  # noqa: A002, ARG002
        username: str,
        name: str,
        password: str,
        organizations: list,
        roles: list,
        permissions: list,
    ) -> None:
        """Initialize a User object with the given parameters.

        Args:
            id (int): The unique identifier of the user.
            username (str): The username of the user.
            name (str): The name of the user.
            password (str): The password of the user.
            organizations (list): The organizations the user belongs to.
            roles (list): The roles assigned to the user.
            permissions (list): The permissions granted to the user.

        Returns:
            None
        """
        self.id = None
        self.username = username
        self.name = name
        self.password = generate_password_hash(password)
        self.organizations = []
        if organizations:
            for organization in organizations:
                self.organizations.append(Organization.find(organization.id))

        self.roles = []
        if roles:
            for role in roles:
                self.roles.append(Role.find(role.id))

        self.permissions = []
        if permissions:
            for permission in permissions:
                self.permissions.append(Permission.find(permission.id))

        self.hotkeys = []
        self.word_lists = []

        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct the user object."""
        self.title = self.name
        self.subtitle = self.username
        self.tag = "mdi-account"

    @classmethod
    def find(cls, username: str) -> User | None:
        """Find a user by their username.

        Args:
            cls: The class object.
            username: The username of the user to find.

        Returns:
            The user object if found, None otherwise.
        """
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_id(cls, user_id: int) -> User | None:
        """Find a user by their ID.

        Args:
            cls: The class object.
            user_id: The ID of the user to find.

        Returns:
            The user object if found, None otherwise.
        """
        return db.session.get(cls, user_id)

    @classmethod
    def get_all(cls) -> list[User]:
        """Retrieve all instances of the User class from the database.

        Returns:
            list: A list of User instances, ordered by name in ascending order.
        """
        return cls.query.order_by(db.asc(User.name)).all()

    @classmethod
    def get(cls, search: str, organization: Organization | None) -> tuple[list[User], int]:
        """Retrieve users based on search criteria and organization.

        Args:
            cls: The class object.
            search (str): The search string to filter users by name or username.
            organization: The organization to filter users by.

        Returns:
            tuple: A tuple containing two elements:
                    A list of users matching the search criteria and organization, ordered by name.
                    The total count of users matching the search criteria and organization.
        """
        query = cls.query

        if organization is not None:
            query = query.join(UserOrganization, User.id == UserOrganization.user_id)

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(User.name.ilike(search_string), User.username.ilike(search_string)))

        return query.order_by(db.asc(User.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str) -> dict:
        """Retrieve all users matching the given search criteria and returns them as a JSON object.

        Args:
            cls: The class object.
            search: The search criteria.

        Returns:
            A JSON object containing the total count of users and a list of user items matching the search criteria.
        """
        users, count = cls.get(search, None)
        user_schema = UserPresentationSchema(many=True)
        return {"total_count": count, "items": user_schema.dump(users)}

    @classmethod
    def get_all_external_json(cls, user: User, search: str) -> dict:
        """Retrieve all external JSON data for a given user.

        Args:
            cls (class): The class object.
            user (User): The user object.
            search (str): The search query.

        Returns:
            dict: A dictionary containing the total count and items of the retrieved data.
        """
        if user.organizations:
            users, count = cls.get(search, user.organizations[0])
        else:
            return {"total_count": 0, "items": []}
        user_schema = UserPresentationSchema(many=True)
        return {"total_count": count, "items": user_schema.dump(users)}

    @classmethod
    def add_new(cls, data: dict) -> None:
        """Add a new user to the database.

        Args:
            data: A dictionary containing the user data.
        """
        new_user_schema = NewUserSchema()
        user = new_user_schema.load(data)
        db.session.add(user)
        db.session.commit()

    @classmethod
    def add_new_external(cls, user: User, permissions: list, data: dict) -> None:
        """Add a new external user to the system.

        Args:
            cls: The class object.
            user: The user object.
            permissions: The list of permissions.
            data: The data for the new user.
        """
        new_user_schema = NewUserSchema()
        new_user = new_user_schema.load(data)
        new_user.roles = []
        new_user.organizations = user.organizations

        for permission in new_user.permissions[:]:
            if permission.id not in permissions:
                new_user.permissions.remove(permission)

        db.session.add(new_user)
        db.session.commit()

    @classmethod
    def update(cls, user_id: int, data: dict) -> None:
        """Update a user with the given user_id using the provided data.

        Args:
            cls (class): The class object.
            user_id (int): The ID of the user to be updated.
            data (dict): The data containing the updated user information.
        """
        schema = UpdateUserSchema()
        updated_user = schema.load(data)
        user = db.session.get(cls, user_id)
        user.username = updated_user["username"]
        user.name = updated_user["name"]
        if updated_user["password"]:  # update password only when user fill it
            user.password = generate_password_hash(updated_user["password"])
        user.organizations = []
        for o in updated_user["organizations"]:
            org = Organization.find(o.id)
            if org:
                user.organizations.append(org)
        user.roles = []
        for r in updated_user["roles"]:
            role = Role.find(r.id)
            if role:
                user.roles.append(role)
        user.permissions = []
        for p in updated_user["permissions"]:
            perm = Permission.find(p.id)
            if perm:
                user.permissions.append(perm)
        db.session.commit()

    @classmethod
    def update_external(cls, current_user: User, assets_permissions: list, user_id: int, data: dict) -> None:
        """Update an external user with the provided data.

        Args:
            cls (class): The class object.
            current_user (User): The current user performing the update.
            assets_permissions (list): The list of ASSETS permissions.
            user_id (int): The ID of the user to be updated.
            data (dict): The data to update the user with.
        """
        schema = UpdateUserSchema()
        user_data = schema.load(data)
        user = db.session.get(cls, user_id)

        if any(org in current_user.organizations for org in user.organizations):
            user.username = user_data["username"]
            user.name = user_data["name"]
            if user_data["password"]:  # update password only when user fill it
                user.password = generate_password_hash(user_data["password"])
            user.permissions = []
            for p in user_data["permissions"]:
                perm = Permission.find(p.id)
                if perm and perm.id in assets_permissions:
                    user.permissions.append(perm)
            db.session.commit()

    @classmethod
    def delete(cls, user_id: int) -> None:
        """Delete a user from the database.

        Args:
            cls (class): The class representing the user model.
            user_id (int): The ID of the user to be deleted.
        """
        user = db.session.get(cls, user_id)
        db.session.delete(user)
        db.session.commit()

    @classmethod
    def delete_external(cls, user: User, user_id: int) -> None:
        """Delete an external user from the database.

        Args:
            cls (class): The class object.
            user (User): The user performing the deletion.
            user_id (int): The ID of the user to be deleted.
        """
        existing_user = db.session.get(cls, user_id)
        if any(org in user.organizations for org in existing_user.organizations):
            db.session.delete(existing_user)
            db.session.commit()

    def get_permissions(self) -> list[int]:
        """Return a list of all permissions associated with the user.

        Returns:
            list: A list of permission IDs.
        """
        all_permissions = set()

        for permission in self.permissions:
            all_permissions.add(permission.id)

        for role in self.roles:
            all_permissions.update(role.get_permissions())

        return list(all_permissions)

    def get_current_organization_name(self) -> str:
        """Return the name of the current organization.

        Returns:
            str: The name of the current organization. If no organization is available, an empty string is returned.
        """
        if len(self.organizations) > 0:
            return self.organizations[0].name
        return ""


class NewUserSchema(UserSchemaBase):
    """NewUserSchema class for defining the schema of a new user.

    Attributes:
        roles (Nested): A nested field representing the roles of the user.
        permissions (Nested): A nested field representing the permissions of the user.
        organizations (Nested): A nested field representing the organizations the user belongs to.

    Returns:
        User: A User object created from the given data.
    """

    roles = fields.Nested(RoleIdSchema, many=True)
    permissions = fields.Nested(PermissionIdSchema, many=True)
    organizations = fields.Nested(OrganizationIdSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> User:  # noqa: ANN003, ARG002
        """Create a new User object based on the provided data.

        Args:
            data (dict): A dictionary containing the user data.
            **kwargs: Additional keyword arguments.

        Returns:
            User: A new User object initialized with the provided data.
        """
        return User(**data)


class UpdateUserSchema(UserSchemaBase):
    """Schema for updating user information.

    Attributes:
        password (str): The user's password. If not provided, the password will not be updated.
        roles (list): A list of role IDs assigned to the user.
        permissions (list): A list of permission IDs assigned to the user.
        organizations (list): A list of organization IDs associated with the user.
    """

    password = fields.Str(load_default=None, allow_none=True)
    roles = fields.Nested(RoleIdSchema, many=True)
    permissions = fields.Nested(PermissionIdSchema, many=True)
    organizations = fields.Nested(OrganizationIdSchema, many=True)


class UserOrganization(db.Model):
    """Represents the association table between User and Organization.

    Attributes:
        user_id (int): The ID of the user.
        organization_id (int): The ID of the organization.
    """

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), primary_key=True)


class UserRole(db.Model):
    """Model class representing the association table between User and Role.

    Attributes:
        user_id (int): The ID of the user.
        role_id (int): The ID of the role.
    """

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)


class UserPermission(db.Model):
    """Represents the association table between User and Permission models.

    Attributes:
        user_id (int): The ID of the user.
        permission_id (str): The ID of the permission.
    """

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id"), primary_key=True)


class UserWordList(db.Model):
    """Model class representing the association table between User and WordList.

    Attributes:
        user_id (int): The ID of the user.
        word_list_id (int): The ID of the word list.
    """

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id"), primary_key=True)

    def __init__(self, user_id: int, word_list_id: int) -> None:
        """Initialize a UserWordList object."""
        self.user_id = user_id
        self.word_list_id = word_list_id

    @classmethod
    def get_json(cls, user: User) -> dict:
        """Return the JSON representation of a user's word lists.

        Args:
            cls (class): The class object.
            user (User): The user object.

        Returns:
            dict: The JSON representation of the user's word lists.
        """
        schema = WordListSchema(many=True)
        return schema.dump(user.word_lists)

    @classmethod
    def update(cls, user: User, data: dict) -> dict:
        """Update the user's word list with the provided data.

        Args:
            cls (class): The class object.
            user (User): The user object to update the word list for.
            data (dict): The data containing the updated word list information.

        Returns:
            dict: The updated word list information in JSON format.
        """
        ids = [item["id"] for item in data]
        user.word_lists = [db.session.get(WordList, i) for i in ids if i is not None]

        db.session.commit()
        return cls.get_json(user)


class NewUserWordListSchema(Schema):
    """Represents a schema for creating a new UserWordList."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    user_id = fields.Int()
    word_list_id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> UserWordList:  # noqa: ANN003, ARG002
        """Create a new UserWordList instance based on the given data.

        Args:
            data (dict): A dictionary containing the data for the UserWordList.
            **kwargs: Additional keyword arguments.

        Returns:
            UserWordList: A new UserWordList instance.
        """
        return UserWordList(**data)
