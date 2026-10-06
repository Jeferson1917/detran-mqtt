import json

import paho.mqtt.client as mqtt

from app.domain.condutor import Condutor
from app.repository import CondutorRepository


TOPICO_CADASTRAR = "detran/requests/condutores/cadastrar"
TOPICO_RESPOSTA_CADASTRAR = "detran/responses/condutores/cadastrar"

TOPICO_TRANSFERIR = "detran/requests/condutores/transferir"
TOPICO_RESPOSTA_TRANSFERIR = "detran/responses/condutores/transferir"

# Tópicos usados para consultar a existência do veículo no microserviço de emplacamento.
TOPICO_CONSULTAR_PLACA = "detran/requests/emplacamento/consultar-placa"
TOPICO_RESPOSTA_CONSULTAR_PLACA = (
    "detran/responses/emplacamento/consultar-placa"
)


repository = CondutorRepository()

# Guarda transferências que aguardam a resposta do microserviço de emplacamento.
transferencias_pendentes = {}


# Executado quando o microserviço consegue estabelecer conexão com o broker.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Conectado ao broker MQTT. Código: {reason_code}")

    # O microserviço se inscreve nas operações que oferece.
    client.subscribe(TOPICO_CADASTRAR)
    client.subscribe(TOPICO_TRANSFERIR)

    # Recebe as respostas das consultas feitas ao microserviço de emplacamento.
    client.subscribe(TOPICO_RESPOSTA_CONSULTAR_PLACA)

    print(f"Inscrito no tópico: {TOPICO_CADASTRAR}")
    print(f"Inscrito no tópico: {TOPICO_TRANSFERIR}")
    print(f"Inscrito no tópico: {TOPICO_RESPOSTA_CONSULTAR_PLACA}")


def cadastrar_condutor(client, dados):
    condutor = Condutor(
        cpf=dados["cpf"],
        nome=dados["nome"],
    )

    # Salva o condutor no armazenamento do microserviço.
    repository.salvar(condutor)

    resposta = {
        "requestId": dados.get("requestId"),
        "sucesso": True,
        "mensagem": "Condutor cadastrado com sucesso.",
        "cpf": condutor.cpf,
    }

    client.publish(
        TOPICO_RESPOSTA_CADASTRAR,
        json.dumps(resposta),
    )

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_CADASTRAR}"
    )


def transferir_proprietario(client, dados):
    request_id = dados.get("requestId")

    # Guarda os dados até o microserviço de emplacamento responder.
    transferencias_pendentes[request_id] = dados

    consulta = {
        "requestId": request_id,
        "placa": dados["placa"],
    }

    # Consulta o microserviço responsável pelos veículos através do broker.
    client.publish(
        TOPICO_CONSULTAR_PLACA,
        json.dumps(consulta),
    )

    print(
        f"Consulta de placa publicada em: "
        f"{TOPICO_CONSULTAR_PLACA}"
    )


def processar_resposta_consulta_placa(client, dados):
    request_id = dados.get("requestId")

    # Ignora respostas que não correspondem a uma transferência pendente.
    transferencia = transferencias_pendentes.get(request_id)

    if transferencia is None:
        print(f"Transferência pendente não encontrada: {request_id}")
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Veículo não encontrado. Transferência não realizada.",
            "placa": transferencia["placa"],
            "cpf": transferencia["cpf"],
        }

        client.publish(
            TOPICO_RESPOSTA_TRANSFERIR,
            json.dumps(resposta),
        )

        # Remove a solicitação depois de processar a resposta.
        del transferencias_pendentes[request_id]

        print(
            f"Resposta publicada em: "
            f"{TOPICO_RESPOSTA_TRANSFERIR}"
        )
        return

    # Só altera a propriedade depois de confirmar que o veículo existe.
    repository.transferir_propriedade(
        placa=transferencia["placa"],
        cpf_proprietario=transferencia["cpf"],
    )

    resposta = {
        "requestId": request_id,
        "sucesso": True,
        "mensagem": "Proprietário transferido com sucesso.",
        "placa": transferencia["placa"],
        "cpf": transferencia["cpf"],
    }

    client.publish(
        TOPICO_RESPOSTA_TRANSFERIR,
        json.dumps(resposta),
    )

    # Remove a solicitação depois de concluir a transferência.
    del transferencias_pendentes[request_id]

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_TRANSFERIR}"
    )


# Executado quando uma mensagem chega em um tópico inscrito.
def on_message(client, userdata, message):
    print(f"Mensagem recebida em: {message.topic}")

    try:
        # MQTT entrega o payload como bytes, então transformamos em JSON.
        dados = json.loads(message.payload.decode("utf-8"))

        print(f"Solicitação recebida: {dados}")

        if message.topic == TOPICO_CADASTRAR:
            cadastrar_condutor(client, dados)
            return

        if message.topic == TOPICO_TRANSFERIR:
            transferir_proprietario(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_CONSULTAR_PLACA:
            processar_resposta_consulta_placa(client, dados)
            return

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