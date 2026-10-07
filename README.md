# DETRAN MQTT

Sistema distribuído para gerenciamento de veículos, condutores e multas utilizando comunicação assíncrona por MQTT.

## Tecnologias

* Python 3.12
* MQTT
* Eclipse Mosquitto
* Docker
* Docker Compose
* Paho MQTT

## Arquitetura

O sistema é dividido em três microserviços independentes que se comunicam por meio de um broker MQTT.

```text
                    ┌─────────────────────┐
                    │   MQTT Broker       │
                    │   Mosquitto         │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │ Emplacamento │  │  Condutores  │  │    Multas    │
      └──────────────┘  └──────────────┘  └──────────────┘
```

### Microserviços

**Emplacamento**

Responsável pelo cadastro e consulta dos veículos e pelo cálculo do IPVA.

**Condutores**

Responsável pelo cadastro e consulta dos condutores e pela transferência de propriedade dos veículos.

**Multas**

Responsável pelo lançamento e consulta das multas e pelo ranking dos cinco condutores com maior pontuação.

## Comunicação MQTT

As solicitações são publicadas nos tópicos:

```text
detran/requests/emplacamento/emplacar
detran/requests/emplacamento/calcular-ipva
detran/requests/emplacamento/veiculos-por-ano
detran/requests/emplacamento/consultar-placa
detran/requests/emplacamento/veiculos-por-cpf

detran/requests/condutores/cadastrar
detran/requests/condutores/transferir
detran/requests/condutores/consultar-cpf

detran/requests/multas/lancar
detran/requests/multas/veiculo
detran/requests/multas/ano
detran/requests/multas/condutor
detran/requests/multas/ranking
```

As respostas são publicadas nos respectivos tópicos:

```text
detran/responses/emplacamento/...
detran/responses/condutores/...
detran/responses/multas/...
```

As mensagens utilizam JSON e possuem `requestId` para relacionar cada resposta à sua solicitação.

## Requisitos implementados

* [x] Emplacar veículo
* [x] Calcular IPVA
* [x] Transferir proprietário
* [x] Cadastrar condutor
* [x] Lançar multa
* [x] Consultar veículos emplacados em determinado ano
* [x] Consultar multas de um veículo em determinado ano
* [x] Consultar multas de um condutor em determinado ano
* [x] Consultar multas lançadas em determinado ano
* [x] Consultar os cinco condutores com maior pontuação

O cálculo do IPVA utiliza a taxa de 2% sobre o valor do veículo.

O ranking é ordenado pela pontuação total dos condutores e retorna no máximo cinco posições.

## Executando o projeto

É necessário ter Docker e Docker Compose instalados.

Na raiz do projeto, execute:

```powershell
docker compose up --build
```

Os serviços serão iniciados:

```text
detran-mqtt-broker
detran-mqtt-emplacamento
detran-mqtt-condutores
detran-mqtt-multas
```

Para executar em segundo plano:

```powershell
docker compose up --build -d
```

Para verificar os containers:

```powershell
docker compose ps
```

Para acompanhar os logs:

```powershell
docker logs -f detran-mqtt-emplacamento
docker logs -f detran-mqtt-condutores
docker logs -f detran-mqtt-multas
```

Para encerrar o sistema:

```powershell
docker compose down
```

## Exemplo de requisição

Para emplacar um veículo:

```json
{
  "requestId": "001",
  "placa": "ABC1D23",
  "modelo": "Toyota Corolla",
  "valor": 120000,
  "cpf": "12345678900",
  "ano": 2026
}
```

Publicação:

```text
detran/requests/emplacamento/emplacar
```

## Estrutura do projeto

```text
detran-mqt/
├── broker/
│   └── mosquitto/
│       └── config/
│           └── mosquitto.conf
├── emplacamento/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── domain/
│       │   └── veiculo.py
│       ├── repository.py
│       └── main.py
├── condutores/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── domain/
│       │   ├── condutor.py
│       │   └── propriedade.py
│       ├── repository.py
│       └── main.py
├── multas/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── domain/
│       │   └── multa.py
│       ├── repository.py
│       └── main.py
├── docker-compose.yml
└── README.md
```

## Observação

Os dados são armazenados em memória pelos microserviços. Portanto, os registros são perdidos quando os containers são recriados.
