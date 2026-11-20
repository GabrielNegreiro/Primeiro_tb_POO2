"""Cria a tabela de filmes.

Revision ID: 20261120_01
Revises:
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20261120_01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria filmes sem alterar tabelas existentes."""
    op.create_table(
        'filmes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('genero', sa.String(length=100), nullable=False),
        sa.Column('ano', sa.Integer(), nullable=False),
        sa.Column('duracao', sa.Integer(), nullable=False),
        sa.Column(
            'disponivel',
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.CheckConstraint('ano >= 1888', name='ck_filmes_ano_minimo'),
        sa.CheckConstraint(
            'duracao > 0',
            name='ck_filmes_duracao_positiva',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_filmes_titulo', 'filmes', ['titulo'], unique=False)
    op.create_index(
        'ix_filmes_disponivel',
        'filmes',
        ['disponivel'],
        unique=False,
    )


def downgrade() -> None:
    """Remove somente os objetos criados por esta migracao."""
    op.drop_index('ix_filmes_disponivel', table_name='filmes')
    op.drop_index('ix_filmes_titulo', table_name='filmes')
    op.drop_table('filmes')
