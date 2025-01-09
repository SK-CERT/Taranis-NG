"""Product model."""

from datetime import datetime
import sqlalchemy
from marshmallow import fields
from marshmallow import post_load
from sqlalchemy import orm, func, or_, and_
from sqlalchemy.sql.expression import cast

from managers.db_manager import db
from model.acl_entry import ACLEntry
from model.report_item import ReportItem
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
    def make(self, data, **kwargs):
        """Create a new product.

        Args:
            data: Product data
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

    report_items = db.relationship("ReportItem", secondary="product_report_item")

    def __init__(self, id, title, description, product_type_id, report_items):
        """Initialize a product."""
        if id != -1:
            self.id = id
        else:
            self.id = None

        self.title = title
        self.description = description
        self.product_type_id = product_type_id
        self.subtitle = ""
        self.tag = ""

        self.report_items = []
        for report_item in report_items:
            self.report_items.append(ReportItem.find(report_item.id))

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct a product."""
        self.subtitle = self.description
        self.tag = "mdi-file-pdf-outline"

    @classmethod
    def count_all(cls):
        """Count all products.

        Returns:
            int: Number of products
        """
        return cls.query.count()

    @classmethod
    def find(cls, product_id):
        """Find a product.

        Args:
            product_id: Product id
        Returns:
            Product: Product
        """
        product = db.session.get(cls, product_id)
        return product

    @classmethod
    def get_detail_json(cls, product_id):
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
    def get(cls, filter, offset, limit, user):
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
            ACLEntry, and_(cast(Product.product_type_id, sqlalchemy.String) == ACLEntry.item_id, ACLEntry.item_type == ItemType.PRODUCT_TYPE)
        )
        query = ACLEntry.apply_query(query, user, True, False, False)

        if "search" in filter and filter["search"] != "":
            search_string = "%" + filter["search"].lower() + "%"
            query = query.filter(or_(func.lower(Product.title).like(search_string), func.lower(Product.description).like(search_string)))

        if "range" in filter and filter["range"] != "ALL":
            date_limit = datetime.now()
            if filter["range"] == "TODAY":
                date_limit = date_limit.replace(hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "WEEK":
                date_limit = date_limit.replace(day=date_limit.day - date_limit.weekday(), hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "MONTH":
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            query = query.filter(Product.created >= date_limit)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(Product.created))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(Product.created))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_json(cls, filter, offset, limit, user):
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
                report_item.modify = False

        products_schema = ProductPresentationSchema(many=True)
        return {"total_count": count, "items": products_schema.dump(products)}

    @classmethod
    def add_product(cls, product_data, user_id):
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
    def update_product(cls, product_id, product_data):
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
        original_product.report_items = []
        original_product.report_items.extend(product.report_items)

        db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete a product.

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
