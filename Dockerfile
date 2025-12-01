# Usa uma imagem base Python slim para menor tamanho
FROM python:3.9-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

# Copia o código da aplicação
COPY app.py .

# A aplicação escuta na porta 8080
EXPOSE 8080

# Comando para iniciar o servidor Flask
CMD ["python", "-u", "app.py"]