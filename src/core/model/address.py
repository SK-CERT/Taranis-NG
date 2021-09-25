from managers.db_manager import db
from marshmallow import post_load
from taranisng.schema.address import AddressSchema


class NewAddressSchema(AddressSchema):

    @post_load
    def make(self, data, **kwargs):
        return Address(**data)


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    street = db.Column(db.String(64))
    city = db.Column(db.String(64))
    zip = db.Column(db.String(16))
    country = db.Column(db.String(54))

    def __init__(self, street, city, zip, country):
        self.street = street
        self.city = city
        self.zip = zip
        self.country = country
