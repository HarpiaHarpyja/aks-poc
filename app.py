import traceback
from flask import Flask, request, jsonify
import time
import os 
import pymysql
from typing import List, Tuple

import signal
import sys


app = Flask(__name__)

# --- Configurações ---
DB_USER = "grafana_user"
DB_PASS = os.environ.get("DB_PASS")
if not DB_PASS:
    raise RuntimeError("❌ Variável de ambiente DB_PASS não definida!")
DB_NAME = "grafana"

USER_TABLE = "user" 
EMAIL_COLUMN = "email"


# ==================================================================
# Função segura de conexão — sem criar múltiplas sessões aiohttp
# ==================================================================
def connect_to_db():
    try:
        conn = pymysql.connect(
            host="127.0.0.1",  # Cloud SQL Proxy
            port=3306,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            connect_timeout=10
        )
        print("✅ Conexão com o banco estabelecida via Cloud SQL Proxy!")
        return conn
    except Exception as e:
        print("❌ ERRO ao conectar ao banco via Proxy!")
        traceback.print_exc()
        raise e

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
        conn = connect_to_db()
        with conn.cursor() as cursor:
            log += "✅ Conexão estabelecida!\n"
            try:
                log += "\n▶️ Executando consulta...\n"
                cursor.execute(query)
                result = cursor.fetchall()
                log += "✅ Consulta OK!\n"
            except Exception:
                log += "❌ ERRO ao executar SQL!\n"
                log += traceback.format_exc()
                return [], log
            log += "\n📥 Lendo resultados:\n"
            try:
                for idx, row in enumerate(result):
                    log += f" -> Linha {idx}: {row}\n"
                    emails.append(row[0])
            except Exception:
                log += "❌ ERRO ao iterar resultados!\n"
                log += traceback.format_exc()
                return [], log
    except Exception:
        log += "❌ ERRO ao conectar/consultar!\n"
        log += traceback.format_exc()
        return [], log
    finally:
        try:
            conn.close()
            log += "\n🧹 Conexão encerrada com sucesso!\n"
        except Exception:
            log += "\n⚠️ ERRO ao fechar conexão!\n"
            log += traceback.format_exc()

    # -----------------------------------------------------
    # 3. Finalização
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
        "emails": lst[0],
        "debug": lst[1]
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

def handler(sig, frame):
    print("Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handler)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)