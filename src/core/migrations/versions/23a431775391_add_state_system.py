"""Add state system for products and report items.

Revision ID: 23a431775391
Revises: fdc6bba17c9b
Create Date: 2025-10-25 10:00:00.000000

"""

import logging
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from model.state import StateEntityTypeEnum, StateEnum, StateTypeEnum
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from shared.common import TZ

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "23a431775391"
down_revision = "fdc6bba17c9b"
branch_labels = None
depends_on = None

Base = orm.declarative_base()
default_updated_by = "system-migration"


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
    updated_by = sa.Column(sa.String())
    updated_at = sa.Column(sa.DateTime())

    def __init__(
        self,
        display_name: StateEnum,
        description: str,
        color: str,
        icon: str,
    ) -> None:
        """Initialize state definition."""
        self.display_name = display_name.value
        self.description = description
        self.color = color
        self.icon = icon
        self.editable = False
        self.updated_at = datetime.now(TZ)
        self.updated_by = default_updated_by


class StateEntityTypeMigration(Base):
    """State entity type table for migration."""

    __tablename__ = "state_entity_type"
    id = sa.Column(sa.Integer, primary_key=True)
    entity_type = sa.Column(
        sa.Enum(StateEntityTypeEnum.REPORT_ITEM.value, StateEntityTypeEnum.PRODUCT.value, name="entity_type_enum"),
        nullable=False,
    )
    state_id = sa.Column(sa.Integer, sa.ForeignKey("state.id"), nullable=False)
    state_type = sa.Column(
        sa.Enum(StateTypeEnum.NORMAL.value, StateTypeEnum.INITIAL.value, StateTypeEnum.FINAL.value, name="state_type_enum"),
        default=StateTypeEnum.NORMAL.value,
    )
    is_active = sa.Column(sa.Boolean, default=True)
    editable = sa.Column(sa.Boolean, default=True)
    sort_order = sa.Column(sa.Integer, default=0)
    updated_by = sa.Column(sa.String())
    updated_at = sa.Column(sa.DateTime())

    def __init__(
        self,
        entity_type: StateEntityTypeEnum,
        state_id: int,
        state_type: StateTypeEnum,
        sort_order: int = 0,
    ) -> None:
        """Initialize state entity type."""
        self.entity_type = entity_type.value
        self.state_id = state_id
        self.state_type = state_type.value
        self.is_active = True
        self.editable = False
        self.sort_order = sort_order
        self.updated_at = datetime.now(TZ)
        self.updated_by = default_updated_by


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
        sa.Column("updated_by", sa.VARCHAR()),
        sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "state_entity_type",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "entity_type",
            sa.Enum(StateEntityTypeEnum.REPORT_ITEM.value, StateEntityTypeEnum.PRODUCT.value, name="entity_type_enum"),
            nullable=False,
        ),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("state.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "state_type",
            sa.Enum(StateTypeEnum.NORMAL.value, StateTypeEnum.INITIAL.value, StateTypeEnum.FINAL.value, name="state_type_enum"),
            default=StateTypeEnum.NORMAL.value,
        ),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("editable", sa.Boolean(), default=True),
        sa.Column("sort_order", sa.Integer(), default=0),
        sa.Column("updated_by", sa.VARCHAR()),
        sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("entity_type", "state_id", name="unique_state_type"),
    )

    # Add state_id column to product table
    op.add_column("product", sa.Column("state_id", sa.Integer(), sa.ForeignKey("state.id", ondelete="SET NULL"), nullable=True))

    # Add state_id column to report_item table
    op.add_column("report_item", sa.Column("state_id", sa.Integer(), sa.ForeignKey("state.id", ondelete="SET NULL"), nullable=True))

    # Insert default states
    session = orm.Session(bind=op.get_bind())

    default_states = [
        StateDefinitionMigration(StateEnum.PUBLISHED, "Product has been published", "#2E7D32", "mdi-checkbox-marked"),
        StateDefinitionMigration(StateEnum.WORK_IN_PROGRESS, "Item is being processed", "#FF9800", "mdi-traffic-cone"),
        StateDefinitionMigration(StateEnum.COMPLETED, "Report has been completed", "#2E7D32", "mdi-checkbox-marked"),
    ]

    for state in default_states:
        session.add(state)

    session.commit()
    logger.info("Default states inserted successfully")

    # Populate state_entity_type table to define which states are available for which entity types
    logger.info("Populating state_entity_type table...")

    # Get state IDs for mapping
    published_state = session.query(StateDefinitionMigration).filter_by(display_name=StateEnum.PUBLISHED.value).first()
    wip_state = session.query(StateDefinitionMigration).filter_by(display_name=StateEnum.WORK_IN_PROGRESS.value).first()
    completed_state = session.query(StateDefinitionMigration).filter_by(display_name=StateEnum.COMPLETED.value).first()

    # Create state-entity type mappings using SQLAlchemy
    state_entity_mappings = []

    if published_state:
        # Published state only for products
        state_entity_mappings.append(
            StateEntityTypeMigration(StateEntityTypeEnum.PRODUCT, published_state.id, StateTypeEnum.FINAL, sort_order=20),
        )

    if wip_state:
        # Work-in-Progress for both report_item and product
        state_entity_mappings.append(
            StateEntityTypeMigration(StateEntityTypeEnum.REPORT_ITEM, wip_state.id, StateTypeEnum.INITIAL, sort_order=10),
        )
        state_entity_mappings.append(
            StateEntityTypeMigration(StateEntityTypeEnum.PRODUCT, wip_state.id, StateTypeEnum.INITIAL, sort_order=10),
        )

    if completed_state:
        # Completed state only for report_item
        state_entity_mappings.append(
            StateEntityTypeMigration(StateEntityTypeEnum.REPORT_ITEM, completed_state.id, StateTypeEnum.FINAL, sort_order=20),
        )

    # Add all mappings to session
    for mapping in state_entity_mappings:
        session.add(mapping)

    session.commit()
    logger.info("State-entity type mappings created successfully")

    logger.info("Migrating existing report_item completed states to new state system...")

    bind = op.get_bind()
    if completed_state:
        # Update report_items that were completed to use the new state
        bind.execute(
            sa.text("UPDATE report_item SET state_id = CASE WHEN completed THEN :comp_id ELSE :wip_id END"),
            {"comp_id": completed_state.id, "wip_id": wip_state.id},
        )
        logger.info(f"Migrated report_items to states: {completed_state.id}, {wip_state.id}")

    if published_state:
        bind.execute(sa.text("UPDATE product SET state_id = :pub_id"), {"pub_id": published_state.id})
        logger.info(f"Migrated products to state: {published_state.id}")

    logger.info("Dropping completed column from report_item table...")
    op.drop_column("report_item", "completed")

    logger.info("State migration completed successfully")

    # Add state definition permissions
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_ACCESS", "Config workflow access", "Access to workflow configuration")
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_CREATE", "Config workflow create", "Create workflow configuration")
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_UPDATE", "Config workflow update", "Update workflow configuration")
    PermissionStateSystem.add(session, "CONFIG_WORKFLOW_DELETE", "Config workflow delete", "Delete workflow configuration")
    session.commit()

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
    op.add_column("report_item", sa.Column("completed", sa.Boolean(), nullable=True, server_default=sa.text("FALSE")))

    logger.info("Restoring completed column data from state_id...")
    # Get "Completed" state ID and update completed column
    bind = op.get_bind()
    completed_state_id = bind.execute(
        sa.text("SELECT id FROM state WHERE display_name = :name"),
        {"name": StateEnum.COMPLETED.value},
    ).scalar()
    if completed_state_id:
        bind.execute(sa.text("UPDATE report_item SET completed = (COALESCE(state_id, 0) = :state_id)"), {"state_id": completed_state_id})

    logger.info("Restored completed column from state_id")
    op.alter_column("report_item", "completed", nullable=False)

    logger.info("Dropping state_id columns...")
    op.drop_column("product", "state_id")
    op.drop_column("report_item", "state_id")

    # Delete state definition permissions
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
    op.execute("DROP TYPE IF EXISTS entity_type_enum")
    op.execute("DROP TYPE IF EXISTS state_type_enum")

    logger.info("State system tables dropped")
