"""Initial migration

Create tables for consultas and decisoes.

Revision ID: 001
Revises:
Create Date: 2026-03-03 00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create consultas table
    op.create_table(
        "consultas",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
        ),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("filtros", sa.JSON(), nullable=True),
        sa.Column(
            "resultados_encontrados", sa.Integer(), server_default="0", nullable=True
        ),
        sa.Column("pagina", sa.Integer(), server_default="1", nullable=True),
        sa.Column("tamanho", sa.Integer(), server_default="20", nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consultas_criado_em", "consultas", ["criado_em"])
    op.create_index("ix_consultas_usuario_id", "consultas", ["usuario_id"])

    # Create decisoes table
    op.create_table(
        "decisoes",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
        ),
        sa.Column("uuid_tjdft", sa.String(), nullable=False),
        sa.Column("processo", sa.String(), nullable=True),
        sa.Column("ementa", sa.Text(), nullable=True),
        sa.Column("inteiro_teor", sa.Text(), nullable=True),
        sa.Column("relator", sa.String(), nullable=True),
        sa.Column("data_julgamento", sa.Date(), nullable=True),
        sa.Column("data_publicacao", sa.Date(), nullable=True),
        sa.Column("orgao_julgador", sa.String(), nullable=True),
        sa.Column("classe", sa.String(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decisoes_uuid_tjdft", "decisoes", ["uuid_tjdft"], unique=True)
    op.create_index("ix_decisoes_relator", "decisoes", ["relator"])


def downgrade() -> None:
    # Drop decisoes table
    op.drop_index("ix_decisoes_relator", table_name="decisoes")
    op.drop_index("ix_decisoes_uuid_tjdft", table_name="decisoes")
    op.drop_table("decisoes")

    # Drop consultas table
    op.drop_index("ix_consultas_usuario_id", table_name="consultas")
    op.drop_index("ix_consultas_criado_em", table_name="consultas")
    op.drop_table("consultas")
