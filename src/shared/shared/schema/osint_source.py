"""Module for defining the schema of an OSINT source."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from shared.schema.collector import CollectorExport


from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.collector import CollectorExportSchema, CollectorSchema
from shared.schema.parameter_value import ParameterValueExportSchema, ParameterValueSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.word_list import WordListSchema


class OSINTSourceGroupSchemaBase(Schema):
    """OSINTSourceGroupSchemaBase is a schema class for defining the structure of an OSINT source group.

    Attributes:
        id (str): The unique identifier of the OSINT source group.
        name (str): The name of the OSINT source group.
        description (str): A brief description of the OSINT source group.
        default (bool): Indicates whether this OSINT source group is the default.
    """

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    default = fields.Bool()


class OSINTSourceGroupId:
    """OSINTSourceGroupId is a class for representing the ID of an OSINT source group."""

    def __init__(
        self,
        id: str,  # noqa: A002
    ) -> None:
        """Initialize an instance of OSINTSourceGroupId.

        Args:
            id (str): The ID of the OSINT source group.
        """
        self.id = id


class OSINTSourceGroupIdSchema(Schema):
    """OSINTSourceGroupIdSchema is a Marshmallow schema for deserializing and validating data related to OSINTSourceGroupId.

    Attributes:
        id (fields.Str): A string field representing the ID of the OSINT source group.
    """

    class Meta:
        """Meta class for the schema.

        Attributes:
            unknown (marshmallow.fields.Field): Specifies the behavior for unknown fields in the input data.
                Setting it to EXCLUDE will ignore any unknown fields.
        """

        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> OSINTSourceGroupId:  # noqa: ANN003, ARG002
        """Create an instance of OSINTSourceGroupId with the provided data.

        Args:
            data (dict): A dictionary containing the data to initialize the OSINTSourceGroupId instance.
            **kwargs: Additional keyword arguments.

        Returns:
            OSINTSourceGroupId: An instance of OSINTSourceGroupId initialized with the provided data.
        """
        return OSINTSourceGroupId(**data)


class OSINTSourceCollectorSchema(Schema):
    """OSINTSourceCollectorSchema is a schema class for defining the structure of an OSINT source collector.

    Attributes:
        id (fields.Str): The unique identifier of the collector.
        name (fields.Str): The name of the collector.
        description (fields.Str): A brief description of the collector.
        collector_type (fields.Str): The type of the collector.
    """

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    collector_type = fields.Str()


class OSINTSourceId:
    """Class to represent the ID of an OSINT source.

    Attributes:
        id (str): The identifier for the OSINT source.
    """

    def __init__(
        self,
        id: str,  # noqa: A002
    ) -> None:
        """Initialize an instance of OSINTSourceId.

        Args:
            id (str): The identifier for the OSINT source.
        """
        self.id = id


class OSINTSourceIdSchema(Schema):
    """Schema for OSINTSourceId.

    This schema is used to validate and deserialize data related to OSINTSourceId.

    Attributes:
        id (str): The identifier for the OSINT source.

    Methods:
        make(data, **kwargs):
            Creates an OSINTSourceId instance from the deserialized data.
    """

    class Meta:
        """Meta class for the schema.

        Attributes:
            unknown (marshmallow.fields.Field): Specifies the behavior for unknown fields in the input data.
                Setting it to EXCLUDE will ignore any unknown fields.
        """

        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> OSINTSourceId:  # noqa: ANN003, ARG002
        """Create an instance of OSINTSourceId with the provided data.

        Args:
            data (dict): A dictionary containing the data to initialize the OSINTSourceId instance.
            **kwargs: Additional keyword arguments.

        Returns:
            OSINTSourceId: An instance of OSINTSourceId initialized with the provided data.
        """
        return OSINTSourceId(**data)


class OSINTSource:
    """Class to represent an OSINT source."""

    def __init__(
        self,
        id: str,  # noqa: A002
        name: str,
        parameter_values: list,
        word_lists: list,
        description: str,
        collector_id: str,
        last_attempted: datetime,
        last_collected: datetime,
        last_error_message: str | None = None,
    ) -> None:
        """Initialize an instance of the class.

        Args:
            id (str): The unique identifier of the OSINT source.
            name (str): The name of the OSINT source.
            parameter_values (list): A list of parameter values associated with the OSINT source.
            word_lists (list): A list of word lists associated with the OSINT source.
            description (str): A brief description of the OSINT source.
            collector_id (str): The unique identifier of the collector associated with the OSINT source.
            last_attempted (datetime): The date and time when the OSINT source was last attempted to be collected.
            last_collected (datetime): The date and time when the OSINT source was last collected.
            last_error_message (str, optional): The error message from the last collection attempt.
        """
        self.id = id
        self.name = name

        self.param_key_values = {}
        for pv in parameter_values:
            self.param_key_values.update({pv.parameter.key: pv.value})

        self.word_lists = word_lists
        self.description = description
        self.collector_id = collector_id
        self.last_attempted = last_attempted
        self.last_collected = last_collected
        self.last_error_message = last_error_message


class OSINTSourceSchema(Schema):
    """OSINTSourceSchema is a schema class for defining the structure of an OSINT source.

    Attributes:
        id (fields.Str): The unique identifier of the OSINT source.
        name (fields.Str): The name of the OSINT source.
        parameter_values (fields.List): A list of parameter values associated with the OSINT source.
        word_lists (fields.List): A list of word lists associated with the OSINT source.
        description (fields.Str): A brief description of the OSINT source.
        collector_id (fields.Str): The unique identifier of the collector associated with the OSINT source.
        last_attempted (fields.DateTime): The date and time when the OSINT source was last attempted to be collected.
        last_collected (fields.DateTime): The date and time when the OSINT source was last collected
        last_error_message (fields.Str): The error message from the last collection attempt.
        status (fields.Str): The status of the OSINT source (e.g., "green", "gray").
    """

    class Meta:
        """Meta class for the schema.

        Attributes:
            unknown (marshmallow.fields.Field): Specifies the behavior for unknown fields in the input data.
                Setting it to EXCLUDE will ignore any unknown fields.
        """

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    word_lists = fields.List(fields.Nested(WordListSchema))
    description = fields.Str()
    collector_id = fields.Str()
    last_attempted = fields.DateTime("%d.%m.%Y - %H:%M:%S", allow_none=True)
    last_collected = fields.DateTime("%d.%m.%Y - %H:%M:%S", allow_none=True)
    last_error_message = fields.Str(allow_none=True)
    status = fields.Str(dump_only=True)  # skip this field during deserialization

    @post_load
    def make_osint_source(self, data: dict, **kwargs) -> OSINTSource:  # noqa: ANN003, ARG002
        """Create an instance of OSINTSource with the provided data.

        Args:
            data (dict): A dictionary containing the data to initialize the OSINTSource instance.
            **kwargs: Additional keyword arguments.

        Returns:
            OSINTSource: An instance of OSINTSource initialized with the provided data.
        """
        return OSINTSource(**data)


class OSINTSourceGroupSchema(OSINTSourceGroupSchemaBase):
    """OSINTSourceGroupSchema is a schema class for defining the structure of an OSINT source group.

    Attributes:
        id (fields.Str): The unique identifier of the OSINT source group.
        name (fields.Str): The name of the OSINT source group.
        description (fields.Str): A brief description of the OSINT source group.
        default (fields.Bool): Indicates whether this OSINT source group is the default.
        osint_sources (fields.List): A list of OSINT sources associated with the OSINT source group.
    """

    osint_sources = fields.List(fields.Nested(OSINTSourceSchema))


class OSINTSourcePresentationSchema(OSINTSourceSchema, PresentationSchema):
    """OSINTSourcePresentationSchema is a schema class for defining the structure of an OSINT source presentation schema.

    Attributes:
        collector (fields.Nested): A nested field representing the collector associated with the OSINT source.
        osint_source_groups (fields.List): A list of OSINT source groups associated with the OSINT source.
    """

    collector = fields.Nested(CollectorSchema)
    osint_source_groups = fields.Nested(OSINTSourceSchema, many=True, allow_none=True)


class OSINTSourceGroupPresentationSchema(OSINTSourceGroupSchema, PresentationSchema):
    """OSINTSourceGroupPresentationSchema is a schema class for defining the structure of an OSINT source group presentation schema.

    Attributes:
        id (fields.Str): The unique identifier of the OSINT source group.
        name (fields.Str): The name of the OSINT source group.
        description (fields.Str): A brief description of the OSINT source group.
        default (fields.Bool): Indicates whether this OSINT source group is the default.
        osint_sources (fields.List): A list of OSINT sources associated with the OSINT source group.
    """


class OSINTSourceExport:
    """A class to represent an OSINT source export."""

    def __init__(self, name: str, description: str, collector: CollectorExport, parameter_values: list) -> None:
        """Initialize an instance of the class.

        Args:
            name (str): The name of the OSINT source.
            description (str): A brief description of the OSINT source.
            collector (CollectorExport): The collector associated with the OSINT source.
            parameter_values (list): A list of parameter values associated with the OSINT source.
        """
        self.name = name
        self.description = description
        self.collector = collector
        self.parameter_values = parameter_values


class OSINTSourceExportSchema(Schema):
    """OSINTSourceExportSchema is a schema class for defining the structure of an OSINT source export.

    Attributes:
        name (fields.Str): The name of the OSINT source.
        description (fields.Str): A brief description of the OSINT source.
        collector (fields.Nested): A nested field representing the collector associated with the OSINT source.
        parameter_values (fields.List): A list of parameter values associated with the OSINT source.
    """

    name = fields.Str()
    description = fields.Str()
    collector = fields.Nested(CollectorExportSchema)
    parameter_values = fields.List(fields.Nested(ParameterValueExportSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> OSINTSourceExport:  # noqa: ANN003, ARG002
        """Create an instance of OSINTSourceExport with the provided data.

        Args:
            data (dict): A dictionary containing the data to initialize the OSINTSourceExport instance.
            **kwargs: Additional keyword arguments.

        Returns:
            OSINTSourceExport: An instance of OSINTSourceExport initialized with the provided data.
        """
        return OSINTSourceExport(**data)


class OSINTSourceExportRoot:
    """A class to represent the root of an OSINT source export."""

    def __init__(self, version: int, data: list) -> None:
        """Initialize an instance of the class.

        Args:
            version (str): The version of the OSINT source.
            data (dict): The data associated with the OSINT source.
        """
        self.version = version
        self.data = data


class OSINTSourceExportRootSchema(Schema):
    """A schema class for defining the structure of the root of an OSINT source export.

    Attributes:
        version (fields.Int): The version of the OSINT source.
        data (fields.Nested): A nested field representing the data associated with the OSINT source.
    """

    version = fields.Int()
    data = fields.Nested(OSINTSourceExportSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> OSINTSourceExportRoot:  # noqa: ANN003, ARG002
        """Create an instance of OSINTSourceExportRoot with the provided data.

        Args:
            data (dict): A dictionary containing the data to initialize the OSINTSourceExportRoot instance.
            **kwargs: Additional keyword arguments.

        Returns:
            OSINTSourceExportRoot: An instance of OSINTSourceExportRoot initialized with the provided data.
        """
        return OSINTSourceExportRoot(**data)
