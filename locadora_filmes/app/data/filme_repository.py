import json
from pathlib import Path
from typing import Iterable, List, Optional, Union

from app.models.filme import Filme


class FilmeRepository:
    def __init__(
        self,
        caminho_arquivo: Optional[Union[str, Path]] = None,
    ):
        self.caminho_arquivo = (
            Path(caminho_arquivo)
            if caminho_arquivo is not None
            else Path(__file__).resolve().parent / 'filmes.json'
        )

    def carregar_filmes(self) -> List[Filme]:
        if not self.caminho_arquivo.exists():
            return []

        conteudo = self.caminho_arquivo.read_text(encoding='utf-8')
        if not conteudo.strip():
            return []

        try:
            registros = json.loads(conteudo)
        except json.JSONDecodeError as erro:
            raise ValueError(
                f'Arquivo JSON invalido: {self.caminho_arquivo}'
            ) from erro

        if not isinstance(registros, list):
            raise ValueError('O arquivo de filmes deve conter uma lista JSON.')

        return [self._desserializar_filme(registro) for registro in registros]

    def salvar_filmes(self, filmes: Iterable[Filme]) -> None:
        registros = [self._serializar_filme(filme) for filme in filmes]
        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

        with self.caminho_arquivo.open('w', encoding='utf-8') as arquivo:
            json.dump(registros, arquivo, ensure_ascii=False, indent=4)
            arquivo.write('\n')

    @staticmethod
    def _serializar_filme(filme: Filme) -> dict:
        return {
            'id': filme.id,
            'titulo': filme.titulo,
            'genero': filme.genero,
            'ano': filme.ano,
            'duracao': filme.duracao,
            'disponivel': filme.disponivel,
        }

    @staticmethod
    def _desserializar_filme(registro: dict) -> Filme:
        if not isinstance(registro, dict):
            raise ValueError('Cada filme deve ser representado por um objeto JSON.')

        try:
            return Filme(
                id=registro['id'],
                titulo=registro['titulo'],
                genero=registro['genero'],
                ano=registro['ano'],
                duracao=registro['duracao'],
                disponivel=registro['disponivel'],
            )
        except KeyError as erro:
            raise ValueError(
                f'Campo obrigatorio ausente no filme: {erro.args[0]}'
            ) from erro
