"""agrega lo necesario para reenviar pasos atascados

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reservas", sa.Column("resultado_simulado", sa.String(10), nullable=True))
    op.add_column("reservas", sa.Column("transicion_en", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "reservas",
        sa.Column("entradas_emitidas", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "reservas",
        sa.Column("liberacion_pendiente", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("reservas", "liberacion_pendiente")
    op.drop_column("reservas", "entradas_emitidas")
    op.drop_column("reservas", "transicion_en")
    op.drop_column("reservas", "resultado_simulado")
