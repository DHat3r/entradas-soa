"""crea tabla de reservas

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
        "reservas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cliente_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_correo", sa.String(254), nullable=False),
        sa.Column("sector_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evento_id", UUID(as_uuid=True), nullable=True),
        sa.Column("evento_nombre", sa.String(160), nullable=True),
        sa.Column("sector_nombre", sa.String(80), nullable=True),
        sa.Column("monto_clp", sa.Integer(), nullable=True),
        sa.Column(
            "creada_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "estado IN ('CREADA', 'CANCELADA', 'PENDIENTE_PAGO', 'VENCIDA', 'PAGANDO', "
            "'CONFIRMADA', 'RECHAZADA')",
            name="estado_valido",
        ),
        sa.CheckConstraint("cantidad BETWEEN 1 AND 6", name="cantidad_valida"),
    )
    op.create_index("ix_reservas_estado_vence_en", "reservas", ["estado", "vence_en"])
    op.create_index("ix_reservas_cliente_id", "reservas", ["cliente_id"])


def downgrade() -> None:
    op.drop_table("reservas")
