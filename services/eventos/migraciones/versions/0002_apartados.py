"""crea tabla de cupos apartados por reserva

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apartados",
        sa.Column("reserva_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("sector_id", UUID(as_uuid=True), sa.ForeignKey("sectores.id"), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("liberado", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("apartados")
