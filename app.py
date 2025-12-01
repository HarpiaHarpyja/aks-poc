import traceback
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
    """Conecta ao banco de dados e retorna a lista de e-mails, com logs detalhados."""
    
    print("\n==========================")
    print("🔍 Iniciando get_user_emails()")
    print("==========================\n")

    emails = []
    query = f"SELECT {EMAIL_COLUMN} FROM {USER_TABLE};"

    print(f"📌 SQL montado:\n{query}\n")

    # -------------------------
    # 1. TENTAR CRIAR O ENGINE
    # -------------------------
    try:
        print("⚙️ Tentando criar engine DB...")
        db_engine = connect_with_connector()
        print("✅ Engine criado com sucesso!")
        print(f"   -> Tipo: {type(db_engine)}")
    except Exception as e:
        print("\n❌ ERRO AO CRIAR O ENGINE!")
        print(f"Erro: {e}")
        print("Traceback completo:")
        traceback.print_exc()
        return []  # não adianta continuar

    # -------------------------
    # 2. TENTAR CONECTAR
    # -------------------------
    try:
        print("\n🔌 Tentando conectar ao banco...")
        with db_engine.connect() as db_conn:
            print("✅ Conexão estabelecida!")
            print(f"   -> Tipo: {type(db_conn)}")

            try:
                print("\n▶️ Executando a consulta...")
                result = db_conn.execute(sqlalchemy.text(query))
                print("✅ Consulta executada com sucesso!")

            except Exception as e:
                print("\n❌ ERRO AO EXECUTAR A CONSULTA SQL!")
                print(f"Erro: {e}")
                print("Traceback completo:")
                traceback.print_exc()
                return []

            # -------------------------
            # 3. Ler resultados linha por linha
            # -------------------------
            try:
                print("\n📥 Lendo resultados linha por linha:")
                for idx, row in enumerate(result):
                    print(f"   -> Linha {idx}: {row}")
                    emails.append(row[0])
                print("\n📦 Total de e-mails encontrados:", len(emails))

            except Exception as e:
                print("\n❌ ERRO AO ITERAR RESULTADOS!")
                print(f"Erro: {e}")
                print("Traceback completo:")
                traceback.print_exc()
                return []

    except Exception as e:
        print("\n❌ ERRO AO CONECTAR AO BANCO!")
        print(f"Erro: {e}")
        print("Traceback completo:")
        traceback.print_exc()
        return []

    # -------------------------
    # 4. TENTAR FECHAR O ENGINE
    # -------------------------
    try:
        print("\n🧹 Tentando liberar o pool do engine...")
        db_engine.dispose()
        print("✅ Pool liberado com sucesso!")
    except Exception as e:
        print("\n⚠️ ERRO AO FECHAR O POOL DO ENGINE (não é fatal)")
        print(f"Erro: {e}")
        traceback.print_exc()

    print("\n🏁 Finalizando get_user_emails().")
    print("==========================\n")
    return emails

# --- Execução do Script ---
@app.route('/lista-emails')
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

@app.route('/')
def index():
    return jsonify({"message": "Hello! Try /lista-emails or /stress endpoints."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)