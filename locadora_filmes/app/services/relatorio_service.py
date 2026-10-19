from pathlib import Path
from typing import Iterable, Union

from app.models.locacao import Locacao


class RelatorioService:

    def exportar_txt(
        self,
        locacoes: Iterable[Locacao],
        caminho: Union[str, Path],
    ) -> None:
        locacoes = list(locacoes)

        linhas = ['RELATORIO DE LOCACOES', '=' * 40, '']
        for locacao in locacoes:
            linhas.append(f'Filme: {locacao.filme.titulo}')
            linhas.append(f'Cliente: {locacao.cliente_nome}')
            linhas.append(f'Locacao: {locacao.data_locacao}')
            linhas.append(f'Prevista: {locacao.data_devolucao_prevista}')
            linhas.append(f'Devolucao: {locacao.data_devolucao_real or "-"}')
            linhas.append(f'Status: {locacao.status}')
            linhas.append('')
        linhas.append(f'Total de locacoes: {len(locacoes)}')

        Path(caminho).write_text('\n'.join(linhas) + '\n', encoding='utf-8')