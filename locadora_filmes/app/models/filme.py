from dataclasses import dataclass


@dataclass
class Filme:
    id: int
    titulo: str
    genero: str
    ano: int
    duracao: int
    disponivel: bool = True

    @property
    def status(self):
        return 'Disponivel' if self.disponivel else 'Indisponivel'
