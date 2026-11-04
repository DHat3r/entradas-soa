"""crea tabla de pagos

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
        "pagos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reserva_id", UUID(as_uuid=True), nullable=False),
        sa.Column("monto_clp", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("reserva_id", name="pagos_reserva_id_key"),
        sa.CheckConstraint("estado IN ('APROBADO', 'RECHAZADO')", name="estado_valido"),
    )


def downgrade() -> None:
    op.drop_table("pagos")
