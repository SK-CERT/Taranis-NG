"""ProductFormat model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.parameter_value import ParameterValue


import datetime as dt

import sqlalchemy
from managers import content_language
from managers.db_manager import db
from marshmallow import fields, post_load
from model.parameter import Parameter
from model.parameter_value import NewParameterValueSchema, ParameterValue
from model.presenter import Presenter
from shared.schema.product_format import ProductFormatPresentationSchema, ProductFormatSchema
from sqlalchemy import or_, orm
from sqlalchemy.dialects.postgresql import JSONB


class NewProductFormatSchema(ProductFormatSchema):
    """New product format schema.

    Attributes:
        parameter_values: List of parameter values
    """

    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> ProductFormat:  # noqa: ARG002, ANN003
        """Create a new product format.

        Args:
            data: Product format data
            **kwargs: Additional arguments.

        Returns:
            ProductFormat: New product format
        """
        return ProductFormat(**data)


class ProductFormat(db.Model):
    """Product format model.

    Attributes:
        id: Product format id
        title: Product format title
        description: Product format description
        created: Product format creation date
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

    parameter_values = db.relationship("ParameterValue", secondary="product_format_parameter_value", cascade="all")

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
        """Initialize product format.

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
        """Reconstruct product format."""
        self.subtitle = self.description
        self.tag = "mdi-file-document-outline"

    @classmethod
    def get_all(cls) -> list[ProductFormat]:
        """Get all product formats.

        Returns:
            List[ProductFormat]: List of product formats
        """
        return cls.query.order_by(db.asc(ProductFormat.title)).all()

    @classmethod
    def get(cls, search: str | None) -> tuple[list[ProductFormat], int]:
        """Get product formats.

        Who may use a product format is decided by the product presets it is part of.

        Args:
            search: Search string
        Returns:
            List[ProductFormat]: List of product formats
            int: Number of product formats
        """
        query = cls.query.distinct().group_by(ProductFormat.id)

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(ProductFormat.title.ilike(search_string), ProductFormat.description.ilike(search_string)))

        return query.order_by(db.asc(ProductFormat.title)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None) -> dict:
        """Get all product formats as JSON.

        Args:
            search: Search string
        Returns:
            dict: Product formats
        """
        product_formats, count = cls.get(search)
        product_format_schema = ProductFormatPresentationSchema(many=True)
        return {"total_count": count, "items": product_format_schema.dump(product_formats)}

    @classmethod
    def add_new(cls, data: dict) -> None:
        """Add a new product format.

        Args:
            data: Product format data
        """
        new_product_format_schema = NewProductFormatSchema()
        product_format = new_product_format_schema.load(data)
        presenter = db.session.get(Presenter, product_format.presenter_id) if product_format.presenter_id else None
        product_format.language_templates = content_language.clean_language_templates(
            product_format.language_templates,
            cls.template_keys(presenter),
        )
        db.session.add(product_format)
        db.session.commit()

    @staticmethod
    def template_keys(presenter: Presenter | None) -> list[str]:
        """The presenter's parameters enabled for language-specific values.

        Args:
            presenter (Presenter | None): The presenter.

        Returns:
            list[str]: Keys of parameters marked translatable.
        """
        if presenter is None:
            return []
        return [parameter.key for parameter in presenter.parameters if parameter.translate]

    @classmethod
    def delete(cls, product_format_id: int) -> None:
        """Delete a product format.

        Args:
            product_format_id: Product format id
        """
        product_format = db.session.get(cls, product_format_id)
        db.session.delete(product_format)
        db.session.commit()

    @classmethod
    def update(cls, product_format_id: int, data: dict) -> None:
        """Update a product format.

        Args:
            product_format_id: Product format id
            data: Product format data
        """
        new_product_format_schema = NewProductFormatSchema()
        updated_product_format = new_product_format_schema.load(data)
        product_format = db.session.get(cls, product_format_id)
        product_format.title = updated_product_format.title
        product_format.description = updated_product_format.description

        if updated_product_format.presenter_id and updated_product_format.presenter_id != product_format.presenter_id:
            target_presenter = db.session.get(Presenter, updated_product_format.presenter_id)
            if target_presenter is None:
                msg = f"Target presenter {updated_product_format.presenter_id} not found"
                raise ValueError(msg)
            product_format.presenter_id = target_presenter.id

        product_format.language = updated_product_format.language
        presenter = db.session.get(Presenter, product_format.presenter_id) if product_format.presenter_id else None
        product_format.language_templates = content_language.clean_language_templates(
            updated_product_format.language_templates,
            cls.template_keys(presenter),
        )

        # existing parameters are updated
        for value in product_format.parameter_values:
            for updated_value in updated_product_format.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value
        # create missing parameters (re-save old version, re-assigning no new type)
        id_param_lookup = {param.parameter.id: param for param in product_format.parameter_values}
        for par in updated_product_format.parameter_values:
            if par.parameter_id not in id_param_lookup:
                param = Parameter.find(par.parameter_id)
                new_parameter_value = ParameterValue(par.value, param)
                product_format.parameter_values.append(new_parameter_value)
        # delete removed parameters
        for value in product_format.parameter_values:
            for updated_value in updated_product_format.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    break
            else:
                db.session.delete(value)

        db.session.commit()


class ProductFormatParameterValue(db.Model):
    """Product format parameter value model.

    Attributes:
        product_format_id: Product format id
        parameter_value_id: Parameter value id
    """

    product_format_id = db.Column(db.Integer, db.ForeignKey("product_format.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
