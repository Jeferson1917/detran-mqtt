FROM python:3.12-slim

# Define o diretório de trabalho dentro do container.
WORKDIR /app

# Copia as dependências do microserviço.
COPY requirements.txt .

# Instala as dependências Python.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do microserviço.
COPY app/ ./app/

# Executa o Python sem bufferizar a saída, permitindo acompanhar os logs do microserviço normalmente pelo Docker, apenas com CMD ["python", "app/main.py"] não estava retornando os logs corretamente.
CMD ["python", "-u", "app/main.py"]