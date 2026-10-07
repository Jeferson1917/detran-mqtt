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
TOPICO_CONSULTAR_PLACA = (
    "detran/requests/emplacamento/consultar-placa"
)

TOPICO_RESPOSTA_CONSULTAR_PLACA = (
    "detran/responses/emplacamento/consultar-placa"
)


# Tópicos usados para consultar os dados do condutor no microserviço
# de condutores.
TOPICO_CONSULTAR_CPF = (
    "detran/requests/condutores/consultar-cpf"
)

TOPICO_RESPOSTA_CONSULTAR_CPF = (
    "detran/responses/condutores/consultar-cpf"
)


# Tópicos usados para consultar as multas de um condutor em determinado ano.
TOPICO_CONDUTOR = (
    "detran/requests/multas/condutor"
)

TOPICO_RESPOSTA_CONDUTOR = (
    "detran/responses/multas/condutor"
)


# Tópicos usados para descobrir os veículos associados a um CPF.
# Essa consulta é realizada pelo microserviço de emplacamento.
TOPICO_VEICULOS_POR_CPF = (
    "detran/requests/emplacamento/veiculos-por-cpf"
)

TOPICO_RESPOSTA_VEICULOS_POR_CPF = (
    "detran/responses/emplacamento/veiculos-por-cpf"
)


repository = MultaRepository()


# Guarda temporariamente as consultas que estão esperando
# respostas dos outros microserviços.
consultas_pendentes = {}


# Executado quando o microserviço consegue estabelecer conexão com o broker.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Conectado ao broker MQTT. Código: {reason_code}")

    # Operações oferecidas diretamente pelo microserviço de multas.
    client.subscribe(TOPICO_LANCAR)
    client.subscribe(TOPICO_VEICULO)
    client.subscribe(TOPICO_ANO)
    client.subscribe(TOPICO_CONDUTOR)

    # Respostas recebidas do microserviço de emplacamento.
    client.subscribe(TOPICO_RESPOSTA_CONSULTAR_PLACA)
    client.subscribe(TOPICO_RESPOSTA_VEICULOS_POR_CPF)

    # Respostas recebidas do microserviço de condutores.
    client.subscribe(TOPICO_RESPOSTA_CONSULTAR_CPF)

    print(f"Inscrito no tópico: {TOPICO_LANCAR}")
    print(f"Inscrito no tópico: {TOPICO_VEICULO}")
    print(f"Inscrito no tópico: {TOPICO_ANO}")
    print(f"Inscrito no tópico: {TOPICO_CONDUTOR}")
    print(f"Inscrito no tópico: {TOPICO_RESPOSTA_CONSULTAR_PLACA}")
    print(f"Inscrito no tópico: {TOPICO_RESPOSTA_VEICULOS_POR_CPF}")
    print(f"Inscrito no tópico: {TOPICO_RESPOSTA_CONSULTAR_CPF}")


def lancar_multa(client, dados):
    multa = Multa(
        ano=int(dados["ano"]),
        descricao=dados["descricao"],
        pontuacao=int(dados["pontuacao"]),
        placa=dados["placa"],
    )

    # Salva a multa no armazenamento pertencente ao microserviço.
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

    # Guarda o estado da consulta enquanto esperamos
    # as respostas dos outros microserviços.
    #
    # O tipo identifica qual fluxo originou a consulta.
    consultas_pendentes[request_id] = {
        "tipo": "veiculo",
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
        print(
            f"Consulta pendente não encontrada: {request_id}"
        )
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
        print(
            f"Consulta pendente não encontrada: {request_id}"
        )
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


def consultar_multas_condutor(client, dados):
    request_id = dados.get("requestId")

    # Guarda o estado da consulta enquanto aguardamos
    # a resposta do microserviço de emplacamento.
    #
    # O tipo identifica que esta consulta começou
    # pelo CPF do condutor.
    consultas_pendentes[request_id] = {
        "tipo": "condutor",
        "cpf": dados["cpf"],
        "ano": int(dados["ano"]),
        "multas": [],
    }

    consulta = {
        "requestId": request_id,
        "cpf": dados["cpf"],
    }

    # O microserviço de multas não acessa diretamente
    # o repository de emplacamento.
    client.publish(
        TOPICO_VEICULOS_POR_CPF,
        json.dumps(consulta),
    )

    print(
        f"Consulta de veículos por CPF publicada em: "
        f"{TOPICO_VEICULOS_POR_CPF}"
    )


def processar_resposta_veiculos_por_cpf(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if consulta is None:
        print(
            f"Consulta pendente não encontrada: {request_id}"
        )
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": (
                "Não foi possível consultar os veículos do condutor."
            ),
            "cpf": consulta["cpf"],
            "ano": consulta["ano"],
            "multas": [],
        }

        client.publish(
            TOPICO_RESPOSTA_CONDUTOR,
            json.dumps(resposta),
        )

        del consultas_pendentes[request_id]
        return

    # O emplacamento informa quais placas estão associadas ao CPF.
    # A partir daqui, multas consulta apenas os seus próprios dados.
    for veiculo in dados["veiculos"]:
        placa = veiculo["placa"]

        multas = repository.buscar_por_placa_e_ano(
            placa=placa,
            ano=consulta["ano"],
        )

        consulta["multas"].extend(
            [
                {
                    "placa": multa.placa,
                    "descricao": multa.descricao,
                    "pontuacao": multa.pontuacao,
                }
                for multa in multas
            ]
        )

    # Depois de reunir as multas, consultamos o nome do condutor.
    consulta_cpf = {
        "requestId": request_id,
        "cpf": consulta["cpf"],
    }

    client.publish(
        TOPICO_CONSULTAR_CPF,
        json.dumps(consulta_cpf),
    )

    print(
        f"Consulta de CPF publicada em: "
        f"{TOPICO_CONSULTAR_CPF}"
    )


def processar_resposta_condutor_consulta(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if consulta is None:
        print(
            f"Consulta pendente não encontrada: {request_id}"
        )
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Condutor não encontrado.",
            "cpf": consulta["cpf"],
            "ano": consulta["ano"],
            "multas": consulta["multas"],
        }

        client.publish(
            TOPICO_RESPOSTA_CONDUTOR,
            json.dumps(resposta),
        )

        del consultas_pendentes[request_id]
        return

    resposta = {
        "requestId": request_id,
        "sucesso": True,
        "condutor": {
            "cpf": dados["cpf"],
            "nome": dados["nome"],
        },
        "ano": consulta["ano"],
        "multas": consulta["multas"],
    }

    client.publish(
        TOPICO_RESPOSTA_CONDUTOR,
        json.dumps(resposta),
    )

    del consultas_pendentes[request_id]

    print(
        f"Resposta publicada em: "
        f"{TOPICO_RESPOSTA_CONDUTOR}"
    )


# Executado quando uma mensagem chega em um tópico inscrito.
def on_message(client, userdata, message):
    print(f"Mensagem recebida em: {message.topic}")

    try:
        # MQTT entrega o payload como bytes, então transformamos em JSON.
        #
        # utf-8-sig também permite lidar com JSONs que eventualmente
        # tenham sido gerados com BOM.
        dados = json.loads(
            message.payload.decode("utf-8-sig")
        )

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

        if message.topic == TOPICO_CONDUTOR:
            consultar_multas_condutor(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_CONSULTAR_PLACA:
            processar_resposta_veiculo(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_VEICULOS_POR_CPF:
            processar_resposta_veiculos_por_cpf(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_CONSULTAR_CPF:
            request_id = dados.get("requestId")

            consulta = consultas_pendentes.get(request_id)

            if consulta is None:
                print(
                    f"Consulta pendente não encontrada: {request_id}"
                )
                return

            # A resposta de consultar-cpf é compartilhada por
            # dois fluxos diferentes. O tipo identifica qual
            # operação originou a consulta.
            if consulta.get("tipo") == "veiculo":
                processar_resposta_condutor(client, dados)
                return

            if consulta.get("tipo") == "condutor":
                processar_resposta_condutor_consulta(
                    client,
                    dados,
                )
                return

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        KeyError,
        ValueError,
    ) as erro:
        print(f"Erro ao processar mensagem: {erro}")


# Cria o cliente MQTT utilizado pelo microserviço.
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2
)

# Define os callbacks responsáveis pela comunicação MQTT.
client.on_connect = on_connect
client.on_message = on_message

# Dentro da rede Docker Compose, "broker" é o nome
# do serviço Mosquitto.
client.connect(
    "broker",
    1883,
    60,
)

# Mantém o microserviço executando e processando mensagens.
client.loop_forever()