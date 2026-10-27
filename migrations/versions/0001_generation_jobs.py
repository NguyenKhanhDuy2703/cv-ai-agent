"""Initial durable AI jobs and event log."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_generation_jobs"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_generation_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=False, unique=True),
        sa.Column("generation_id", sa.Text(), nullable=False, unique=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.String(36)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('QUEUED','RUNNING','NEEDS_INPUT','COMPLETED','FAILED')", name="valid_job_status"),
    )
    op.create_index("ix_ai_jobs_queue", "ai_generation_jobs", ["status", "created_at"])
    op.create_index("ix_ai_jobs_expiry", "ai_generation_jobs", ["expires_at"])
    op.create_table(
        "ai_generation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("ai_generation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "sequence", name="uq_ai_event_sequence"),
    )
    op.create_index("uq_ai_event_terminal", "ai_generation_events", ["job_id"], unique=True,
                    postgresql_where=sa.text("type IN ('done','needs_input','error')"))


def downgrade():
    op.drop_table("ai_generation_events")
    op.drop_table("ai_generation_jobs")
