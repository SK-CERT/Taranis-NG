"""User module for the model representing a user in the system."""

from marshmallow import fields, post_load
from sqlalchemy import func, or_, orm

from managers.db_manager import db
from model.role import Role
from model.permission import Permission
from model.organization import Organization
from shared.schema.user import UserSchemaBase, UserProfileSchema, HotkeySchema, UserPresentationSchema
from shared.schema.role import RoleIdSchema, PermissionIdSchema
from shared.schema.organization import OrganizationIdSchema
from shared.schema.word_list import WordListIdSchema
from werkzeug.security import generate_password_hash


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
    def make(self, data, **kwargs):
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
        profile_id (int): The ID of the user's profile.
        profile (UserProfile): The profile of the user.
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

    profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id"))
    profile = db.relationship("UserProfile", cascade="all", lazy="joined")

    def __init__(self, id, username, name, password, organizations, roles, permissions):
        """Initialize a User object with the given parameters.

        Args:
            id (int): The user's ID.
            username (str): The user's username.
            name (str): The user's name.
            password (str): The user's password.
            organizations (list): A list of organizations the user belongs to.
            roles (list): A list of roles assigned to the user.
            permissions (list): A list of permissions granted to the user.
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

        self.profile = UserProfile(True, False, None, [], [])
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the user object.

        This method updates the `title`, `subtitle`, and `tag` attributes of the user object
          based on the current `name` and `username` values.
        """
        self.title = self.name
        self.subtitle = self.username
        self.tag = "mdi-account"

    @classmethod
    def find(cls, username):
        """Find a user by their username.

        Args:
            cls: The class object.
            username: The username of the user to find.
        Returns:
            The user object if found, None otherwise.
        """
        user = cls.query.filter_by(username=username).first()
        return user

    @classmethod
    def find_by_id(cls, user_id):
        """Find a user by their ID.

        Args:
            cls: The class object.
            user_id: The ID of the user to find.
        Returns:
            The user object if found, None otherwise.
        """
        user = cls.query.get(user_id)
        return user

    @classmethod
    def get_all(cls):
        """Retrieve all instances of the User class from the database.

        Returns:
            list: A list of User instances, ordered by name in ascending order.
        """
        return cls.query.order_by(db.asc(User.name)).all()

    @classmethod
    def get(cls, search, organization):
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
            search_string = f"%{search.lower()}%"
            query = query.filter(or_(func.lower(User.name).like(search_string), func.lower(User.username).like(search_string)))

        return query.order_by(db.asc(User.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
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
    def get_all_external_json(cls, user, search):
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
    def add_new(cls, data):
        """Add a new user to the database.

        Args:
            data: A dictionary containing the user data.
        """
        new_user_schema = NewUserSchema()
        user = new_user_schema.load(data)
        db.session.add(user)
        db.session.commit()

    @classmethod
    def add_new_external(cls, user, permissions, data):
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
    def update(cls, user_id, data):
        """Update a user with the given user_id using the provided data.

        Args:
            cls (class): The class object.
            user_id (int): The ID of the user to be updated.
            data (dict): The data containing the updated user information.
        """
        schema = UpdateUserSchema()
        updated_user = schema.load(data)
        user = cls.query.get(user_id)
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
    def update_external(cls, user, permissions, user_id, data):
        """Update an external user with the provided data.

        Args:
            cls (class): The class object.
            user (User): The current user performing the update.
            permissions (list): The list of permissions.
            user_id (int): The ID of the user to be updated.
            data (dict): The data to update the user with.
        """
        schema = NewUserSchema()
        updated_user = schema.load(data)
        existing_user = cls.query.get(user_id)

        if any(org in user.organizations for org in existing_user.organizations):
            existing_user.username = updated_user.username
            existing_user.name = updated_user.name

            for permission in updated_user.permissions[:]:
                if permission.id not in permissions:
                    updated_user.permissions.remove(permission)

            existing_user.permissions = updated_user.permissions

            db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete a user from the database.

        Args:
            cls (class): The class representing the user model.
            id (int): The ID of the user to be deleted.
        """
        user = cls.query.get(id)
        db.session.delete(user)
        db.session.commit()

    @classmethod
    def delete_external(cls, user, id):
        """Delete an external user from the database.

        Args:
            cls (class): The class object.
            user (User): The user performing the deletion.
            id (int): The ID of the user to be deleted.
        """
        existing_user = cls.query.get(id)
        if any(org in user.organizations for org in existing_user.organizations):
            db.session.delete(existing_user)
            db.session.commit()

    def get_permissions(self):
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

    def get_current_organization_name(self):
        """Return the name of the current organization.

        Returns:
            str: The name of the current organization. If no organization is available, an empty string is returned.
        """
        if len(self.organizations) > 0:
            return self.organizations[0].name
        else:
            return ""

    @classmethod
    def get_profile_json(cls, user):
        """Return the JSON representation of a user's profile.

        Args:
            cls (class): The class object.
            user (User): The user object.
        Returns:
            dict: The JSON representation of the user's profile.
        """
        profile_schema = UserProfileSchema()
        return profile_schema.dump(user.profile)

    @classmethod
    def update_profile(cls, user, data):
        """Update the user's profile with the provided data.

        Args:
            cls (class): The class object.
            user (User): The user object to update the profile for.
            data (dict): The data containing the updated profile information.
        Returns:
            dict: The updated profile information in JSON format.
        """
        new_profile_schema = NewUserProfileSchema()
        updated_profile = new_profile_schema.load(data)

        user.profile.spellcheck = updated_profile.spellcheck
        user.profile.dark_theme = updated_profile.dark_theme
        user.profile.language = updated_profile.language
        user.profile.word_lists = []
        from model.word_list import WordList

        for word_list in updated_profile.word_lists:
            if WordList.allowed_with_acl(word_list.id, user, True, False, False):
                user.profile.word_lists.append(word_list)

        user.profile.hotkeys = updated_profile.hotkeys

        db.session.commit()

        return cls.get_profile_json(user)


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


class NewHotkeySchema(HotkeySchema):
    """Represents a schema for creating a new hotkey."""

    @post_load
    def make(self, data, **kwargs):
        """Create a new Hotkey instance based on the given data.

        Args:
            data (dict): A dictionary containing the data for the Hotkey.
            **kwargs: Additional keyword arguments.
        Returns:
            Hotkey: A new Hotkey instance.
        """
        return Hotkey(**data)


class NewUserProfileSchema(UserProfileSchema):
    """Schema for creating a new user profile.

    Attributes:
        word_lists (List[Nested[WordListIdSchema]]): A list of nested schemas for word lists.
        hotkeys (List[Nested[NewHotkeySchema]]): A list of nested schemas for hotkeys.
    """

    word_lists = fields.List(fields.Nested(WordListIdSchema))
    hotkeys = fields.List(fields.Nested(NewHotkeySchema))

    @post_load
    def make(self, data, **kwargs):
        """Create a new UserProfile instance based on the given data.

        Args:
            data (dict): A dictionary containing the data for the UserProfile.
            **kwargs: Additional keyword arguments.
        Returns:
            UserProfile: A new UserProfile instance.
        """
        return UserProfile(**data)


class UserProfile(db.Model):
    """Represent a user profile.

    Attributes:
        id (int): The unique identifier for the user profile.
        spellcheck (bool): Indicates whether spellcheck is enabled for the user.
        dark_theme (bool): Indicates whether dark theme is enabled for the user.
        language (str): The language code for the user's preferred language.
        hotkeys (list): A list of hotkeys associated with the user profile.
        word_lists (list): A list of word lists associated with the user profile.
    """

    id = db.Column(db.Integer, primary_key=True)

    spellcheck = db.Column(db.Boolean, default=True)
    dark_theme = db.Column(db.Boolean, default=False)
    language = db.Column(db.String(2))
    hotkeys = db.relationship("Hotkey", cascade="all, delete-orphan", lazy="joined")
    word_lists = db.relationship("WordList", secondary="user_profile_word_list", lazy="joined")

    def __init__(self, spellcheck, dark_theme, language, hotkeys, word_lists):
        """Initialize a User object with the given parameters.

        Args:
            spellcheck (bool): Indicates whether spellcheck is enabled for the user.
            dark_theme (bool): Indicates whether the user has enabled dark theme.
            language (str): The language preference of the user.
            hotkeys (list): A list of hotkeys configured by the user.
            word_lists (list): A list of WordList objects associated with the user.
        """
        self.id = None
        self.spellcheck = spellcheck
        self.dark_theme = dark_theme
        self.language = language
        self.hotkeys = hotkeys

        self.word_lists = []
        from model.word_list import WordList

        for word_list in word_lists:
            self.word_lists.append(WordList.find(word_list.id))


class UserProfileWordList(db.Model):
    """Model class representing the association table between UserProfile and WordList.

    Attributes:
        user_profile_id (int): The ID of the user profile.
        word_list_id (int): The ID of the word list.
    """

    user_profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id"), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id"), primary_key=True)


class Hotkey(db.Model):
    """Represents a hotkey for a user.

    Attributes:
        id (int): The unique identifier for the hotkey.
        key_code (int): The code of the key associated with the hotkey.
        key (str): The key associated with the hotkey.
        alias (str): The alias for the hotkey.
        user_profile_id (int): The foreign key referencing the user profile.
    Args:
        db.Model: The base class for all models in the application.
    """

    id = db.Column(db.Integer, primary_key=True)
    key_code = db.Column(db.Integer)
    key = db.Column(db.String)
    alias = db.Column(db.String)

    user_profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id"))

    def __init__(self, key_code, key, alias):
        """Initialize a User object.

        Args:
            key_code (str): The key code of the user.
            key (str): The key of the user.
            alias (str): The alias of the user.
        """
        self.id = None
        self.key_code = key_code
        self.key = key
        self.alias = alias
