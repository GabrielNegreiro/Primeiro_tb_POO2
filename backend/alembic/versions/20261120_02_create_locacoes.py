"""Cria a tabela de locacoes.

Revision ID: 20261120_02
Revises: 20261120_01
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20261120_02'
down_revision: Union[str, None] = '20261120_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria locacoes sem alterar a tabela de filmes."""
    op.create_table(
        'locacoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filme_id', sa.Integer(), nullable=False),
        sa.Column('cliente_nome', sa.String(), nullable=False),
        sa.Column('data_locacao', sa.Date(), nullable=False),
        sa.Column('data_devolucao_prevista', sa.Date(), nullable=False),
        sa.Column('data_devolucao_real', sa.Date(), nullable=True),
        sa.CheckConstraint(
            'data_devolucao_prevista >= data_locacao',
            name='ck_locacoes_prevista_apos_locacao',
        ),
        sa.CheckConstraint(
            'data_devolucao_real IS NULL OR data_devolucao_real >= data_locacao',
            name='ck_locacoes_real_apos_locacao',
        ),
        sa.ForeignKeyConstraint(
            ['filme_id'],
            ['filmes.id'],
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_locacoes_filme_id',
        'locacoes',
        ['filme_id'],
        unique=False,
    )
    op.create_index(
        'uq_locacoes_filme_em_aberto',
        'locacoes',
        ['filme_id'],
        unique=True,
        postgresql_where=sa.text('data_devolucao_real IS NULL'),
    )


def downgrade() -> None:
    """Remove somente os objetos criados por esta migracao."""
    op.drop_index('uq_locacoes_filme_em_aberto', table_name='locacoes')
    op.drop_index('ix_locacoes_filme_id', table_name='locacoes')
    op.drop_table('locacoes')