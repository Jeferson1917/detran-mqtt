from dataclasses import dataclass

@dataclass
class Condutor:
    # Representa os dados próprios de um condutor.
    cpf: str
    nome: str