"""crea tabla de entradas

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
        "entradas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reserva_id", UUID(as_uuid=True), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("cliente_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_correo", sa.String(254), nullable=False),
        sa.Column("evento_id", UUID(as_uuid=True), nullable=False),
        sa.Column("evento_nombre", sa.String(160), nullable=False),
        sa.Column("sector_nombre", sa.String(80), nullable=False),
        sa.Column("usada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "emitida_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("reserva_id", "numero", name="entradas_reserva_numero_key"),
    )
    op.create_index("ix_entradas_cliente_id", "entradas", ["cliente_id"])


def downgrade() -> None:
    op.drop_table("entradas")
