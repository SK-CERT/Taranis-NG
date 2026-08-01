"""Organization model."""

from __future__ import annotations

from managers.db_manager import db
from marshmallow import fields, post_load
from model.address import Address, NewAddressSchema
from shared.schema.organization import OrganizationPresentationSchema, OrganizationSchema
from sqlalchemy import or_, orm


class NewOrganizationSchema(OrganizationSchema):
    """This schema is used to create a new organization.

    Attributes:
        address (NewAddressSchema): The address of the organization
    """

    address = fields.Nested(NewAddressSchema)

    @post_load
    def make(self, data: dict, **kwargs) -> Organization:  # noqa: ANN003, ARG002
        """Create a new organization object.

        Args:
            data (dict): The data to create the organization object.
            **kwargs: Additional keyword arguments.

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
        require_mfa (bool): Whether members must have a second factor.
        address_id (int): The address id.
        address (Address): The address of the organization.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    require_mfa = db.Column(db.Boolean, nullable=False, default=False, server_default="false")

    address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    address = db.relationship("Address", cascade="all")

    def __init__(
        self,
        id: int | None,  # noqa: A002, ARG002
        name: str,
        description: str,
        address: Address,
        require_mfa: bool = False,
    ) -> None:
        """Initialize the organization object."""
        self.id = None
        self.name = name
        self.description = description
        self.require_mfa = bool(require_mfa)
        self.address = address
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct the organization object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-office-building"

    @classmethod
    def find(cls, organization_id: int) -> Organization | None:
        """Find an organization by id.

        Args:
            organization_id (int): The organization id.

        Returns:
            Organization: The organization object.
        """
        return db.session.get(cls, organization_id)

    @classmethod
    def get_all(cls) -> list[Organization]:
        """Get all organizations.

        Returns:
            list: The list of all organizations.
        """
        return cls.query.order_by(db.asc(Organization.name)).all()

    @classmethod
    def get(cls, search: str | None) -> tuple[list[Organization], int]:
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
    def get_all_json(cls, search: str | None) -> dict:
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
    def add_new(cls, data: dict) -> None:
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
    def update(cls, organization_id: int, data: dict) -> None:
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
        organization.require_mfa = updated_organization.require_mfa
        organization.address.street = updated_organization.address.street
        organization.address.city = updated_organization.address.city
        organization.address.zip = updated_organization.address.zip
        organization.address.country = updated_organization.address.country
        db.session.commit()

    @classmethod
    def delete(cls, id: int) -> None:  # noqa: A002
        """Delete an organization.

        Args:
            id (int): The organization id.
        """
        organization = db.session.get(cls, id)
        db.session.delete(organization)
        db.session.commit()
