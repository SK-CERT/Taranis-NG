"""Regenerating bots, collectors, presenters and publishers."""

from sqlalchemy import orm

from migrations.regenerate_params import RegenerateParameters


def regenerate_all(connection):
    """Regenerate all nodes.

    Args:
        connection: Connection to DTB.
    """
    session = orm.Session(bind=connection)
    RegenerateParameters("bots", session)
    RegenerateParameters("collectors", session)
    RegenerateParameters("presenters", session)
    RegenerateParameters("publishers", session)
