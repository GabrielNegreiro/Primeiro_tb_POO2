from datetime import date

class Locacao:

    def __init__(self, filme, cliente_nome, data_locacao=None,
                 data_devolucao_prevista=None, data_devolucao_real=None):
        self.filme = filme
        self.cliente_nome = cliente_nome
        self.data_locacao = data_locacao or date.today()
        self.data_devolucao_prevista = data_devolucao_prevista
        self.data_devolucao_real = data_devolucao_real

    @property
    def status(self):
        return 'Devolvido' if self.data_devolucao_real else 'Em aberto'

    @property
    def atrasada(self):
        if self.data_devolucao_real is not None:
            return False
        if self.data_devolucao_prevista is None:
            return False
        return date.today() > self.data_devolucao_prevista

    def registrar_devolucao(self, data=None):
        self.data_devolucao_real = data or date.today()