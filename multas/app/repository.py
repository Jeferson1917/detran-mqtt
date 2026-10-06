from app.domain.multa import Multa

class MultaRepository:
    def __init__(self):
        # O armazenamento das multas pertence a este microserviço.
        self._multas = []

    def salvar(self, multa: Multa) -> None:
        self._multas.append(multa)

    def buscar_por_placa_e_ano(
        self,
        placa: str,
        ano: int,
    ) -> list[Multa]:
        return [
            multa
            for multa in self._multas
            if multa.placa == placa and multa.ano == ano
        ]

    def buscar_por_ano(self, ano: int) -> list[Multa]:
        return [
            multa
            for multa in self._multas
            if multa.ano == ano
        ]

    def buscar_por_placa(self, placa: str) -> list[Multa]:
        return [
            multa
            for multa in self._multas
            if multa.placa == placa
        ]