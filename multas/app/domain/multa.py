from dataclasses import dataclass

@dataclass
class Multa:
    # Representa os dados próprios de uma multa.
    ano: int
    descricao: str
    pontuacao: int
    placa: str