"""Parameter Model."""

from managers.db_manager import db
from managers.log_manager import logger
from marshmallow import post_load
from sqlalchemy.sql import exists

from shared.schema.parameter import ParameterSchema, ParameterType


class Parameter(db.Model):
    """Parameter Model.

    Attributes:
        id (int): Identifier.
        key (str): Key of parameter.
        name (str): Name of parameter.
        description (str): Description of parameter.
        type (ParameterType): Type of parameter.
        default_value (str): Default value.
    """

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(), nullable=False)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(ParameterType))
    default_value = db.Column(db.String(), nullable=True)

    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        type: ParameterType,  # noqa: A002
        default_value: str,
    ) -> None:
        """Initialize Parameter Model.

        Args:
            key (str): Key of parameter.
            name (str): Name of parameter.
            description (str): Description of parameter.
            type (ParameterType): Type of parameter.
            default_value (str): Default value.
        """
        self.key = key
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value

    @classmethod
    def delete_unused(cls) -> None:
        """Delete all Parameter rows that are not referenced in any other tables."""
        from model.bot import BotParameter  # noqa: PLC0415 Must be here, because circular import error
        from model.collector import CollectorParameter  # noqa: PLC0415 Must be here, because circular import error
        from model.presenter import PresenterParameter  # noqa: PLC0415 Must be here, because circular import error
        from model.publisher import PublisherParameter  # noqa: PLC0415 Must be here, because circular import error

        unused_params = (
            db.session.query(cls)
            .filter(
                ~exists().where(BotParameter.parameter_id == Parameter.id)
                & ~exists().where(CollectorParameter.parameter_id == Parameter.id)
                & ~exists().where(PresenterParameter.parameter_id == Parameter.id)
                & ~exists().where(PublisherParameter.parameter_id == Parameter.id),
            )
            .all()
        )

        for param in unused_params:
            db.session.delete(param)

        db.session.commit()
        logger.info(f"Deleted {len(unused_params)} unused Parameter records.")


class NewParameterSchema(ParameterSchema):
    """New Parameter Schema."""

    @post_load
    def make_parameter(self, data: dict, **kwargs) -> Parameter:  # noqa: ANN003, ARG002
        """Make parameter.

        Args:
            data (dict): Data to create parameter.
            **kwargs: Additional arguments.

        Returns:
            Parameter: Created parameter.
        """
        return Parameter(**data)
