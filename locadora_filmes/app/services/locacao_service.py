from datetime import date, timedelta

from app.models.locacao import Locacao


class LocacaoService:

    def __init__(self, repository=None, filme_service=None):
        self.repository = repository
        self.filme_service = filme_service
        self.locacoes = []

    def carregar(self, buscar_filme):
        # Carrega as locacoes salvas. Chamar depois que os filmes ja foram carregados.
        if self.repository is None:
            return

        self.locacoes = self.repository.carregar_locacoes(buscar_filme)
        self._sincronizar_disponibilidade()

    def criar_locacao(self, filme, cliente_nome, dias_previstos=7):
        if not filme.disponivel:
            raise ValueError('Filme indisponível para locação.')

        prevista = date.today() + timedelta(days=dias_previstos)
        filme = self._definir_disponibilidade(filme, False)
        locacao = Locacao(filme, cliente_nome, data_devolucao_prevista=prevista)

        self.locacoes.append(locacao)
        self._persistir()
        return locacao

    def atualizar_locacao(self, locacao, filme, cliente_nome, dias_previstos):
        if locacao not in self.locacoes:
            raise ValueError('Locacao nao encontrada.')
        if locacao.data_devolucao_real is not None:
            raise ValueError('Nao e possivel editar uma locacao devolvida.')

        cliente_nome = cliente_nome.strip()
        if not cliente_nome:
            raise ValueError('Informe o nome do cliente.')
        if dias_previstos < 1:
            raise ValueError('O prazo deve ter pelo menos um dia.')

        filme_anterior = locacao.filme
        if filme is not filme_anterior:
            if not filme.disponivel:
                raise ValueError('Filme indisponivel para locacao.')
            self._definir_disponibilidade(filme_anterior, True)
            locacao.filme = self._definir_disponibilidade(filme, False)

        locacao.cliente_nome = cliente_nome
        locacao.data_devolucao_prevista = (
            locacao.data_locacao + timedelta(days=dias_previstos)
        )
        self._persistir()
        return locacao

    def devolver_locacao(self, locacao):
        if locacao.data_devolucao_real is not None:
            raise ValueError('Locação já foi devolvida.')

        locacao.registrar_devolucao()
        locacao.filme = self._definir_disponibilidade(locacao.filme, True)
        self._persistir()

    def excluir_locacao(self, locacao):
        if locacao.data_devolucao_real is None:
            raise ValueError('Devolva a locação antes de excluí-la.')

        self.locacoes.remove(locacao)
        self._persistir()

    def listar_todas(self):
        return list(self.locacoes)

    def listar_ativas(self):
        return [l for l in self.locacoes if l.status == 'Em aberto']

    def listar_atrasadas(self):
        return [l for l in self.locacoes if l.atrasada]

    def _persistir(self):
        if self.repository is not None:
            self.repository.salvar_locacoes(self.locacoes)

    def _sincronizar_disponibilidade(self):
        # O filmes.json pode estar desatualizado: a disponibilidade vem das locacoes.
        em_aberto = {l.filme.id for l in self.locacoes if l.data_devolucao_real is None}
        filmes = {locacao.filme.id: locacao.filme for locacao in self.locacoes}
        for filme in filmes.values():
            self._definir_disponibilidade(filme, filme.id not in em_aberto)

    def _definir_disponibilidade(self, filme, disponivel):
        if self.filme_service is None:
            filme.disponivel = bool(disponivel)
            return filme
        return self.filme_service.definir_disponibilidade(filme.id, disponivel)
