from dataclasses import dataclass

@dataclass
class Propriedade:
    # Representa o proprietário atual de um veículo.
    placa: str
    cpf_proprietario: str