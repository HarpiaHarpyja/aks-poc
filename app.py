from flask import Flask, request, jsonify
import time
import os 

import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pymysql
from typing import List

app = Flask(__name__)

# # --- Variáveis de Configuração ---
INSTANCE_CONNECTION_NAME = "telemetria-rumo-9ccc4:us-central1:grafana-server-harpia"
DB_USER = "grafana_user"
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = "grafana"

IP_TYPE = IPTypes.PUBLIC

USER_TABLE = "user" 
EMAIL_COLUMN = "email"

# --- Função de Conexão ---
def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """Inicializa um pool de conexões para a instância do Cloud SQL."""
    
    connector = Connector(ip_type=IP_TYPE, refresh_strategy="LAZY")

    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pymysql",
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
        )
        return conn

    # 3. Cria o engine do SQLAlchemy com o método de conexão seguro
    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30, # segundos
    )
    return pool

def get_user_emails() -> List[str]:
    """Conecta ao banco de dados e retorna a lista de e-mails."""
    
    # 1. Estabelece a conexão (pool)
    db_engine = connect_with_connector()
    emails = []
    
    query = f"SELECT {EMAIL_COLUMN} FROM {USER_TABLE};" 

    try:
        print("Conectando e executando a consulta...")
        with db_engine.connect() as db_conn:
            result = db_conn.execute(sqlalchemy.text(query))
            
            for row in result:
                print(row[0])
                emails.append(row[0]) 

            print("Consulta concluída com sucesso!")

    except Exception as e:
        print(f"Ocorreu um erro ao conectar ou consultar o banco de dados: {e}")
        
    finally:
        # Fechar o pool de conexões (importante)
        db_engine.dispose()
        
    return emails

# --- Execução do Script ---
@app.route('/')
def lista_emails():
    lista_emails = get_user_emails()
    
    if lista_emails:
        return jsonify(lista_emails)
    else:
        return jsonify("Nenhum e-mail encontrado ou erro de conexão/consulta.")

# Função que simula o consumo de CPU
def cpu_intensive_task(duration_seconds):
    """Executa um loop para consumir CPU."""
    start_time = time.time()
    count = 0
    while (time.time() - start_time) < duration_seconds:
        # A operação de elevação ao quadrado é intencionalmente intensiva em CPU
        count += 1
        _ = 2 ** 1000
    return count

@app.route('/stress')
def stress_cpu():
    # Define a duração do stress em segundos (0.5s por padrão)
    try:
        duration = float(request.args.get('duration', 0.5))
    except ValueError:
        duration = 0.5
        
    count = cpu_intensive_task(duration)
    
    return jsonify({
        "message": f"Stress de CPU executado por {duration} segundos.",
        "iterations": count
    })

@app.route('/hello')
def index():
    return jsonify({"message": "Hello world!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)