FROM python:3.12-slim

# Define o diretório de trabalho dentro do container.
WORKDIR /app

# Copia as dependências do microserviço.
COPY requirements.txt .

# Instala as dependências Python.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do microserviço.
COPY app/ ./app/

# Executa o microserviço como módulo para preservar os imports do pacote app.
CMD ["python", "-u", "-m", "app.main"]