"""crea tabla de correos enviados

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "correos_enviados",
        sa.Column("reserva_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("destinatario", sa.String(254), nullable=False),
        sa.Column(
            "enviado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("correos_enviados")
