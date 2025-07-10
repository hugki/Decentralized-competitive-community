"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2025-05-08 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("hf_repo", sa.Text(), nullable=False),
        sa.Column("submitter_github", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()")),
    )

    op.create_table(
        "benchmark",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("dataset_sha", sa.Text(), nullable=False),
    )

    task_status = postgresql.ENUM(
        "QUEUED", "RUNNING", "DONE", "DISPUTED", name="taskstatus"
    )
    task_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "task",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("model.id")),
        sa.Column("benchmark_id", sa.Integer(), sa.ForeignKey("benchmark.id")),
        sa.Column("status", sa.Enum("QUEUED", "RUNNING", "DONE", "DISPUTED", name="taskstatus")),
        sa.Column("assigned_to", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("runtime_sec", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    op.create_table(
        "task_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("task.id")),
        sa.Column("runner_id", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("runtime_sec", sa.Integer(), nullable=False),
        sa.Column("stdout_sha", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()")),
    )

def downgrade():
    op.drop_table("task_result")
    op.drop_table("task")
    op.drop_table("benchmark")
    op.drop_table("model")
    op.execute("DROP TYPE taskstatus")
