import json
import paho.mqtt.client as mqtt
from app.domain.multa import Multa
from app.repository import MultaRepository


TOPICO_LANCAR = "detran/requests/multas/lancar"
TOPICO_RESPOSTA_LANCAR = "detran/responses/multas/lancar"

TOPICO_VEICULO = "detran/requests/multas/veiculo"
TOPICO_RESPOSTA_VEICULO = "detran/responses/multas/veiculo"

TOPICO_ANO = "detran/requests/multas/ano"
TOPICO_RESPOSTA_ANO = "detran/responses/multas/ano"


# Tópicos usados para consultar os dados do veículo no microserviço
# de emplacamento.
TOPICO_CONSULTAR_PLACA = "detran/requests/emplacamento/consultar-placa"
TOPICO_RESPOSTA_CONSULTAR_PLACA = (
    "detran/responses/emplacamento/consultar-placa"
)


# Tópicos usados para consultar os dados do condutor no microserviço
# de condutores.
TOPICO_CONSULTAR_CPF = "detran/requests/condutores/consultar-cpf"
TOPICO_RESPOSTA_CONSULTAR_CPF = (
    "detran/responses/condutores/consultar-cpf"
)


repository = MultaRepository()


# Guarda temporariamente as consultas que estão esperando
# respostas dos outros microserviços.
consultas_pendentes = {}


# Executado quando o microserviço consegue estabelecer conexão com o broker.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Conectado ao broker MQTT. Código: {reason_code}")

    # O microserviço se inscreve nas operações que oferece.
    client.subscribe(TOPICO_LANCAR)
    client.subscribe(TOPICO_VEICULO)
    client.subscribe(TOPICO_ANO)

    # Recebe respostas do microserviço de emplacamento.
    client.subscribe(TOPICO_RESPOSTA_CONSULTAR_PLACA)

    # Recebe respostas do microserviço de condutores.
    client.subscribe(TOPICO_RESPOSTA_CONSULTAR_CPF)

    print(f"Inscrito no tópico: {TOPICO_LANCAR}")
    print(f"Inscrito no tópico: {TOPICO_VEICULO}")
    print(f"Inscrito no tópico: {TOPICO_ANO}")
    print(f"Inscrito no tópico: {TOPICO_RESPOSTA_CONSULTAR_PLACA}")
    print(f"Inscrito no tópico: {TOPICO_RESPOSTA_CONSULTAR_CPF}")


def lancar_multa(client, dados):
    multa = Multa(
        ano=int(dados["ano"]),
        descricao=dados["descricao"],
        pontuacao=int(dados["pontuacao"]),
        placa=dados["placa"],
    )

    # Salva a multa no armazenamento do microserviço.
    repository.salvar(multa)

    resposta = {
        "requestId": dados.get("requestId"),
        "sucesso": True,
        "mensagem": "Multa lançada com sucesso.",
        "placa": multa.placa,
        "ano": multa.ano,
        "pontuacao": multa.pontuacao,
    }

    client.publish(
        TOPICO_RESPOSTA_LANCAR,
        json.dumps(resposta),
    )

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_LANCAR}"
    )


def consultar_multas_veiculo(client, dados):
    request_id = dados.get("requestId")

    multas = repository.buscar_por_placa_e_ano(
        placa=dados["placa"],
        ano=int(dados["ano"]),
    )

    # Guarda os dados da consulta enquanto esperamos
    # as respostas dos outros microserviços.
    consultas_pendentes[request_id] = {
        "placa": dados["placa"],
        "ano": int(dados["ano"]),
        "multas": multas,
    }

    consulta = {
        "requestId": request_id,
        "placa": dados["placa"],
    }

    # O microserviço de multas não acessa diretamente os dados
    # de veículos. A consulta passa pelo broker MQTT.
    client.publish(
        TOPICO_CONSULTAR_PLACA,
        json.dumps(consulta),
    )

    print(
        f"Consulta de placa publicada em: "
        f"{TOPICO_CONSULTAR_PLACA}"
    )


def processar_resposta_veiculo(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if consulta is None:
        print(f"Consulta pendente não encontrada: {request_id}")
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Veículo não encontrado.",
            "placa": consulta["placa"],
            "ano": consulta["ano"],
            "multas": [],
        }

        client.publish(
            TOPICO_RESPOSTA_VEICULO,
            json.dumps(resposta),
        )

        del consultas_pendentes[request_id]

        return

    cpf_condutor = dados["cpf_condutor"]

    # Agora que temos o CPF retornado pelo microserviço
    # de emplacamento, consultamos os dados do condutor.
    consulta_cpf = {
        "requestId": request_id,
        "cpf": cpf_condutor,
    }

    client.publish(
        TOPICO_CONSULTAR_CPF,
        json.dumps(consulta_cpf),
    )

    print(
        f"Consulta de CPF publicada em: "
        f"{TOPICO_CONSULTAR_CPF}"
    )


def processar_resposta_condutor(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if consulta is None:
        print(f"Consulta pendente não encontrada: {request_id}")
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Condutor não encontrado.",
            "placa": consulta["placa"],
            "ano": consulta["ano"],
            "multas": [],
        }

        client.publish(
            TOPICO_RESPOSTA_VEICULO,
            json.dumps(resposta),
        )

        del consultas_pendentes[request_id]

        return

    resposta = {
        "requestId": request_id,
        "sucesso": True,
        "placa": consulta["placa"],
        "ano": consulta["ano"],
        "condutor": {
            "cpf": dados["cpf"],
            "nome": dados["nome"],
        },
        "multas": [
            {
                "descricao": multa.descricao,
                "pontuacao": multa.pontuacao,
            }
            for multa in consulta["multas"]
        ],
    }

    client.publish(
        TOPICO_RESPOSTA_VEICULO,
        json.dumps(resposta),
    )

    # A consulta foi concluída e não precisa mais ficar pendente.
    del consultas_pendentes[request_id]

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_VEICULO}"
    )


def consultar_multas_ano(client, dados):
    multas = repository.buscar_por_ano(
        ano=int(dados["ano"]),
    )

    resposta = {
        "requestId": dados.get("requestId"),
        "sucesso": True,
        "ano": int(dados["ano"]),
        "multas": [
            {
                "placa": multa.placa,
                "descricao": multa.descricao,
                "pontuacao": multa.pontuacao,
            }
            for multa in multas
        ],
    }

    client.publish(
        TOPICO_RESPOSTA_ANO,
        json.dumps(resposta),
    )

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_ANO}"
    )


# Executado quando uma mensagem chega em um tópico inscrito.
def on_message(client, userdata, message):
    print(f"Mensagem recebida em: {message.topic}")

    try:
        # MQTT entrega o payload como bytes, então transformamos em JSON.
        dados = json.loads(message.payload.decode("utf-8"))

        print(f"Solicitação recebida: {dados}")

        if message.topic == TOPICO_LANCAR:
            lancar_multa(client, dados)
            return

        if message.topic == TOPICO_VEICULO:
            consultar_multas_veiculo(client, dados)
            return

        if message.topic == TOPICO_ANO:
            consultar_multas_ano(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_CONSULTAR_PLACA:
            processar_resposta_veiculo(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_CONSULTAR_CPF:
            processar_resposta_condutor(client, dados)
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