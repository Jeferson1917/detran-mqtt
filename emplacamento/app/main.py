import paho.mqtt.client as mqtt


# Callback executado quando o microserviço consegue se conectar ao broker.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Conectado ao broker MQTT. Código: {reason_code}")


# Cria o cliente MQTT que será utilizado pelo microserviço.
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Define o callback responsável por tratar a conexão.
client.on_connect = on_connect

# O nome broker será resolvido pelo Docker Compose para o container responsável pelo Mosquitto.
client.connect("broker", 1883, 60)

# Mantém o microserviço executando e processando mensagens MQTT.
client.loop_forever()