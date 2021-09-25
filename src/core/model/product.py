from managers.db_manager import db
from datetime import *
from taranisng.schema.product import ProductPresentationSchema, ProductSchemaBase
from marshmallow import post_load
from sqlalchemy import orm, func, or_, and_
from marshmallow import fields
from taranisng.schema.report_item import ReportItemIdSchema
from model.report_item import ReportItem
from model.acl_entry import ACLEntry
from taranisng.schema.acl_entry import ItemType
from sqlalchemy.sql.expression import cast
import sqlalchemy


class NewProductSchema(ProductSchemaBase):
    report_items = fields.Nested(ReportItemIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return Product(**data)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(1024))

    created = db.Column(db.DateTime, default=datetime.now)

    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'))
    product_type = db.relationship("ProductType")

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User")

    report_items = db.relationship("ReportItem", secondary='product_report_item')

    def __init__(self, id, title, description, product_type_id, report_items):

        if id != -1:
            self.id = id

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
        self.subtitle = self.description
        self.tag = "mdi-file-pdf-outline"

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def find(cls, product_id):
        product = cls.query.get(product_id)
        return product

    @classmethod
    def get_detail_json(cls, product_id):
        product = cls.query.get(product_id)
        products_schema = ProductPresentationSchema()
        return products_schema.dump(product)

    @classmethod
    def get(cls, filter, offset, limit, user):

        query = db.session.query(Product, func.count().filter(ACLEntry.id > 0).label("acls"),
                                 func.count().filter(ACLEntry.access == True).label("access"),
                                 func.count().filter(ACLEntry.modify == True).label("modify")).distinct().group_by(
            Product.id)

        query = query.outerjoin(ACLEntry, and_(cast(Product.product_type_id, sqlalchemy.String) == ACLEntry.item_id,
                                               ACLEntry.item_type == ItemType.PRODUCT_TYPE))
        query = ACLEntry.apply_query(query, user, True, False, False)

        if 'search' in filter and filter['search'] != '':
            search_string = '%' + filter['search'].lower() + '%'
            query = query.filter(
                or_(func.lower(Product.title).like(search_string),
                    func.lower(Product.description).like(search_string)))

        if 'limit' in filter and filter['limit'] != 'ALL':
            date_limit = datetime.now()
            if filter['limit'] == 'TODAY':
                date_limit = date_limit.replace(hour=0, minute=0, second=0, microsecond=0)

            if filter['limit'] == 'WEEK':
                date_limit = date_limit.replace(day=date_limit.day - date_limit.weekday(), hour=0, minute=0, second=0,
                                                microsecond=0)

            if filter['limit'] == 'MONTH':
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            query = query.filter(Product.created >= date_limit)

        if 'sort' in filter:
            if filter['sort'] == 'DATE_DESC':
                query = query.order_by(db.desc(Product.created))

            elif filter['sort'] == 'DATE_ASC':
                query = query.order_by(db.asc(Product.created))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_json(cls, filter, offset, limit, user):
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
        return {'total_count': count, 'items': products_schema.dump(products)}

    @classmethod
    def add_product(cls, product_data, user_id):
        product_schema = NewProductSchema()
        product = product_schema.load(product_data)

        if product.id is not None:
            original_product = cls.query.get(product.id)
            product.created = original_product.created
            Product.delete(original_product.id)

        product.user_id = user_id
        db.session.add(product)
        db.session.commit()

        return product

    @classmethod
    def delete(cls, id):
        product = cls.query.get(id)
        if product is not None:
            db.session.delete(product)
            db.session.commit()


class ProductReportItem(db.Model):
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    report_item_id = db.Column(db.Integer, db.ForeignKey('report_item.id'), primary_key=True)
