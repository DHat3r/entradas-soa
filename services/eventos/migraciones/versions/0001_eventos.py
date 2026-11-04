"""crea tablas de eventos y sectores

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
        "eventos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organizador_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("lugar", sa.String(160), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("estado IN ('BORRADOR', 'PUBLICADO')", name="estado_valido"),
    )
    op.create_table(
        "sectores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evento_id",
            UUID(as_uuid=True),
            sa.ForeignKey("eventos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("precio_clp", sa.Integer(), nullable=False),
        sa.Column("capacidad", sa.Integer(), nullable=False),
        sa.Column("disponibles", sa.Integer(), nullable=False),
        sa.CheckConstraint("precio_clp >= 0", name="precio_no_negativo"),
        sa.CheckConstraint("capacidad > 0", name="capacidad_positiva"),
        sa.CheckConstraint(
            "disponibles >= 0 AND disponibles <= capacidad", name="disponibles_en_rango"
        ),
    )
    op.create_index("ix_sectores_evento_id", "sectores", ["evento_id"])


def downgrade() -> None:
    op.drop_index("ix_sectores_evento_id", table_name="sectores")
    op.drop_table("sectores")
    op.drop_table("eventos")
