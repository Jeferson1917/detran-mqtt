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

TOPICO_CONDUTOR = "detran/requests/multas/condutor"
TOPICO_RESPOSTA_CONDUTOR = "detran/responses/multas/condutor"

# Tópicos usados para consultar o ranking dos condutores.
TOPICO_RANKING = "detran/requests/multas/ranking"
TOPICO_RESPOSTA_RANKING = "detran/responses/multas/ranking"

# Tópicos usados para consultar os dados dos veículos no microserviço de emplacamento.
TOPICO_CONSULTAR_PLACA = "detran/requests/emplacamento/consultar-placa"
TOPICO_RESPOSTA_CONSULTAR_PLACA = "detran/responses/emplacamento/consultar-placa"

# Tópicos usados para consultar os dados dos condutores no microserviço de condutores.
TOPICO_CONSULTAR_CPF = "detran/requests/condutores/consultar-cpf"
TOPICO_RESPOSTA_CONSULTAR_CPF = "detran/responses/condutores/consultar-cpf"

# Tópicos usados para consultar os veículos associados a um CPF.
TOPICO_VEICULOS_POR_CPF = "detran/requests/emplacamento/veiculos-por-cpf"
TOPICO_RESPOSTA_VEICULOS_POR_CPF = "detran/responses/emplacamento/veiculos-por-cpf"

repository = MultaRepository()

# Armazena consultas que precisam aguardar respostas de outros microserviços.
consultas_pendentes = {}


def on_connect(client, userdata, flags, reason_code, properties):
    print("Conectado ao broker MQTT.")

    client.subscribe(TOPICO_LANCAR)
    client.subscribe(TOPICO_VEICULO)
    client.subscribe(TOPICO_ANO)
    client.subscribe(TOPICO_CONDUTOR)
    client.subscribe(TOPICO_RANKING)

    client.subscribe(TOPICO_RESPOSTA_CONSULTAR_PLACA)
    client.subscribe(TOPICO_RESPOSTA_VEICULOS_POR_CPF)
    client.subscribe(TOPICO_RESPOSTA_CONSULTAR_CPF)

    print(f"Inscrito no tópico: {TOPICO_LANCAR}")
    print(f"Inscrito no tópico: {TOPICO_VEICULO}")
    print(f"Inscrito no tópico: {TOPICO_ANO}")
    print(f"Inscrito no tópico: {TOPICO_CONDUTOR}")
    print(f"Inscrito no tópico: {TOPICO_RANKING}")
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

    repository.salvar(multa)

    resposta = {
        "requestId": dados.get("requestId"),
        "sucesso": True,
        "mensagem": "Multa lançada com sucesso.",
    }

    client.publish(
        TOPICO_RESPOSTA_LANCAR,
        json.dumps(resposta),
    )


def consultar_multas_veiculo(client, dados):
    request_id = dados.get("requestId")

    multas = repository.buscar_por_placa_e_ano(
        placa=dados["placa"],
        ano=int(dados["ano"]),
    )

    # Guarda o resultado parcial enquanto aguarda os dados do veículo e do condutor.
    consultas_pendentes[request_id] = {
        "tipo": "veiculo",
        "placa": dados["placa"],
        "ano": int(dados["ano"]),
        "multas": multas,
    }

    client.publish(
        TOPICO_CONSULTAR_PLACA,
        json.dumps({
            "requestId": request_id,
            "placa": dados["placa"],
        }),
    )


def processar_resposta_veiculo(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if not consulta:
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Veículo não encontrado.",
        }

        client.publish(
            TOPICO_RESPOSTA_VEICULO,
            json.dumps(resposta),
        )

        consultas_pendentes.pop(request_id, None)
        return

    cpf = dados["veiculo"]["cpf_condutor"]

    consulta["cpf"] = cpf

    client.publish(
        TOPICO_CONSULTAR_CPF,
        json.dumps({
            "requestId": request_id,
            "cpf": cpf,
        }),
    )


def processar_resposta_condutor(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if not consulta:
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Condutor não encontrado.",
        }

        client.publish(
            TOPICO_RESPOSTA_VEICULO,
            json.dumps(resposta),
        )

        consultas_pendentes.pop(request_id, None)
        return

    resposta = {
        "requestId": request_id,
        "sucesso": True,
        "veiculo": {
            "placa": consulta["placa"],
        },
        "condutor": {
            "cpf": dados["condutor"]["cpf"],
            "nome": dados["condutor"]["nome"],
        },
        "ano": consulta["ano"],
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

    consultas_pendentes.pop(request_id, None)


def consultar_multas_ano(client, dados):
    ano = int(dados["ano"])

    multas = repository.buscar_por_ano(ano)

    resposta = {
        "requestId": dados.get("requestId"),
        "sucesso": True,
        "ano": ano,
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


def consultar_multas_condutor(client, dados):
    request_id = dados.get("requestId")

    consultas_pendentes[request_id] = {
        "tipo": "condutor",
        "cpf": dados["cpf"],
        "ano": int(dados["ano"]),
        "multas": [],
    }

    # Primeiro consulta os veículos associados ao CPF para descobrir quais placas devem ser verificadas.
    client.publish(
        TOPICO_VEICULOS_POR_CPF,
        json.dumps({
            "requestId": request_id,
            "cpf": dados["cpf"],
        }),
    )


def processar_resposta_veiculos_por_cpf(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if not consulta:
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Nenhum veículo encontrado para o CPF.",
        }

        client.publish(
            TOPICO_RESPOSTA_CONDUTOR,
            json.dumps(resposta),
        )

        consultas_pendentes.pop(request_id, None)
        return

    ano = consulta["ano"]

    for veiculo in dados.get("veiculos", []):
        placa = veiculo["placa"]

        multas = repository.buscar_por_placa_e_ano(
            placa=placa,
            ano=ano,
        )

        for multa in multas:
            consulta["multas"].append({
                "placa": multa.placa,
                "descricao": multa.descricao,
                "pontuacao": multa.pontuacao,
            })

    client.publish(
        TOPICO_CONSULTAR_CPF,
        json.dumps({
            "requestId": request_id,
            "cpf": consulta["cpf"],
        }),
    )


def processar_resposta_condutor_consulta(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if not consulta:
        return

    if not dados.get("sucesso"):
        resposta = {
            "requestId": request_id,
            "sucesso": False,
            "mensagem": "Condutor não encontrado.",
        }

        client.publish(
            TOPICO_RESPOSTA_CONDUTOR,
            json.dumps(resposta),
        )

        consultas_pendentes.pop(request_id, None)
        return

    resposta = {
        "requestId": request_id,
        "sucesso": True,
        "condutor": {
            "cpf": dados["condutor"]["cpf"],
            "nome": dados["condutor"]["nome"],
        },
        "ano": consulta["ano"],
        "multas": consulta["multas"],
    }

    client.publish(
        TOPICO_RESPOSTA_CONDUTOR,
        json.dumps(resposta),
    )

    consultas_pendentes.pop(request_id, None)


def consultar_ranking(client, dados):
    request_id = dados.get("requestId")
    ano = int(dados["ano"])

    multas = repository.buscar_por_ano(ano)

    # Soma primeiro os pontos por placa porque ainda precisamos consultar a qual condutor cada veículo pertence.
    pontuacao_por_placa = {}

    for multa in multas:
        if multa.placa not in pontuacao_por_placa:
            pontuacao_por_placa[multa.placa] = 0

        pontuacao_por_placa[multa.placa] += multa.pontuacao

    placas = list(pontuacao_por_placa.keys())

    consultas_pendentes[request_id] = {
        "tipo": "ranking",
        "ano": ano,
        "pontuacao_por_placa": pontuacao_por_placa,
        "placas_pendentes": set(placas),
        "cpf_por_placa": {},
        "cpfs_pendentes": set(),
        "condutores": {},
    }

    if not placas:
        finalizar_ranking(client, request_id)
        return

    # Consulta cada placa no microserviço de emplacamento para descobrir o CPF do condutor.
    for placa in placas:
        client.publish(
            TOPICO_CONSULTAR_PLACA,
            json.dumps({
                "requestId": request_id,
                "placa": placa,
            }),
        )


def processar_resposta_ranking_veiculo(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if not consulta or consulta.get("tipo") != "ranking":
        return

    placa = dados.get("placa")

    if not placa:
        return

    if dados.get("sucesso"):
        cpf = dados.get("cpf_condutor")

        if cpf:
            consulta["cpf_por_placa"][placa] = cpf
            consulta["cpfs_pendentes"].add(cpf)

    consulta["placas_pendentes"].discard(placa)

    if consulta["placas_pendentes"]:
        return

    if not consulta["cpfs_pendentes"]:
        finalizar_ranking(client, request_id)
        return

    # Consulta cada CPF encontrado para obter o nome do condutor.
    for cpf in consulta["cpfs_pendentes"]:
        client.publish(
            TOPICO_CONSULTAR_CPF,
            json.dumps({
                "requestId": request_id,
                "cpf": cpf,
            }),
        )


def processar_resposta_ranking_condutor(client, dados):
    request_id = dados.get("requestId")

    consulta = consultas_pendentes.get(request_id)

    if not consulta or consulta.get("tipo") != "ranking":
        return

    cpf = dados.get("cpf")

    if dados.get("sucesso") and cpf:
        consulta["condutores"][cpf] = {
            "cpf": cpf,
            "nome": dados["nome"],
        }

    if cpf:
        consulta["cpfs_pendentes"].discard(cpf)

    if consulta["cpfs_pendentes"]:
        return

    finalizar_ranking(client, request_id)


def finalizar_ranking(client, request_id):
    consulta = consultas_pendentes.get(request_id)

    if not consulta:
        return

    # Soma os pontos de todos os veículos associados ao mesmo CPF.
    pontuacao_por_cpf = {}

    for placa, pontuacao in consulta["pontuacao_por_placa"].items():
        cpf = consulta["cpf_por_placa"].get(placa)

        if not cpf:
            continue

        if cpf not in pontuacao_por_cpf:
            pontuacao_por_cpf[cpf] = 0

        pontuacao_por_cpf[cpf] += pontuacao

    ranking = []

    for cpf, pontuacao in pontuacao_por_cpf.items():
        condutor = consulta["condutores"].get(cpf)

        if not condutor:
            continue

        ranking.append({
            "cpf": cpf,
            "nome": condutor["nome"],
            "pontuacaoTotal": pontuacao,
        })

    # Ordena os condutores pela maior pontuação acumulada.
    ranking.sort(
        key=lambda condutor: condutor["pontuacaoTotal"],
        reverse=True,
    )

    # Mantém somente os cinco primeiros colocados.
    ranking = ranking[:5]

    for posicao, condutor in enumerate(ranking, start=1):
        condutor["posicao"] = posicao

    resposta = {
        "requestId": request_id,
        "sucesso": True,
        "ano": consulta["ano"],
        "ranking": ranking,
    }

    client.publish(
        TOPICO_RESPOSTA_RANKING,
        json.dumps(resposta),
    )

    consultas_pendentes.pop(request_id, None)


def on_message(client, userdata, message):
    try:
        # Usa utf-8-sig para aceitar mensagens com BOM geradas durante testes pelo PowerShell.
        payload = message.payload.decode("utf-8-sig")

        if not payload.strip():
            return

        dados = json.loads(payload)

        print(f"Mensagem recebida em: {message.topic}")
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

        if message.topic == TOPICO_RANKING:
            consultar_ranking(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_CONSULTAR_PLACA:
            request_id = dados.get("requestId")

            consulta = consultas_pendentes.get(request_id)

            if not consulta:
                return

            if consulta.get("tipo") == "veiculo":
                processar_resposta_veiculo(client, dados)

            elif consulta.get("tipo") == "ranking":
                processar_resposta_ranking_veiculo(client, dados)

            return

        if message.topic == TOPICO_RESPOSTA_VEICULOS_POR_CPF:
            processar_resposta_veiculos_por_cpf(client, dados)
            return

        if message.topic == TOPICO_RESPOSTA_CONSULTAR_CPF:
            request_id = dados.get("requestId")

            consulta = consultas_pendentes.get(request_id)

            if not consulta:
                return

            if consulta.get("tipo") == "veiculo":
                processar_resposta_condutor(client, dados)

            elif consulta.get("tipo") == "condutor":
                processar_resposta_condutor_consulta(client, dados)

            elif consulta.get("tipo") == "ranking":
                processar_resposta_ranking_condutor(client, dados)

            return

    except json.JSONDecodeError:
        print("Erro: mensagem recebida não contém um JSON válido.")

    except UnicodeDecodeError:
        print("Erro: mensagem recebida possui codificação inválida.")

    except KeyError as erro:
        print(f"Erro: campo obrigatório ausente: {erro}")

    except ValueError as erro:
        print(f"Erro: valor inválido recebido: {erro}")

    except Exception as erro:
        print(f"Erro inesperado ao processar mensagem: {erro}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

client.on_connect = on_connect
client.on_message = on_message

client.connect("broker", 1883, 60)

print("Microserviço de multas iniciado.")

client.loop_forever()