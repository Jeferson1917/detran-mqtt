from app.domain.veiculo import Veiculo


class VeiculoRepository:
    def __init__(self):
        # O armazenamento pertence ao microserviço de emplacamento.
        # Por enquanto usamos memória para facilitar a implementação.
        self._veiculos = []

    def salvar(self, veiculo: Veiculo) -> None:
        self._veiculos.append(veiculo)

    def buscar_por_placa(self, placa: str) -> Veiculo | None:
        for veiculo in self._veiculos:
            if veiculo.placa == placa:
                return veiculo

        return None

    def buscar_por_ano(self, ano: int) -> list[Veiculo]:
        return [
            veiculo
            for veiculo in self._veiculos
            if veiculo.ano_emplacamento == ano
        ]

    def buscar_por_cpf(self, cpf: str) -> list[Veiculo]:
        # Retorna os veículos associados ao condutor informado.
        return [
            veiculo
            for veiculo in self._veiculos
            if veiculo.cpf_condutor == cpf
        ]