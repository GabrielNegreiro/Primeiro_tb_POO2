from datetime import date, timedelta

from app.models.locacao import Locacao


class LocacaoService:
    """Regras de negócio para locações de filmes."""

    def __init__(self, repository=None):
        self.repository = repository
        self.locacoes = []

    def carregar(self, buscar_filme):
        """Carrega as locações salvas. Chamar depois que os filmes já foram carregados."""
        if self.repository is None:
            return

        self.locacoes = self.repository.carregar_locacoes(buscar_filme)
        self._sincronizar_disponibilidade()

    def criar_locacao(self, filme, cliente_nome, dias_previstos=7):
        if not filme.disponivel:
            raise ValueError("Filme indisponível para locação.")

        prevista = date.today() + timedelta(days=dias_previstos)
        locacao = Locacao(filme, cliente_nome, data_devolucao_prevista=prevista)

        filme.disponivel = False
        self.locacoes.append(locacao)
        self._persistir()
        return locacao

    def devolver_locacao(self, locacao):
        if locacao.data_devolucao_real is not None:
            raise ValueError("Locação já foi devolvida.")

        locacao.registrar_devolucao()
        locacao.filme.disponivel = True
        self._persistir()

    def excluir_locacao(self, locacao):
        if locacao.data_devolucao_real is None:
            raise ValueError("Devolva a locação antes de excluí-la.")

        self.locacoes.remove(locacao)
        self._persistir()

    def listar_todas(self):
        return list(self.locacoes)

    def listar_ativas(self):
        return [l for l in self.locacoes if l.status == "Em aberto"]

    def listar_atrasadas(self):
        return [l for l in self.locacoes if l.atrasada]

    def _persistir(self):
        if self.repository is not None:
            self.repository.salvar_locacoes(self.locacoes)

    def _sincronizar_disponibilidade(self):
        # O filmes.json pode estar desatualizado: a disponibilidade vem das locações.
        em_aberto = {l.filme.id for l in self.locacoes if l.data_devolucao_real is None}
        for locacao in self.locacoes:
            locacao.filme.disponivel = locacao.filme.id not in em_aberto