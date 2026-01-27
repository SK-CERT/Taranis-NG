"""Product model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.product import Product

from datetime import datetime, timedelta

import sqlalchemy
from managers.db_manager import db
from marshmallow import fields, post_load
from model.acl_entry import ACLEntry
from model.report_item import ReportItem
from model.state import StateDefinition, StateEnum
from sqlalchemy import and_, func, or_, orm
from sqlalchemy.sql.expression import cast

from shared.common import TZ
from shared.log_manager import logger
from shared.schema.acl_entry import ItemType
from shared.schema.product import ProductPresentationSchema, ProductSchemaBase
from shared.schema.report_item import ReportItemIdSchema


class NewProductSchema(ProductSchemaBase):
    """New product schema.

    Attributes:
        report_items: List of report items
    """

    report_items = fields.Nested(ReportItemIdSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> Product:  # noqa: ARG002, ANN003
        """Create a new product.

        Args:
            data: Product data
            **kwargs: Additional keyword arguments from marshmallow

        Returns:
            Product: New product
        """
        return Product(**data)


class Product(db.Model):
    """Product model.

    Attributes:
        id: Product id
        title: Product title
        description: Product description
        created: Product creation date
        product_type_id: Product type id
        product_type: Product type
        user_id: User id
        user: User
        report_items: List of report items
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.now)

    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id"))
    product_type = db.relationship("ProductType")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User")

    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=True)
    state = db.relationship(StateDefinition, lazy="select")  # must be "select" to avoid join issues in get()

    report_items = db.relationship("ReportItem", secondary="product_report_item")

    def __init__(self, id: int, title: str, description: str, product_type_id: int, state_id: int, report_items: list[ReportItem]) -> None:  # noqa: A002
        """Initialize a product."""
        if id != -1:
            self.id = id
        else:
            self.id = None

        self.title = title
        self.description = description
        self.product_type_id = product_type_id
        self.state_id = state_id
        self.subtitle = ""
        self.tag = ""

        self.report_items = []
        for report_item in report_items:
            self.report_items.append(ReportItem.find(report_item.id))

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct a product."""
        self.subtitle = self.description
        self.tag = "mdi-file-pdf-outline"

    @classmethod
    def count_by_states(cls) -> dict:
        """Count products by their states.

        Returns:
            dict: Dictionary with state names as keys and counts as values
        """
        try:
            state_counts = {}
            result = (
                db.session.query(
                    cls.state_id,
                    db.func.count(cls.id).label("count"),
                    StateDefinition.display_name,
                    StateDefinition.color,
                    StateDefinition.icon,
                )
                .outerjoin(StateDefinition, StateDefinition.id == cls.state_id)
                .group_by(
                    cls.state_id,
                    StateDefinition.display_name,
                    StateDefinition.color,
                    StateDefinition.icon,
                )
                .order_by(db.asc(func.count(cls.id)))
                .all()
            )
            for _state_id, count, display_name, color, icon in result:
                disp = "no_state" if display_name is None else display_name
                col = "#9E9E9E" if color is None else color
                ico = "mdi-help" if icon is None else icon

                state_counts[disp] = {
                    "count": count,
                    "display_name": disp,
                    "color": col,
                    "icon": ico,
                }
            return state_counts

        except Exception as error:
            # Fallback if state system not available
            logger.exception(f"Error counting products by states: {error}")
            return {}

    @classmethod
    def find(cls, product_id: int) -> Product:
        """Find a product.

        Args:
            product_id: Product id
        Returns:
            Product: Product
        """
        return db.session.get(cls, product_id)

    @classmethod
    def get_detail_json(cls, product_id: int) -> dict:
        """Get product detail.

        Args:
            product_id: Product id
        Returns:
            dict: Product detail
        """
        product = db.session.get(cls, product_id)
        products_schema = ProductPresentationSchema()
        return products_schema.dump(product)

    @classmethod
    def get(cls, filter: dict, offset: int, limit: int, user: object) -> tuple[list, int]:  # noqa: A002
        """Get products.

        Args:
            filter: Filter
            offset: Offset
            limit: Limit
            user: User
        Returns:
            list: List of products
            int: Number of products
        """
        query = (
            db.session.query(
                Product,
                func.count().filter(ACLEntry.id > 0).label("acls"),
                func.count().filter(ACLEntry.access.is_(True)).label("access"),
                func.count().filter(ACLEntry.modify.is_(True)).label("modify"),
            )
            .distinct()
            .group_by(Product.id)
        )
        query = query.outerjoin(
            ACLEntry,
            and_(
                cast(Product.product_type_id, sqlalchemy.String) == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.PRODUCT_TYPE,
            ),
        )
        query = ACLEntry.apply_query(query, user, see=True, access=False, modify=False)

        if "search" in filter and filter["search"] != "":
            search_string = "%" + filter["search"] + "%"
            query = query.filter(or_(Product.title.ilike(search_string), Product.description.ilike(search_string)))

        if filter.get("published", "").lower() == "true":
            published_state = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
            if published_state:
                query = query.filter(Product.state_id == published_state.id)

        if filter.get("unpublished", "").lower() == "true":
            published_state = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
            if published_state:
                query = query.filter(or_(Product.state_id != published_state.id, Product.state_id.is_(None)))

        if "range" in filter and filter["range"] != "ALL":
            date_limit = datetime.now(tz=TZ)
            if filter["range"] == "TODAY":
                date_limit = date_limit.replace(hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "WEEK":
                date_limit = date_limit.replace(day=date_limit.day - date_limit.weekday(), hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "MONTH":
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "LAST_7_DAYS":
                date_limit = date_limit - timedelta(days=7)

            if filter["range"] == "LAST_31_DAYS":
                date_limit = date_limit - timedelta(days=31)

            if filter["range"] == "DATE":
                date_limit = datetime.fromisoformat(filter["date_from"])
                date_to = datetime.fromisoformat(filter["date_to"])
                query = query.filter(Product.created <= date_to)

            query = query.filter(Product.created >= date_limit)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(Product.created))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(Product.created))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_json(cls, filter: dict, offset: int, limit: int, user: object) -> dict:  # noqa: A002
        """Get products.

        Args:
            filter: Filter
            offset: Offset
            limit: Limit
            user: User
        Returns:
            dict: {total_count, items}
        """
        results, count = cls.get(filter, offset, limit, user)
        products = []
        for result in results:
            product = result.Product
            product.see = True
            product.access = result.access > 0 or result.acls == 0
            product.modify = result.modify > 0 or result.acls == 0
            products.append(product)

            for report_item in product.report_items:
                report_item.see = True
                report_item.access = True
                report_item.modify = True

        products_schema = ProductPresentationSchema(many=True)
        return {"total_count": count, "items": products_schema.dump(products)}

    @classmethod
    def add_product(cls, product_data: dict, user_id: int) -> Product:
        """Add a product.

        Args:
            product_data: Product data
            user_id: User id
        Returns:
            Product: New product
        """
        product_schema = NewProductSchema()
        product = product_schema.load(product_data)

        product.user_id = user_id
        db.session.add(product)
        db.session.commit()

        return product

    @classmethod
    def update_product(cls, product_id: int, product_data: dict) -> None:
        """Update a product.

        Args:
            product_id: Product id
            product_data: Product data
        """
        product_schema = NewProductSchema()
        product = product_schema.load(product_data)

        original_product = Product.find(product_id)
        original_product.title = product.title
        original_product.description = product.description
        original_product.product_type_id = product.product_type_id
        original_product.state_id = product.state_id
        original_product.report_items = []
        original_product.report_items.extend(product.report_items)

        db.session.commit()

    @classmethod
    def delete(cls, id: int) -> None:  # noqa: A002
        """Delete product by id.

        Args:
            id: Product id
        """
        product = db.session.get(cls, id)
        if product is not None:
            db.session.delete(product)
            db.session.commit()


class ProductReportItem(db.Model):
    """Product report item model.

    Attributes:
        product_id: Product id
        report_item_id: Report item id
    """

    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), primary_key=True)
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), primary_key=True)
