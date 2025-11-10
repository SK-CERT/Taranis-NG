"""Add state system for products and report items.

Revision ID: 23a431775391
Revises: fdc6bba17c9b
Create Date: 2025-10-25 10:00:00.000000

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "23a431775391"
down_revision = "fdc6bba17c9b"
branch_labels = None
depends_on = None

Base = orm.declarative_base()


class PermissionStateSystem(Base):
    """Permission table for state system."""

    __tablename__ = "permission"
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())

    def __init__(
        self,
        id: str,  # noqa: A002
        name: str,
        description: str,
    ) -> None:
        """Initialize permission."""
        self.id = id
        self.name = name
        self.description = description

    @staticmethod
    def add(session: orm.Session, permission_id: str, name: str, description: str) -> None:
        """Add permission if does not exists."""
        perm = session.query(PermissionStateSystem).filter_by(id=permission_id).first()
        if not perm:
            session.add(PermissionStateSystem(permission_id, name, description))

    @staticmethod
    def delete(session: orm.Session, permission_id: str) -> None:
        """Delete permission by id."""
        perm = session.query(PermissionStateSystem).filter_by(id=permission_id).first()
        if perm:
            session.delete(perm)
            logger.info(f"Permission {perm.id} deleted...")


class RoleStateSystem(Base):
    """Role table for state system."""

    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(PermissionStateSystem, secondary="role_permission")


class RolePermissionStateSystem(Base):
    """Association table between role and permission for state system."""

    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


class StateDefinitionMigration(Base):
    """State table for migration."""

    __tablename__ = "state"
    id = sa.Column(sa.Integer, primary_key=True)
    display_name = sa.Column(sa.String(100), nullable=False)
    description = sa.Column(sa.String(500))
    color = sa.Column(sa.String(7))
    icon = sa.Column(sa.String(50))
    editable = sa.Column(sa.Boolean, default=True)
    created = sa.Column(sa.DateTime, default=sa.func.now())

    def __init__(
        self,
        display_name: str,
        description: str,
        color: str,
        icon: str,
        editable: bool = True,
    ) -> None:
        """Initialize state definition."""
        self.display_name = display_name
        self.description = description
        self.color = color
        self.icon = icon
        self.editable = editable


class StateEntityTypeMigration(Base):
    """State entity type table for migration."""

    __tablename__ = "state_entity_type"
    id = sa.Column(sa.Integer, primary_key=True)
    entity_type = sa.Column(sa.Enum("report_item", "product", name="entity_type_enum"), nullable=False)
    state_id = sa.Column(sa.Integer, sa.ForeignKey("state.id"), nullable=False)
    state_type = sa.Column(sa.Enum("normal", "default", "final", name="state_type_enum"), default="normal")
    is_active = sa.Column(sa.Boolean, default=True)
    editable = sa.Column(sa.Boolean, default=True)
    sort_order = sa.Column(sa.Integer, default=0)
    created = sa.Column(sa.DateTime, default=sa.func.now())

    def __init__(
        self,
        entity_type: str,
        state_id: int,
        state_type: str = "normal",
        is_active: bool = True,
        editable: bool = True,
        sort_order: int = 0,
    ) -> None:
        """Initialize state entity type."""
        self.entity_type = entity_type
        self.state_id = state_id
        self.state_type = state_type
        self.is_active = is_active
        self.editable = editable
        self.sort_order = sort_order


def upgrade() -> None:
    """Create state and state_entity_type tables and add state_id columns to product and report_item tables."""
    op.create_table(
        "state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("color", sa.String(7)),  # Hex color code
        sa.Column("icon", sa.String(50)),
        sa.Column("editable", sa.Boolean(), default=True),
        sa.Column("created", sa.DateTime(), default=sa.func.now()),
    )

    op.create_table(
        "state_entity_type",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.Enum("report_item", "product", name="entity_type_enum"), nullable=False),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("state.id"), nullable=False),
        sa.Column("state_type", sa.Enum("normal", "default", "final", name="state_type_enum"), default="normal"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("editable", sa.Boolean(), default=True),
        sa.Column("sort_order", sa.Integer(), default=0),
        sa.Column("created", sa.DateTime(), default=sa.func.now()),
        sa.UniqueConstraint("entity_type", "state_id", name="unique_state_type"),
    )

    # Add state_id column to product table
    op.add_column("product", sa.Column("state_id", sa.Integer(), sa.ForeignKey("state.id"), nullable=True))

    # Add state_id column to report_item table
    op.add_column("report_item", sa.Column("state_id", sa.Integer(), sa.ForeignKey("state.id"), nullable=True))

    # Insert default states
    session = orm.Session(bind=op.get_bind())

    default_states = [
        StateDefinitionMigration("published", "Product has been published", "#9932CC", "mdi-checkbox-marked", editable=False),
        StateDefinitionMigration("work_in_progress", "Report/Product is being processed", "#FF9800", "mdi-traffic-cone", editable=False),
        StateDefinitionMigration("completed", "Report has been completed", "#2E7D32", "mdi-checkbox-marked", editable=False),
    ]

    for state in default_states:
        session.add(state)

    session.commit()
    logger.info("Default states inserted successfully")

    # Populate state_entity_type table to define which states are available for which entity types
    logger.info("Populating state_entity_type table...")

    # Get state IDs for mapping
    published_state = session.query(StateDefinitionMigration).filter_by(display_name="published").first()
    wip_state = session.query(StateDefinitionMigration).filter_by(display_name="work_in_progress").first()
    completed_state = session.query(StateDefinitionMigration).filter_by(display_name="completed").first()

    # Create state-entity type mappings using SQLAlchemy
    state_entity_mappings = []

    if published_state:
        # Published state only for products
        state_entity_mappings.append(
            StateEntityTypeMigration("product", published_state.id, "final", is_active=True, editable=False, sort_order=20),
        )

    if wip_state:
        # Work-in-Progress for both report_item and product
        state_entity_mappings.append(
            StateEntityTypeMigration("report_item", wip_state.id, "default", is_active=True, editable=False, sort_order=10),
        )
        state_entity_mappings.append(
            StateEntityTypeMigration("product", wip_state.id, "default", is_active=True, editable=False, sort_order=10),
        )

    if completed_state:
        # Completed state only for report_item
        state_entity_mappings.append(
            StateEntityTypeMigration("report_item", completed_state.id, "final", is_active=True, editable=False, sort_order=20),
        )

    # Add all mappings to session
    for mapping in state_entity_mappings:
        session.add(mapping)

    session.commit()
    logger.info("State-entity type mappings created successfully")

    logger.info("Migrating existing report_item completed states to new state system...")

    # Get the "Completed" state ID
    completed_state = session.query(StateDefinitionMigration).filter_by(display_name="Completed").first()
    if completed_state:
        # Update report_items that were completed to use the new state
        bind = op.get_bind()
        bind.execute(sa.text("UPDATE report_item SET state_id = :state_id WHERE completed = true"), {"state_id": completed_state.id})
        logger.info(f"Migrated completed report_items to state_id {completed_state.id}")

    logger.info("Dropping completed column from report_item table...")
    op.drop_column("report_item", "completed")

    logger.info("State migration completed successfully")

    # Add state definition permissions
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_ACCESS", "Config workflow access", "Access to workflow configuration")
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_CREATE", "Config workflow create", "Create workflow configuration")
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_UPDATE", "Config workflow update", "Update workflow configuration")
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_DELETE", "Config workflow delete", "Delete workflow configuration")
    session.commit()

    # Add permissions to Admin role
    bind = op.get_bind()

    # Insert permissions directly into role_permission table
    admin_role_id = bind.execute(sa.text("SELECT id FROM role WHERE name = 'Admin'")).scalar()
    if admin_role_id:
        # Add each permission to the Admin role
        permissions = [
            "CONFIG_WORKFLOW_ACCESS",
            "CONFIG_WORKFLOW_CREATE",
            "CONFIG_WORKFLOW_UPDATE",
            "CONFIG_WORKFLOW_DELETE",
        ]

        for perm_id in permissions:
            # Check if permission assignment already exists
            existing = bind.execute(
                sa.text("SELECT 1 FROM role_permission WHERE role_id = :role_id AND permission_id = :perm_id"),
                {"role_id": admin_role_id, "perm_id": perm_id},
            ).scalar()

            if not existing:
                bind.execute(
                    sa.text("INSERT INTO role_permission (role_id, permission_id) VALUES (:role_id, :perm_id)"),
                    {"role_id": admin_role_id, "perm_id": perm_id},
                )

        logger.info("Added state definition permissions to Admin role")
    else:
        logger.warning("Admin role not found, could not add state definition permissions")


def downgrade() -> None:
    """Drop state_id columns and state table, restore completed column."""
    logger.info("Downgrading state system...")

    logger.info("Recreating completed column in report_item table...")
    op.add_column("report_item", sa.Column("completed", sa.Boolean(), nullable=False, default=False))

    logger.info("Restoring completed column data from state_id...")
    # Get "Completed" state ID and update completed column
    bind = op.get_bind()
    completed_state_id = bind.execute(sa.text("SELECT id FROM state WHERE display_name = 'Completed'")).scalar()

    if completed_state_id:
        bind.execute(sa.text("UPDATE report_item SET completed = true WHERE state_id = :state_id"), {"state_id": completed_state_id})

    logger.info("Restored completed column from state_id")

    logger.info("Dropping state_id columns...")
    op.drop_column("product", "state_id")
    op.drop_column("report_item", "state_id")

    # Delete state definition permissions
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    logger.info("Deleting state definition permissions...")
    PermissionStateSystem.delete(session, "CONFIG_WORKFLOW_ACCESS")
    PermissionStateSystem.delete(session, "CONFIG_WORKFLOW_CREATE")
    PermissionStateSystem.delete(session, "CONFIG_WORKFLOW_UPDATE")
    PermissionStateSystem.delete(session, "CONFIG_WORKFLOW_DELETE")
    session.commit()

    # Drop tables in reverse order due to foreign key constraints
    op.drop_table("state_entity_type")
    op.drop_table("state")

    logger.info("State system tables dropped")
