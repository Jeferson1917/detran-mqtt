import json

import paho.mqtt.client as mqtt

from app.domain.veiculo import Veiculo
from app.repository import VeiculoRepository


TOPICO_EMPLACAR = "detran/requests/emplacamento/emplacar"
TOPICO_RESPOSTA = "detran/responses/emplacamento/emplacar"

TOPICO_VEICULOS_POR_ANO = "detran/requests/emplacamento/veiculos-por-ano"
TOPICO_RESPOSTA_VEICULOS_POR_ANO = (
    "detran/responses/emplacamento/veiculos-por-ano"
)

TOPICO_CALCULAR_IPVA = "detran/requests/emplacamento/calcular-ipva"
TOPICO_RESPOSTA_CALCULAR_IPVA = (
    "detran/responses/emplacamento/calcular-ipva"
)

TOPICO_CONSULTAR_PLACA = "detran/requests/emplacamento/consultar-placa"
TOPICO_RESPOSTA_CONSULTAR_PLACA = (
    "detran/responses/emplacamento/consultar-placa"
)


repository = VeiculoRepository()


# Executado quando o microserviço consegue estabelecer conexão com o broker.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Conectado ao broker MQTT. Código: {reason_code}")

    # O microserviço se inscreve nos tópicos das operações que oferece.
    client.subscribe(TOPICO_EMPLACAR)
    client.subscribe(TOPICO_VEICULOS_POR_ANO)
    client.subscribe(TOPICO_CALCULAR_IPVA)
    client.subscribe(TOPICO_CONSULTAR_PLACA)

    print(f"Inscrito no tópico: {TOPICO_EMPLACAR}")
    print(f"Inscrito no tópico: {TOPICO_VEICULOS_POR_ANO}")
    print(f"Inscrito no tópico: {TOPICO_CALCULAR_IPVA}")
    print(f"Inscrito no tópico: {TOPICO_CONSULTAR_PLACA}")


def consultar_veiculos_por_ano(client, dados):
    # Busca no repository os veículos registrados no ano informado.
    veiculos = repository.buscar_por_ano(dados["ano"])

    resposta = {
        "requestId": dados.get("requestId"),
        "sucesso": True,
        "veiculos": [
            {
                "placa": veiculo.placa,
                "modelo": veiculo.modelo,
                "valor": veiculo.valor,
                "cpf_condutor": veiculo.cpf_condutor,
            }
            for veiculo in veiculos
        ],
    }

    payload_resposta = json.dumps(resposta)

    client.publish(
        TOPICO_RESPOSTA_VEICULOS_POR_ANO,
        payload_resposta,
    )

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_VEICULOS_POR_ANO}"
    )


def calcular_ipva(client, dados):
    # Busca o veículo pelo identificador conhecido pelo microserviço.
    veiculo = repository.buscar_por_placa(dados["placa"])

    if veiculo is None:
        resposta = {
            "requestId": dados.get("requestId"),
            "sucesso": False,
            "mensagem": "Veículo não encontrado.",
            "placa": dados["placa"],
        }
    else:
        resposta = {
            "requestId": dados.get("requestId"),
            "sucesso": True,
            "placa": veiculo.placa,
            "valor": veiculo.valor,
            "ipva": veiculo.calcular_ipva(),
        }

    client.publish(
        TOPICO_RESPOSTA_CALCULAR_IPVA,
        json.dumps(resposta),
    )

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_CALCULAR_IPVA}"
    )


def consultar_placa(client, dados):
    # Consulta um veículo que pertence ao microserviço de emplacamento.
    veiculo = repository.buscar_por_placa(dados["placa"])

    if veiculo is None:
        resposta = {
            "requestId": dados.get("requestId"),
            "sucesso": False,
            "mensagem": "Veículo não encontrado.",
            "placa": dados["placa"],
        }
    else:
        resposta = {
            "requestId": dados.get("requestId"),
            "sucesso": True,
            "placa": veiculo.placa,
            "modelo": veiculo.modelo,
            "valor": veiculo.valor,
            "cpf_condutor": veiculo.cpf_condutor,
        }

    client.publish(
        TOPICO_RESPOSTA_CONSULTAR_PLACA,
        json.dumps(resposta),
    )

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_CONSULTAR_PLACA}"
    )


# Executado sempre que uma mensagem chega em um tópico inscrito.
def on_message(client, userdata, message):
    print(f"Mensagem recebida em: {message.topic}")

    try:
        # MQTT entrega o payload como bytes, então transformamos em JSON.
        dados = json.loads(message.payload.decode("utf-8"))

        print(f"Solicitação recebida: {dados}")

        if message.topic == TOPICO_CONSULTAR_PLACA:
            consultar_placa(client, dados)
            return

        if message.topic == TOPICO_CALCULAR_IPVA:
            calcular_ipva(client, dados)
            return

        if message.topic == TOPICO_VEICULOS_POR_ANO:
            consultar_veiculos_por_ano(client, dados)
            return

        veiculo = Veiculo(
            placa=dados["placa"],
            modelo=dados["modelo"],
            valor=float(dados["valor"]),
            cpf_condutor=dados["cpf"],
            ano_emplacamento=dados["ano_emplacamento"],
        )

        # Salva o veículo no armazenamento do microserviço.
        repository.salvar(veiculo)

        resposta = {
            "requestId": dados.get("requestId"),
            "sucesso": True,
            "mensagem": "Veículo emplacado com sucesso.",
            "placa": veiculo.placa,
        }

        payload_resposta = json.dumps(resposta)

        client.publish(
            TOPICO_RESPOSTA,
            payload_resposta,
        )

        print(f"Resposta publicada em: {TOPICO_RESPOSTA}")

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        KeyError,
        ValueError,
    ) as erro:
        print(f"Erro ao processar mensagem: {erro}")


# Cria o cliente MQTT utilizado pelo microserviço.
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Define os callbacks responsáveis pela comunicação MQTT.
client.on_connect = on_connect
client.on_message = on_message

# Dentro da rede Docker Compose, "broker" é o nome do serviço Mosquitto.
client.connect("broker", 1883, 60)

# Mantém o microserviço executando e processando mensagens.
client.loop_forever()