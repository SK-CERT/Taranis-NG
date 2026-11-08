"""This module contains schemas for assets and asset groups."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.notification_template import NotificationTemplateSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.report_item import ReportItemAttributeSchema, ReportItemBaseSchema
from shared.schema.report_item_type import ReportItemTypeSchema
from shared.schema.user import UserSchemaBase


class AssetCpeSchema(Schema):
    """Schema for a CPE of an asset."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    value = fields.Str()


class AssetSchema(Schema):
    """Schema for Asset."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    serial = fields.Str()
    description = fields.Str()
    asset_group_id = fields.Str()
    asset_cpes = fields.Nested(AssetCpeSchema, many=True)


class ReportItemVulnerabilitySchema(ReportItemBaseSchema, PresentationSchema):
    """Schema for a report item describing a vulnerability of an asset."""

    report_item_type = fields.Nested(ReportItemTypeSchema)
    attributes = fields.Nested(ReportItemAttributeSchema, many=True)


class AssetVulnerabilitySchema(Schema):
    """Schema for a vulnerability of an asset, and whether it is solved."""

    report_item = fields.Nested(ReportItemVulnerabilitySchema)
    solved = fields.Bool()


class AssetPresentationSchema(AssetSchema, PresentationSchema):
    """Schema for Asset with presentation data and its vulnerabilities."""

    vulnerabilities_count = fields.Int()
    vulnerabilities = fields.Nested(AssetVulnerabilitySchema, many=True)


class AssetGroupSchema(Schema):
    """Schema for Asset group."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()


class AssetGroupPresentationSchema(AssetGroupSchema, PresentationSchema):
    """Schema for Asset group with presentation data, its users and notification templates."""

    users = fields.Nested(UserSchemaBase, many=True)
    templates = fields.Nested(NotificationTemplateSchema, many=True)
