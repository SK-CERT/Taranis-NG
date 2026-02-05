"""remove Atom collector

Revision ID: 4cd4c4758a81
Revises: 9de844252cd5
Create Date: 2025-01-07 10:19:53.355554

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, inspect, select, table

# revision identifiers, used by Alembic.
revision = "4cd4c4758a81"
down_revision = "9de844252cd5"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    if (
        "collectors_node" in inspector.get_table_names()
        and "collector" in inspector.get_table_names()
        and "collector_parameter" in inspector.get_table_names()
    ):
        # get all Collectors nodes
        collectors_node = table("collectors_node", column("id", sa.String))

        stmt = select(collectors_node.c.id)
        results = conn.execute(stmt).fetchall()

        collectors_node_ids = [row[0] for row in results]

        collector_table = table("collector", column("id", sa.String), column("name", sa.String), column("node_id", sa.String))
        for node_id in collectors_node_ids:
            # get all Atom Collectors
            stmt = select(collector_table.c.id).where((collector_table.c.name == "Atom Collector") & (collector_table.c.node_id == node_id))
            results = conn.execute(stmt).fetchall()
            atom_collector_id = results[0][0] if results else None
            # get all RSS Collectors
            stmt = select(collector_table.c.id).where((collector_table.c.name == "RSS Collector") & (collector_table.c.node_id == node_id))
            results = conn.execute(stmt).fetchall()
            rss_collector_id = results[0][0] if results else None

            # get all Atom Collector Parameter IDs
            collector_parameter_table = table("collector_parameter", column("collector_id", sa.String), column("parameter_id", sa.String))
            stmt = select(collector_parameter_table.c.parameter_id).where(collector_parameter_table.c.collector_id == atom_collector_id)
            results = conn.execute(stmt).fetchall()
            atom_collector_parameter_ids = [row[0] for row in results]

            # get all RSS Collector Parameter IDs
            stmt = select(collector_parameter_table.c.parameter_id).where(collector_parameter_table.c.collector_id == rss_collector_id)
            results = conn.execute(stmt).fetchall()
            rss_collector_parameter_ids = [row[0] for row in results]

            # Map parameters
            parameter_mapping = {}
            for atom_collector_parameter_id, rss_collector_parameter_id in zip(
                atom_collector_parameter_ids,
                rss_collector_parameter_ids,
                strict=False,
            ):
                parameter_mapping[atom_collector_parameter_id] = rss_collector_parameter_id

            # change parameter_id in parameter_value table
            parameter_value_table = table("parameter_value", column("parameter_id", sa.Integer))
            for atom_collector_parameter_id, rss_collector_parameter_id in parameter_mapping.items():
                stmt = (
                    parameter_value_table.update()
                    .where(parameter_value_table.c.parameter_id == atom_collector_parameter_id)
                    .values(parameter_id=sa.cast(rss_collector_parameter_id, sa.Integer))
                )
                conn.execute(stmt)

            # add RSS collector parameters in collector_parameter table if they don't exist
            stmt = select(collector_parameter_table.c.parameter_id).where(collector_parameter_table.c.collector_id == rss_collector_id)
            results = conn.execute(stmt).fetchall()
            rss_collector_parameter_ids = [row[0] for row in results]

            if not rss_collector_parameter_ids:
                for atom_collector_parameter_id, rss_collector_parameter_id in parameter_mapping.items():
                    stmt = collector_parameter_table.insert().values(collector_id=rss_collector_id, parameter_id=rss_collector_parameter_id)
                    conn.execute(stmt)

            # change collector_id in osint_source table
            osint_source_table = table("osint_source", column("collector_id", sa.String))
            stmt = (
                osint_source_table.update()
                .where(osint_source_table.c.collector_id == atom_collector_id)
                .values(collector_id=rss_collector_id)
            )
            conn.execute(stmt)

            # delete Atom Collector Parameters
            stmt = collector_parameter_table.delete().where(collector_parameter_table.c.collector_id == atom_collector_id)
            conn.execute(stmt)

            # delete Atom Collector
            stmt = collector_table.delete().where(collector_table.c.id == atom_collector_id)
            conn.execute(stmt)

            # delete Atom Collector Parameter Values
            stmt = parameter_value_table.delete().where(parameter_value_table.c.parameter_id.in_(atom_collector_parameter_ids))
            conn.execute(stmt)


def downgrade():
    pass
