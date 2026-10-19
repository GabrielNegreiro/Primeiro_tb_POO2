import csv
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Union

from app.models.filme import Filme
from app.models.locacao import Locacao


class LocacaoRepository:
    CAMPOS = [
        'filme_id',
        'cliente_nome',
        'data_locacao',
        'data_devolucao_prevista',
        'data_devolucao_real',
    ]

    def __init__(
        self,
        caminho_arquivo: Optional[Union[str, Path]] = None,
    ):
        self.caminho_arquivo = (
            Path(caminho_arquivo)
            if caminho_arquivo is not None
            else Path(__file__).resolve().parent / 'locacoes.csv'
        )

    def carregar_locacoes(
        self,
        buscar_filme: Callable[[int], Optional[Filme]],
    ) -> List[Locacao]:
        if not self.caminho_arquivo.exists():
            return []

        with self.caminho_arquivo.open('r', encoding='utf-8', newline='') as arquivo:
            leitor = csv.DictReader(arquivo)
            registros = list(leitor)

        locacoes = [
            self._desserializar_locacao(registro, buscar_filme)
            for registro in registros
        ]
        # Locacoes de filmes que foram excluidos sao ignoradas.
        return [locacao for locacao in locacoes if locacao is not None]

    def salvar_locacoes(self, locacoes: Iterable[Locacao]) -> None:
        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

        with self.caminho_arquivo.open('w', encoding='utf-8', newline='') as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=self.CAMPOS)
            escritor.writeheader()
            for locacao in locacoes:
                escritor.writerow(self._serializar_locacao(locacao))

    @staticmethod
    def _serializar_locacao(locacao: Locacao) -> dict:
        return {
            'filme_id': locacao.filme.id,
            'cliente_nome': locacao.cliente_nome,
            'data_locacao': LocacaoRepository._data_para_texto(locacao.data_locacao),
            'data_devolucao_prevista': LocacaoRepository._data_para_texto(
                locacao.data_devolucao_prevista
            ),
            'data_devolucao_real': LocacaoRepository._data_para_texto(
                locacao.data_devolucao_real
            ),
        }

    @staticmethod
    def _desserializar_locacao(
        registro: dict,
        buscar_filme: Callable[[int], Optional[Filme]],
    ) -> Optional[Locacao]:
        try:
            filme_id = int(registro['filme_id'])
            filme = buscar_filme(filme_id)
            if filme is None:
                return None

            return Locacao(
                filme=filme,
                cliente_nome=registro['cliente_nome'],
                data_locacao=LocacaoRepository._texto_para_data(
                    registro['data_locacao']
                ),
                data_devolucao_prevista=LocacaoRepository._texto_para_data(
                    registro['data_devolucao_prevista']
                ),
                data_devolucao_real=LocacaoRepository._texto_para_data(
                    registro['data_devolucao_real']
                ),
            )
        except KeyError as erro:
            raise ValueError(
                f'Campo obrigatorio ausente na locacao: {erro.args[0]}'
            ) from erro

    @staticmethod
    def _data_para_texto(valor: Optional[date]) -> str:
        return valor.isoformat() if valor is not None else ''

    @staticmethod
    def _texto_para_data(texto: str) -> Optional[date]:
        return date.fromisoformat(texto) if texto else None