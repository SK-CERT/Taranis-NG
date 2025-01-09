"""Module for Asset model."""

import uuid
from marshmallow import fields, post_load
from sqlalchemy import orm, func, or_, text

from managers.db_manager import db
from model.report_item import ReportItem
from model.user import User
from model.notification_template import NotificationTemplate
from shared.schema.asset import AssetCpeSchema, AssetSchema, AssetPresentationSchema, AssetGroupSchema, AssetGroupPresentationSchema
from shared.schema.user import UserIdSchema
from shared.schema.notification_template import NotificationTemplateIdSchema


class NewAssetCpeSchema(AssetCpeSchema):
    """A schema class for creating a new AssetCpe object.

    This schema inherits from the AssetCpeSchema class and provides a method
    for creating an AssetCpe object from the given data.

    Attributes:
        data (dict): The data used to create the AssetCpe object.

    Returns:
        AssetCpe: The created AssetCpe object.
    """

    @post_load
    def make(self, data, **kwargs):
        """Use decorator to create an instance of the AssetCpe class from the provided data.

        Args:
            data: A dictionary containing the data to initialize the AssetCpe instance.

        Returns:
            An instance of the AssetCpe class initialized with the provided data.
        """
        return AssetCpe(**data)


class AssetCpe(db.Model):
    """Represents an AssetCpe object.

    Attributes:
        id (int): The unique identifier of the AssetCpe.
        value (str): The value of the AssetCpe.
        asset_id (int): The foreign key referencing the associated Asset object.
    """

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String())
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))

    def __init__(self, value):
        """Initialize a new instance of the Asset class."""
        self.id = None
        self.value = value


class NewAssetSchema(AssetSchema):
    """Schema for creating a new asset.

    Attributes:
        asset_cpes (List[NewAssetCpeSchema]): A list of nested schemas for asset CPES.
    """

    asset_cpes = fields.Nested(NewAssetCpeSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Post-load method that creates an Asset instance from the given data.

        Args:
            data (dict): The data to create the Asset instance from.
            **kwargs: Additional keyword arguments.

        Returns:
            Asset: The created Asset instance.
        """
        return Asset(**data)


class Asset(db.Model):
    """Represents an asset in the system.

    Attributes:
        id (int): The unique identifier of the asset.
        name (str): The name of the asset.
        serial (str): The serial number of the asset.
        description (str): The description of the asset.
        asset_group_id (str): The ID of the asset group that the asset belongs to.
        asset_group (AssetGroup): The asset group that the asset belongs to.
        asset_cpes (list[AssetCpe]): The list of asset CPEs associated with the asset.
        vulnerabilities (list[AssetVulnerability]): The list of vulnerabilities associated with the asset.
        vulnerabilities_count (int): The count of vulnerabilities associated with the asset.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    serial = db.Column(db.String())
    description = db.Column(db.String())

    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"))
    asset_group = db.relationship("AssetGroup")
    asset_cpes = db.relationship("AssetCpe", cascade="all, delete-orphan")
    vulnerabilities = db.relationship("AssetVulnerability", cascade="all, delete-orphan")
    vulnerabilities_count = db.Column(db.Integer, default=0)

    def __init__(self, id, name, serial, description, asset_group_id, asset_cpes):
        """Initialize a new instance of the Asset class."""
        self.id = None
        self.name = name
        self.serial = serial
        self.description = description
        self.asset_group_id = asset_group_id
        self.asset_cpes = asset_cpes
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Use decorator to create an instance of the AssetCpe class from the provided data."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-laptop"

    @classmethod
    def get_by_cpe(cls, cpes):
        """Get assets by Common Platform Enumeration (CPE).

        Args:
            cpes: A list of CPE values.

        Returns:
            A list of assets matching the given CPE values.
        """
        if len(cpes) > 0:
            query_string = "SELECT DISTINCT asset_id FROM asset_cpe WHERE value LIKE ANY(:cpes) OR {}"
            params = {"cpes": cpes}

            inner_query = ""
            for i in range(len(cpes)):
                if i > 0:
                    inner_query += " OR "
                param = "cpe" + str(i)
                inner_query += ":" + param + " LIKE value"
                params[param] = cpes[i]

            result = db.engine.execute(text(query_string.format(inner_query)), params)

            return [db.session.get(cls, row._mapping[0]) for row in result]
        else:
            return []

    @classmethod
    def remove_vulnerability(cls, report_item_id):
        """Remove a vulnerability from the asset.

        Args:
            report_item_id: The ID of the report item associated with the vulnerability.
        """
        vulnerabilities = AssetVulnerability.get_by_report(report_item_id)
        for vulnerability in vulnerabilities:
            vulnerability.asset.vulnerabilities_count -= 1
            db.session.delete(vulnerability)

    def add_vulnerability(self, report_item):
        """Add a vulnerability to the asset.

        Args:
            report_item: The report item representing the vulnerability.
        """
        for vulnerability in self.vulnerabilities:
            if vulnerability.report_item.id == report_item.id:
                return

        vulnerability = AssetVulnerability(self.id, report_item.id)
        db.session.add(vulnerability)
        self.vulnerabilities_count += 1

    def update_vulnerabilities(self):
        """Update the vulnerabilities associated with the asset."""
        cpes = []
        for cpe in self.asset_cpes:
            cpes.append(cpe.value)

        report_item_ids = ReportItem.get_by_cpe(cpes)

        solved = []
        for vulnerability in self.vulnerabilities:
            if vulnerability.solved is True:
                solved.append(vulnerability.report_item_id)

        self.vulnerabilities = []
        self.vulnerabilities_count = 0
        for report_item_id in report_item_ids:
            vulnerability = AssetVulnerability(self.id, report_item_id)
            if report_item_id in solved:
                vulnerability.solved = True
            else:
                self.vulnerabilities_count += 1
            self.vulnerabilities.append(vulnerability)

    @classmethod
    def solve_vulnerability(cls, user, group_id, asset_id, report_item_id, solved):
        """Solves a vulnerability for a specific asset.

        Args:
            user (User): The user performing the action.
            group_id (int): The ID of the asset group.
            asset_id (int): The ID of the asset.
            report_item_id (int): The ID of the report item.
            solved (bool): Indicates whether the vulnerability is solved or not.
        """
        asset = db.session.get(cls, asset_id)
        if AssetGroup.access_allowed(user, asset.asset_group_id):
            for vulnerability in asset.vulnerabilities:
                if vulnerability.report_item_id == report_item_id:
                    if solved is not vulnerability.solved:
                        if solved is True:
                            asset.vulnerabilities_count -= 1
                        else:
                            asset.vulnerabilities_count += 1
                    vulnerability.solved = solved
                    db.session.commit()
                    return

    @classmethod
    def get(cls, group_id, search, sort, vulnerable):
        """Retrieve assets based on the provided parameters.

        Args:
            group_id (int): The ID of the asset group.
            search (str): The search string to filter assets by name, description, serial, or CPE value.
            sort (str): The sorting option for the assets. Can be "ALPHABETICAL" or "VULNERABILITIES_COUNT".
            vulnerable (str): Flag to filter assets by vulnerability count. Can be "true" or None.

        Returns:
            assets (list): A list of assets that match the provided parameters.
            count (int): The total count of assets that match the provided parameters.
        """
        query = cls.query.filter(Asset.asset_group_id == group_id)

        if vulnerable is not None:
            if vulnerable == "true":
                query = query.filter(Asset.vulnerabilities_count > 0)

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.join(AssetCpe, Asset.id == AssetCpe.asset_id).filter(
                or_(
                    func.lower(Asset.name).like(search_string),
                    func.lower(Asset.description).like(search_string),
                    func.lower(Asset.serial).like(search_string),
                    func.lower(AssetCpe.value).like(search_string),
                )
            )

        if sort is not None:
            if sort == "ALPHABETICAL":
                query = query.order_by(db.asc(Asset.name))
            else:
                query = query.order_by(db.desc(Asset.vulnerabilities_count))

        return query.all(), query.count()

    @classmethod
    def get_all_json(cls, user, group_id, search, sort, vulnerable):
        """Get all assets in JSON format.

        Args:
            user (User): The user object.
            group_id (int): The ID of the asset group.
            search (str): The search query for filtering assets.
            sort (str): The sorting criteria for assets.
            vulnerable (bool): Flag indicating whether to include vulnerable assets.

        Returns:
        dict: A dictionary containing the total count of assets and a list of asset items in JSON format.
        """
        if AssetGroup.access_allowed(user, group_id):
            assets, count = cls.get(group_id, search, sort, vulnerable)
            asset_schema = AssetPresentationSchema(many=True)
            items = asset_schema.dump(assets)
            return {"total_count": count, "items": items}

    @classmethod
    def add(cls, user, group_id, data):
        """Add a new asset to the database.

        Args:
            user (User): The user adding the asset.
            group_id (int): The ID of the asset group to which the asset belongs.
            data (dict): The data of the asset to be added.
        """
        schema = NewAssetSchema()
        asset = schema.load(data)
        asset.asset_group_id = group_id
        if AssetGroup.access_allowed(user, group_id):
            db.session.add(asset)
            asset.update_vulnerabilities()
            db.session.commit()

    @classmethod
    def update(cls, user, group_id, asset_id, data):
        """Update an asset with the provided data.

        Args:
            user (User): The user performing the update.
            group_id (int): The ID of the asset group.
            asset_id (int): The ID of the asset to update.
            data (dict): The data to update the asset with.
        """
        asset = db.session.get(cls, asset_id)
        if AssetGroup.access_allowed(user, asset.asset_group_id):
            schema = NewAssetSchema()
            updated_asset = schema.load(data)
            asset.name = updated_asset.name
            asset.serial = updated_asset.serial
            asset.description = updated_asset.description
            asset.asset_cpes = updated_asset.asset_cpes
            asset.update_vulnerabilities()
            db.session.commit()

    @classmethod
    def delete(cls, user, group_id, id):
        """Delete an asset.

        Args:
            user (User): The user performing the delete operation.
            group_id (int): The ID of the asset group.
            id (int): The ID of the asset to be deleted.
        """
        asset = db.session.get(cls, id)
        if AssetGroup.access_allowed(user, asset.asset_group_id):
            db.session.delete(asset)
            db.session.commit()


class AssetVulnerability(db.Model):
    """Represents a vulnerability associated with an asset.

    Attributes:
        id (int): The unique identifier of the vulnerability.
        solved (bool): Indicates whether the vulnerability has been solved or not.
        asset_id (int): The ID of the asset associated with the vulnerability.
        report_item_id (int): The ID of the report item associated with the vulnerability.
        report_item (ReportItem): The report item associated with the vulnerability.
    """

    id = db.Column(db.Integer, primary_key=True)
    solved = db.Column(db.Boolean, default=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"))
    report_item = db.relationship("ReportItem")

    def __init__(self, asset_id, report_item_id):
        """Initialize a new instance of the Asset class."""
        self.id = None
        self.asset_id = asset_id
        self.report_item_id = report_item_id

    @classmethod
    def get_by_report(cls, report_id):
        """Get assets by report ID.

        Args:
            report_id (int): The ID of the report.

        Returns:
            List[Asset]: A list of assets associated with the given report ID.
        """
        return cls.query.filter_by(report_item_id=report_id).all()


class NewAssetGroupGroupSchema(AssetGroupSchema):
    """Schema for creating a new asset group with additional fields.

    Attributes:
        users (list): A list of user IDs associated with the asset group.
        templates (list): A list of notification template IDs associated with the asset group.

    Returns:
        AssetGroup: An instance of the AssetGroup class.
    """

    users = fields.Nested(UserIdSchema, many=True)
    templates = fields.Nested(NotificationTemplateIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        """Use decorator to create an instance of the AssetGroup class from the provided data.

        Args:
            data: A dictionary containing the data to initialize the AssetGroup instance.

        Returns:
            An instance of the AssetGroup class.
        """
        return AssetGroup(**data)


class AssetGroup(db.Model):
    """AssetGroup class represents a group of assets in the system.

    Attributes:
        id (str): The unique identifier of the asset group.
        name (str): The name of the asset group.
        description (str): The description of the asset group.
        templates (list): The list of notification templates associated with the asset group.
        organizations (list): The list of organizations associated with the asset group.
        users (list): The list of users associated with the asset group.
        title (str): The title of the asset group.
        subtitle (str): The subtitle of the asset group.
        tag (str): The tag of the asset group.
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    templates = db.relationship("NotificationTemplate", secondary="asset_group_notification_template")

    organizations = db.relationship("Organization", secondary="asset_group_organization")
    users = db.relationship("User", secondary="asset_group_user")

    def __init__(self, id, name, description, users, templates):
        """Initialize an instance of the Asset class."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.organizations = []
        self.users = []
        for user in users:
            self.users.append(User.find_by_id(user.id))

        self.templates = []
        for template in templates:
            self.templates.append(NotificationTemplate.find(template.id))

        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the asset object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-folder-multiple"

    @classmethod
    def find(cls, group_id):
        """Find an asset group by its ID.

        Args:
            group_id (int): The ID of the asset group to find.

        Returns:
            group (AssetGroup): The asset group with the specified ID.
        """
        group = db.session.get(cls, group_id)
        return group

    @classmethod
    def access_allowed(cls, user, group_id):
        """
        Check if the access is allowed for a user in a specific group.

        Args:
            user: The user object representing the user.
            group_id: The ID of the group to check access for.

        Returns:
            True if the access is allowed, False otherwise.
        """
        group = db.session.get(cls, group_id)
        return any(org in user.organizations for org in group.organizations)

    @classmethod
    def get(cls, search, organization):
        """
        Get assets based on search criteria and organization.

        Args:
            search (str): A string representing the search criteria.
            organization: An organization object to filter the assets by.

        Returns:
            A tuple containing a list of assets and the count of assets.
        """
        query = cls.query

        if organization is not None:
            query = query.join(AssetGroupOrganization, AssetGroup.id == AssetGroupOrganization.asset_group_id)

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(or_(func.lower(AssetGroup.name).like(search_string), func.lower(AssetGroup.description).like(search_string)))

        return query.order_by(db.asc(AssetGroup.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, user, search):
        """Get all assets in JSON format.

        Args:
            user (User): The user object.
            search (str): The search query.

        Returns:
            dict: A dictionary containing the total count of assets and a list of asset groups in JSON format.
        """
        if user.organizations:
            groups, count = cls.get(search, user.organizations[0])
        else:
            return {"total_count": 0, "items": []}
        permissions = user.get_permissions()
        if "MY_ASSETS_CONFIG" not in permissions:
            for group in groups[:]:
                if len(group.users) > 0:
                    found = False
                    for accessed_user in group.users:
                        if accessed_user.id == user.id:
                            found = True
                            break

                    if found is False:
                        groups.remove(group)
                        count -= 1

        group_schema = AssetGroupPresentationSchema(many=True)
        return {"total_count": count, "items": group_schema.dump(groups)}

    @classmethod
    def add(cls, user, data):
        """Add a new asset group to the database.

        Args:
            user: The user object representing the user adding the asset group.
            data: The data containing the information for the new asset group.
        """
        new_group_schema = NewAssetGroupGroupSchema()
        group = new_group_schema.load(data)
        group.organizations = user.organizations
        for added_user in group.users[:]:
            if not any(org in added_user.organizations for org in group.organizations):
                group.users.remove(added_user)

        for added_template in group.templates[:]:
            if not any(org in added_template.organizations for org in group.organizations):
                group.temlates.remove(added_template)

        db.session.add(group)
        db.session.commit()

    @classmethod
    def delete(cls, user, group_id):
        """Delete a group if the user belongs to any of the organizations associated with the group.

        Args:
            cls (class): The class object.
            user (User): The user object.
            group_id (int): The ID of the group to be deleted.
        """
        group = db.session.get(cls, group_id)
        if any(org in user.organizations for org in group.organizations):
            db.session.delete(group)
            db.session.commit()

    @classmethod
    def update(cls, user, group_id, data):
        """Update an asset group with the provided data.

        Args:
            cls: The class object.
            user: The user performing the update.
            group_id: The ID of the asset group to update.
            data: The data to update the asset group with.
        """
        new_group_schema = NewAssetGroupGroupSchema()
        updated_group = new_group_schema.load(data)
        group = db.session.get(cls, group_id)
        if any(org in user.organizations for org in group.organizations):
            group.name = updated_group.name
            group.description = updated_group.description
            group.users = []
            for added_user in updated_group.users:
                if any(org in added_user.organizations for org in group.organizations):
                    group.users.append(added_user)

            group.templates = []
            for added_template in updated_group.templates:
                if any(org in added_template.organizations for org in group.organizations):
                    group.templates.append(added_template)

            db.session.commit()


class AssetGroupOrganization(db.Model):
    """AssetGroupOrganization represents the relationship between an asset group and an organization.

    Attributes:
        asset_group_id (str): The ID of the asset group.
        organization_id (int): The ID of the organization.
    """

    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), primary_key=True)


class AssetGroupUser(db.Model):
    """AssetGroupUser model represents the association between an AssetGroup and a User.

    Attributes:
        asset_group_id (str): The ID of the associated AssetGroup.
        user_id (int): The ID of the associated User.
    """

    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)


class AssetGroupNotificationTemplate(db.Model):
    """AssetGroupNotificationTemplate model represents the association between an Asset Group and a Notification Template.

    Attributes:
        asset_group_id (str): The ID of the associated Asset Group.
        notification_template_id (int): The ID of the associated Notification Template.
    """

    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"), primary_key=True)
    notification_template_id = db.Column(db.Integer, db.ForeignKey("notification_template.id"), primary_key=True)
