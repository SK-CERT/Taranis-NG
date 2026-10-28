"""ProductType model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.parameter_value import ParameterValue
    from model.user import User


import datetime as dt

import sqlalchemy
from managers import content_language
from managers.db_manager import db
from marshmallow import fields, post_load
from model.acl_entry import ACLEntry
from model.parameter import Parameter
from model.parameter_value import NewParameterValueSchema, ParameterValue
from model.presenter import Presenter
from model.product import Product
from shared.schema.acl_entry import ItemType
from shared.schema.product_type import ProductTypePresentationSchema, ProductTypeSchema
from sqlalchemy import and_, or_, orm
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import cast


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
        language: Language its default templates are written in; None while not stated
        language_templates: Template paths per language, ``{language: {PARAM_TEMPLATE_PATH: path}}``;
            a template a language does not name is taken from the default set
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(), nullable=False)

    created = db.Column(db.DateTime, default=dt.datetime.now(dt.UTC))

    presenter_id = db.Column(db.String, db.ForeignKey("presenter.id"))
    presenter = db.relationship("Presenter")

    parameter_values = db.relationship("ParameterValue", secondary="product_type_parameter_value", cascade="all")

    language = db.Column(db.String(8), nullable=True)
    language_templates = db.Column(JSONB, nullable=False, default=dict, server_default=sqlalchemy.text("'{}'"))

    def __init__(
        self,
        id: int,  # noqa: A002, ARG002
        title: str,
        description: str,
        presenter_id: str,
        parameter_values: list[ParameterValue],
        language: str | None = None,
        language_templates: dict | None = None,
    ) -> None:
        """Initialize product type.

        Raises:
            ValueError: If the language is not an ISO 639-1 code.
        """
        self.id = None
        self.title = title
        self.description = description
        self.presenter_id = presenter_id
        self.parameter_values = parameter_values
        self.language = content_language.clean_language(language)
        # Checked against the presenter's template parameters by add_new / update.
        self.language_templates = language_templates or {}
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
        presenter = db.session.get(Presenter, product_type.presenter_id) if product_type.presenter_id else None
        product_type.language_templates = content_language.clean_language_templates(
            product_type.language_templates,
            cls.template_keys(presenter),
        )
        db.session.add(product_type)
        db.session.commit()

    @staticmethod
    def template_keys(presenter: Presenter | None) -> list[str]:
        """The presenter's parameters that hold a template path; only they vary per language.

        Args:
            presenter (Presenter | None): The presenter.

        Returns:
            list[str]: Parameter keys ending in a language-varying suffix.
        """
        if presenter is None:
            return []
        return [parameter.key for parameter in presenter.parameters if parameter.key.endswith(content_language.TEMPLATE_SUFFIX)]

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

        if updated_product_type.presenter_id and updated_product_type.presenter_id != product_type.presenter_id:
            target_presenter = db.session.get(Presenter, updated_product_type.presenter_id)
            if target_presenter is None:
                msg = f"Target presenter {updated_product_type.presenter_id} not found"
                raise ValueError(msg)
            product_type.presenter_id = target_presenter.id

        product_type.language = updated_product_type.language
        presenter = db.session.get(Presenter, product_type.presenter_id) if product_type.presenter_id else None
        product_type.language_templates = content_language.clean_language_templates(
            updated_product_type.language_templates,
            cls.template_keys(presenter),
        )

        # existing parameters are updated
        for value in product_type.parameter_values:
            for updated_value in updated_product_type.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value
        # create missing parameters (re-save old version, re-assigning no new type)
        id_param_lookup = {param.parameter.id: param for param in product_type.parameter_values}
        for par in updated_product_type.parameter_values:
            if par.parameter_id not in id_param_lookup:
                param = Parameter.find(par.parameter_id)
                new_parameter_value = ParameterValue(par.value, param)
                product_type.parameter_values.append(new_parameter_value)
        # delete removed parameters
        for value in product_type.parameter_values:
            for updated_value in updated_product_type.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    break
            else:
                db.session.delete(value)

        db.session.commit()


class ProductTypeParameterValue(db.Model):
    """Product type parameter value model.

    Attributes:
        product_type_id: Product type id
        parameter_value_id: Parameter value id
    """

    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
