"""ProductType model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.parameter_value import ParameterValue
    from model.user import User


import datetime

import sqlalchemy
from managers.db_manager import db
from marshmallow import fields, post_load
from model.acl_entry import ACLEntry
from model.parameter_value import NewParameterValueSchema
from model.product import Product
from sqlalchemy import and_, or_, orm
from sqlalchemy.sql.expression import cast

from shared.schema.acl_entry import ItemType
from shared.schema.product_type import ProductTypePresentationSchema, ProductTypeSchema


class NewProductTypeSchema(ProductTypeSchema):
    """New product type schema.

    Attributes:
        parameter_values: List of parameter values
    """

    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> ProductType:  # noqa: ARG002, ANN003
        """Create a new product type.

        Args:
            data: Product type data
            **kwargs: Additional arguments.

        Returns:
            ProductType: New product type
        """
        return ProductType(**data)


class ProductType(db.Model):
    """Product type model.

    Attributes:
        id: Product type id
        title: Product type title
        description: Product type description
        created: Product type creation date
        presenter_id: Presenter GUID
        presenter: Presenter
        parameter_values: List of parameter values
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(), nullable=False)

    created = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    presenter_id = db.Column(db.String, db.ForeignKey("presenter.id"))
    presenter = db.relationship("Presenter")

    parameter_values = db.relationship("ParameterValue", secondary="product_type_parameter_value", cascade="all")

    def __init__(
        self,
        id: int,  # noqa: A002, ARG002
        title: str,
        description: str,
        presenter_id: str,
        parameter_values: list[ParameterValue],
    ) -> None:
        """Initialize product type."""
        self.id = None
        self.title = title
        self.description = description
        self.presenter_id = presenter_id
        self.parameter_values = parameter_values
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct product type."""
        self.subtitle = self.description
        self.tag = "mdi-file-document-outline"

    @classmethod
    def get_all(cls) -> list[ProductType]:
        """Get all product types.

        Returns:
            List[ProductType]: List of product types
        """
        return cls.query.order_by(db.asc(ProductType.title)).all()

    @classmethod
    def allowed_with_acl(cls, product_type_id: int, user: User, see: bool, access: bool, modify: bool) -> bool:
        """Check if user is allowed to access product type.

        Args:
            product_type_id: Product id
            user: User
            see: See permission
            access: Access permission
            modify: Modify permission
        Returns:
            bool: True if user is allowed to access product type
        """
        query = db.session.query(ProductType.id).distinct().group_by(ProductType.id).filter(ProductType.id == product_type_id)

        query = query.outerjoin(
            ACLEntry,
            and_(cast(ProductType.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.PRODUCT_TYPE),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def allowed_product_with_acl(cls, product_id: int, user: User, see: bool, access: bool, modify: bool) -> bool:
        """Check if user is allowed to access product's product type.

        Args:
            product_id: Product id
            user: User
            see: See permission
            access: Access permission
            modify: Modify permission
        Returns:
            bool: True if user is allowed to access product's product type
        """
        product = db.session.query(Product).filter_by(id=product_id).first()
        if not product:
            return False

        return cls.allowed_with_acl(product.product_type_id, user, see, access, modify)

    @classmethod
    def get(cls, search: str, user: User, acl_check: bool) -> tuple[list[ProductType], int]:
        """Get product types.

        Args:
            search: Search string
            user: User
            acl_check: ACL check
        Returns:
            List[ProductType]: List of product types
            int: Number of product types
        """
        query = cls.query.distinct().group_by(ProductType.id)

        if acl_check:
            query = query.outerjoin(
                ACLEntry,
                and_(cast(ProductType.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.PRODUCT_TYPE),
            )
            query = ACLEntry.apply_query(query, user, see=True, access=False, modify=False)

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(ProductType.title.ilike(search_string), ProductType.description.ilike(search_string)))

        return query.order_by(db.asc(ProductType.title)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str, user: User, acl_check: bool) -> dict:
        """Get all product types as JSON.

        Args:
            search: Search string
            user: User
            acl_check: ACL check
        Returns:
            dict: Product types
        """
        product_types, count = cls.get(search, user, acl_check)
        product_type_schema = ProductTypePresentationSchema(many=True)
        return {"total_count": count, "items": product_type_schema.dump(product_types)}

    @classmethod
    def add_new(cls, data: dict) -> None:
        """Add a new product type.

        Args:
            data: Product type data
        """
        new_product_type_schema = NewProductTypeSchema()
        product_type = new_product_type_schema.load(data)
        db.session.add(product_type)
        db.session.commit()

    @classmethod
    def delete(cls, product_type_id: int) -> None:
        """Delete a product type.

        Args:
            product_type_id: Product type id
        """
        product_type = db.session.get(cls, product_type_id)
        db.session.delete(product_type)
        db.session.commit()

    @classmethod
    def update(cls, product_type_id: int, data: dict) -> None:
        """Update a product type.

        Args:
            product_type_id: Product type id
            data: Product type data
        """
        new_product_type_schema = NewProductTypeSchema()
        updated_product_type = new_product_type_schema.load(data)
        product_type = db.session.get(cls, product_type_id)
        product_type.title = updated_product_type.title
        product_type.description = updated_product_type.description

        for value in product_type.parameter_values:
            for updated_value in updated_product_type.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value

        db.session.commit()


class ProductTypeParameterValue(db.Model):
    """Product type parameter value model.

    Attributes:
        product_type_id: Product type id
        parameter_value_id: Parameter value id
    """

    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
