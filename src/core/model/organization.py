"""Organization model."""

from marshmallow import post_load, fields
from sqlalchemy import or_, orm

from managers.db_manager import db
from model.address import NewAddressSchema
from shared.schema.organization import OrganizationSchema, OrganizationPresentationSchema


class NewOrganizationSchema(OrganizationSchema):
    """This schema is used to create a new organization.

    Attributes:
        address (NewAddressSchema): The address of the organization
    """

    address = fields.Nested(NewAddressSchema)

    @post_load
    def make(self, data, **kwargs):
        """Create a new organization object.

        Args:
            data (dict): The data to create the organization object.
        Returns:
            Organization: The new organization object.
        """
        return Organization(**data)


class Organization(db.Model):
    """Organization model.

    Attributes:
        id (int): The organization id.
        name (str): The organization name.
        description (str): The organization description.
        address_id (int): The address id.
        address (Address): The address of the organization.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    address = db.relationship("Address", cascade="all")

    def __init__(self, id, name, description, address):
        """Initialize the organization object."""
        self.id = None
        self.name = name
        self.description = description
        self.address = address
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the organization object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-office-building"

    @classmethod
    def find(cls, organization_id):
        """Find an organization by id.

        Args:
            organization_id (int): The organization id.
        Returns:
            Organization: The organization object.
        """
        organization = db.session.get(cls, organization_id)
        return organization

    @classmethod
    def get_all(cls):
        """Get all organizations.

        Returns:
            list: The list of all organizations.
        """
        return cls.query.order_by(db.asc(Organization.name)).all()

    @classmethod
    def get(cls, search):
        """Get all organizations with search.

        Args:
            search (str): The search string.
        Returns:
            tuple: The list of organizations and the count of organizations.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(Organization.name.ilike(search_string), Organization.description.ilike(search_string)))

        return query.order_by(db.asc(Organization.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Get all organizations with search in JSON format.

        Args:
            search (str): The search string.
        Returns:
            dict: The organizations in JSON format.
        """
        organizations, count = cls.get(search)
        organizations_schema = OrganizationPresentationSchema(many=True)
        return {"total_count": count, "items": organizations_schema.dump(organizations)}

    @classmethod
    def add_new(cls, data):
        """Add a new organization.

        Args:
            data (dict): The data to create the new organization.
        """
        new_organization_schema = NewOrganizationSchema()
        organization = new_organization_schema.load(data)
        db.session.add(organization.address)
        db.session.add(organization)
        db.session.commit()

    @classmethod
    def update(cls, organization_id, data):
        """Update an organization.

        Args:
            organization_id (int): The organization id.
            data (dict): The data to update the organization.
        """
        schema = NewOrganizationSchema()
        updated_organization = schema.load(data)
        organization = db.session.get(cls, organization_id)
        organization.name = updated_organization.name
        organization.description = updated_organization.description
        organization.address.street = updated_organization.address.street
        organization.address.city = updated_organization.address.city
        organization.address.zip = updated_organization.address.zip
        organization.address.country = updated_organization.address.country
        db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete an organization.

        Args:
            id (int): The organization id.
        """
        organization = db.session.get(cls, id)
        db.session.delete(organization)
        db.session.commit()
