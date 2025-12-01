import traceback
from flask import Flask, request, jsonify
import time
import os 

import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pymysql
from typing import List, Tuple

app = Flask(__name__)

# --- Configurações ---
INSTANCE_CONNECTION_NAME = "telemetria-rumo-9ccc4:us-central1:grafana-server-harpia"
DB_USER = "grafana_user"
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = "grafana"
IP_TYPE = IPTypes.PUBLIC

USER_TABLE = "user" 
EMAIL_COLUMN = "email"

# ============================================================
# 🔧 Criar UM ÚNICO connector global — evita Unclosed sessions
# ============================================================
print("🔧 Inicializando Connector global...")
GLOBAL_CONNECTOR = Connector(ip_type=IP_TYPE, refresh_strategy="LAZY")
print("✅ Connector global criado com sucesso!")


# ==================================================================
# Função segura de conexão — sem criar múltiplas sessões aiohttp
# ==================================================================
def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """Inicializa um pool de conexões reutilizando o connector global."""

    print("⚙️ Criando engine com conector global...")

    def getconn() -> pymysql.connections.Connection:
        print("🔌 Abrindo conexão com MySQL via Cloud SQL Connector...")
        conn = GLOBAL_CONNECTOR.connect(
            INSTANCE_CONNECTION_NAME,
            "pymysql",
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
        )
        print("   -> Conexão obtida!")
        return conn

    engine = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
    )

    print("✅ Engine criado com sucesso!")
    return engine


# ==================================================================
# Função principal — agora SEM warnings de sessão não fechada
# ==================================================================
def get_user_emails() -> Tuple[List[str], str]:
    log = ""
    emails = []

    log += "\n==========================\n"
    log += "🔍 Iniciando get_user_emails()\n"
    log += "==========================\n\n"

    query = f"SELECT {EMAIL_COLUMN} FROM {USER_TABLE};"
    log += f"📌 SQL montado:\n{query}\n\n"

    # -----------------------------------------------------
    # 1. Criar engine
    # -----------------------------------------------------
    log += "⚙️ Tentando criar engine DB...\n"
    try:
        db_engine = connect_with_connector()
        log += "✅ Engine criado com sucesso!\n"
    except Exception:
        log += "❌ ERRO ao criar engine!\n"
        log += traceback.format_exc()
        return [], log

    # -----------------------------------------------------
    # 2. Conectar e consultar
    # -----------------------------------------------------
    log += "\n🔌 Tentando conectar ao banco...\n"
    try:
        with db_engine.connect() as db_conn:
            log += "✅ Conexão estabelecida!\n"

            try:
                log += "\n▶️ Executando consulta...\n"
                result = db_conn.execute(sqlalchemy.text(query))
                log += "✅ Consulta OK!\n"
            except Exception:
                log += "❌ ERRO ao executar SQL!\n"
                log += traceback.format_exc()
                return [], log

            log += "\n📥 Lendo resultados:\n"
            try:
                for idx, row in enumerate(result):
                    log += f"   -> Linha {idx}: {row}\n"
                    emails.append(row[0])
            except Exception:
                log += "❌ ERRO ao iterar resultados!\n"
                log += traceback.format_exc()
                return [], log

    except Exception:
        log += "❌ ERRO ao conectar/consultar!\n"
        log += traceback.format_exc()
        return [], log

    # -----------------------------------------------------
    # 3. Fechar engine
    # -----------------------------------------------------
    log += "\n🧹 Fechando o engine...\n"
    try:
        db_engine.dispose()
        log += "   -> Engine dispose OK!\n"
    except Exception:
        log += "⚠️ ERRO ao liberar engine!\n"
        log += traceback.format_exc()

    # -----------------------------------------------------
    # 4. Finalização
    # -----------------------------------------------------
    log += "\n🏁 Finalizando get_user_emails().\n"
    log += "==========================\n"

    return emails, log

# ==================================================================
# Rotas Flask
# ==================================================================
@app.route('/lista-emails')
def lista_emails():
    lst = get_user_emails()
    return jsonify({
        "emails": emails,
        "debug": debug_info
    })


# Stress CPU
def cpu_intensive_task(duration_seconds):
    start_time = time.time()
    count = 0
    while (time.time() - start_time) < duration_seconds:
        count += 1
        _ = 2 ** 1000
    return count

@app.route('/stress')
def stress_cpu():
    try:
        duration = float(request.args.get('duration', 0.5))
    except ValueError:
        duration = 0.5

    count = cpu_intensive_task(duration)
    return jsonify({
        "message": f"Stress {duration}s",
        "iterations": count
    })


@app.route('/')
def index():
    return jsonify({"message": "Hello! Try /lista-emails or /stress"})


# ==================================================================
# Encerramento limpo — evita UNCL0SED CLIENT SESSION
# ==================================================================
@app.teardown_appcontext
def shutdown_context(exception=None):
    print("\n🛑 Encerrando Flask — fechando Connector global...")
    try:
        GLOBAL_CONNECTOR.close()
        print("✅ GLOBAL_CONNECTOR fechado sem erros!")
    except Exception as e:
        print("⚠️ Erro ao fechar Connector:")
        traceback.print_exc()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)