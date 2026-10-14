"""baseline schema (projects, test_definitions, execution_runs)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-07

Represents the CURRENT schema defined by app/models/{project,test_definition,
execution_run}.py exactly -- no schema changes. Suitable for a fresh database.

Existing databases that were created by DB_AUTO_CREATE (Base.metadata.create_all)
already contain these tables; mark them as up to date instead of running this
migration:  alembic stamp 0001_baseline
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "test_definitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_test_definitions_project_id"),
        "test_definitions",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "execution_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("test_definition_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failed_step_id", sa.String(length=255), nullable=True),
        sa.Column("failed_step_index", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=4000), nullable=True),
        sa.Column("executed_step_count", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("diagnosis", sa.JSON(), nullable=True),
        sa.Column("explanation", sa.JSON(), nullable=True),
        sa.Column("healing", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.String(length=64), nullable=False),
        sa.Column("finished_at", sa.String(length=64), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_definition_id"],
            ["test_definitions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_execution_runs_test_definition_id"),
        "execution_runs",
        ["test_definition_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_execution_runs_test_definition_id"),
        table_name="execution_runs",
    )
    op.drop_table("execution_runs")

    op.drop_index(
        op.f("ix_test_definitions_project_id"),
        table_name="test_definitions",
    )
    op.drop_table("test_definitions")

    op.drop_table("projects")
