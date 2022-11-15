from datetime import datetime
from marshmallow import post_load, fields
from sqlalchemy import func, orm

from managers.db_manager import db
from shared.schema.apikey import ApiKeySchema


class NewApiKeySchema(ApiKeySchema):

    @post_load
    def make(self, data, **kwargs):
        return ApiKey(**data)


class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    key = db.Column(db.String()) # length 40
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True, default=None)

    def __init__(self, name, key, created_at, user_id, expires_at):
        #self.id = None
        self.name = name
        self.key = key
        # created_at - database take care about it
        self.user_id = user_id
        self.expires_at = expires_at

    @classmethod
    def find(cls, apikey_id):
        apikey = cls.query.get(apikey_id)
        return apikey

    @classmethod
    def find_by_name(cls, apikey_name):
        apikey = cls.query.filter_by(name=apikey_name).first()
        return apikey

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(ApiKey.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(func.lower(ApiKey.name).like(search_string))

        return query.order_by(db.asc(ApiKey.name)).all(), query.count()

    @classmethod
    def add_new(cls, data):
        schema = NewApiKeySchema()
        apikey = schema.load(data)
        #db.session.add(apikey.user)
        db.session.add(apikey)
        db.session.commit()
        return apikey

    @classmethod
    def delete(cls, id):
        apikey = cls.query.get(id)
        db.session.delete(apikey)
        db.session.commit()
