from app.domain.condutor import Condutor
from app.domain.propriedade import Propriedade


class CondutorRepository:
    def __init__(self):
        # O armazenamento pertence ao microserviço de condutores.
        self._condutores = []
        self._propriedades = []

    def salvar(self, condutor: Condutor) -> None:
        self._condutores.append(condutor)

    def buscar_por_cpf(self, cpf: str) -> Condutor | None:
        for condutor in self._condutores:
            if condutor.cpf == cpf:
                return condutor

        return None

    def transferir_propriedade(
        self,
        placa: str,
        cpf_proprietario: str,
    ) -> None:
        # Atualiza o proprietário se o veículo já estiver cadastrado.
        for propriedade in self._propriedades:
            if propriedade.placa == placa:
                propriedade.cpf_proprietario = cpf_proprietario
                return

        # Caso seja a primeira transferência conhecida pelo serviço.
        self._propriedades.append(
            Propriedade(
                placa=placa,
                cpf_proprietario=cpf_proprietario,
            )
        )