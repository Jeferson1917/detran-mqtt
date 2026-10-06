from dataclasses import dataclass

@dataclass
class Veiculo:
    # Representa os dados próprios de um veículo emplacado, a responsabilidade por esses dados pertence ao microserviço de emplacamento.
    placa: str
    modelo: str
    valor: float
    cpf_condutor: str
    ano_emplacamento: int

    def calcular_ipva(self) -> float:
        # O enunciado define o IPVA como 2% do valor do veículo.
        return self.valor * 0.02