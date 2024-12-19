"""ProductType model."""

import datetime
from marshmallow import post_load, fields
from sqlalchemy import func, or_, orm, and_
import sqlalchemy
from sqlalchemy.sql.expression import cast

from managers.db_manager import db
from model.product import Product
from model.parameter_value import NewParameterValueSchema
from model.acl_entry import ACLEntry
from shared.schema.acl_entry import ItemType
from shared.schema.product_type import ProductTypePresentationSchema, ProductTypeSchema


class NewProductTypeSchema(ProductTypeSchema):
    """New product type schema.

    Attributes:
        parameter_values: List of parameter values
    """

    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        """Create a new product type.

        Args:
            data: Product type data
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
        presenter_id: Presenter id
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

    def __init__(self, id, title, description, presenter_id, parameter_values):
        """Initialize product type."""
        self.id = None
        self.title = title
        self.description = description
        self.presenter_id = presenter_id
        self.parameter_values = parameter_values
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct product type."""
        self.subtitle = self.description
        self.tag = "mdi-file-document-outline"

    @classmethod
    def get_all(cls):
        """Get all product types.

        Returns:
            List[ProductType]: List of product types
        """
        return cls.query.order_by(db.asc(ProductType.title)).all()

    @classmethod
    def allowed_with_acl(cls, product_id, user, see, access, modify):
        """Check if user is allowed to access product type.

        Args:
            product_id: Product id
            user: User
            see: See permission
            access: Access permission
            modify: Modify permission
        Returns:
            bool: True if user is allowed to access product type
        """
        product = db.session.query(Product).filter_by(id=product_id).first()
        if not product:
            return False

        query = db.session.query(ProductType.id).distinct().group_by(ProductType.id).filter(ProductType.id == product.product_type_id)

        query = query.outerjoin(
            ACLEntry, and_(cast(ProductType.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.PRODUCT_TYPE)
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get(cls, search, user, acl_check):
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

        if acl_check is True:
            query = query.outerjoin(
                ACLEntry, and_(cast(ProductType.id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.PRODUCT_TYPE)
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(
                or_(func.lower(ProductType.title).like(search_string), func.lower(ProductType.description).like(search_string))
            )

        return query.order_by(db.asc(ProductType.title)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
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
    def add_new(cls, data):
        """Add a new product type.

        Args:
            data: Product type data
        """
        new_product_type_schema = NewProductTypeSchema()
        product_type = new_product_type_schema.load(data)
        db.session.add(product_type)
        db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete a product type.

        Args:
            id: Product type id
        """
        product_type = db.session.get(cls, id)
        db.session.delete(product_type)
        db.session.commit()

    @classmethod
    def update(cls, preset_id, data):
        """Update a product type.

        Args:
            preset_id: Product type id
            data: Product type data
        """
        new_product_type_schema = NewProductTypeSchema()
        updated_product_type = new_product_type_schema.load(data)
        product_type = db.session.get(cls, preset_id)
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
