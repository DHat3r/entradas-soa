"""crea tabla de usuarios

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
        "usuarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("rol IN ('cliente', 'organizador', 'validador')", name="rol_valido"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
