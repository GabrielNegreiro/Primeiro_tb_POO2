from datetime import date, timedelta

from app.models.locacao import Locacao


class LocacaoService:

    def __init__(self):
        self.locacoes = []

    def criar_locacao(self, filme, cliente_nome, dias_previstos=7):
        if not filme.disponivel:
            raise ValueError('Filme indisponível para locação.')

        prevista = date.today() + timedelta(days=dias_previstos)
        locacao = Locacao(filme, cliente_nome, data_devolucao_prevista=prevista)

        filme.disponivel = False
        self.locacoes.append(locacao)
        return locacao

    def devolver_locacao(self, locacao):
        if locacao.data_devolucao_real is not None:
            raise ValueError('Locação já foi devolvida.')

        locacao.registrar_devolucao()
        locacao.filme.disponivel = True

    def listar_todas(self):
        return list(self.locacoes)

    def listar_ativas(self):
        return [l for l in self.locacoes if l.status == 'Em aberto']

    def listar_atrasadas(self):
        return [l for l in self.locacoes if l.atrasada]