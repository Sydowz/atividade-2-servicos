import os
import time
import random
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request

app = Flask(__name__)


def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "banco"),
        dbname=os.getenv("DB_NAME", "energia"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def consultar(sql, params=None):
    conn = conectar()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    linhas = cur.fetchall()
    conn.close()
    return linhas


def executar(sql, params=None):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()


def criar_tabelas():
    executar("""
        CREATE TABLE IF NOT EXISTS aparelhos (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            potencia_w INTEGER NOT NULL,
            deslocavel BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    executar("""
        CREATE TABLE IF NOT EXISTS consumos (
            id SERIAL PRIMARY KEY,
            aparelho_id INTEGER REFERENCES aparelhos(id),
            data_hora TIMESTAMP NOT NULL,
            kwh NUMERIC(8, 3) NOT NULL
        )
    """)
    executar("""
        CREATE TABLE IF NOT EXISTS tarifas (
            hora INTEGER PRIMARY KEY,
            faixa TEXT NOT NULL,
            preco_branca NUMERIC(6, 2) NOT NULL,
            preco_convencional NUMERIC(6, 2) NOT NULL
        )
    """)


def popular_dados():
    # so popula se o banco estiver vazio
    if consultar("SELECT COUNT(*) AS total FROM aparelhos")[0]["total"] > 0:
        return

    # tarifa branca: ponta 18h-20h, intermediaria 17h e 21h, fora de ponta o resto
    for hora in range(24):
        if 18 <= hora <= 20:
            faixa, preco = "ponta", 1.20
        elif hora in (17, 21):
            faixa, preco = "intermediaria", 0.80
        else:
            faixa, preco = "fora_ponta", 0.50
        executar(
            "INSERT INTO tarifas VALUES (%s, %s, %s, %s)",
            (hora, faixa, preco, 0.75),
        )

    # (nome, potencia em W, deslocavel, horas de uso, chance de uso na hora)
    aparelhos = [
        ("Chuveiro eletrico", 5500, False, [6, 7, 19, 20], 0.5),
        ("Ar-condicionado", 1400, False, list(range(13, 23)), 0.6),
        ("Maquina de lavar", 1000, True, [19, 20], 0.35),
        ("Lava-loucas", 1500, True, [20, 21], 0.4),
        ("Ferro de passar", 1200, True, [18, 19], 0.25),
        ("Computador", 200, False, list(range(8, 23)), 0.8),
        ("TV", 100, False, list(range(18, 24)), 0.8),
        ("Geladeira", 150, False, list(range(24)), 1.0),
    ]

    random.seed(42)
    inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)

    for nome, potencia, deslocavel, horas, chance in aparelhos:
        conn = conectar()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO aparelhos (nome, potencia_w, deslocavel) VALUES (%s, %s, %s) RETURNING id",
            (nome, potencia, deslocavel),
        )
        aparelho_id = cur.fetchone()[0]
        for dia in range(7):
            for hora in horas:
                if random.random() <= chance:
                    kwh = round(potencia / 1000 * random.uniform(0.5, 1.0), 3)
                    data_hora = inicio + timedelta(days=dia, hours=hora)
                    cur.execute(
                        "INSERT INTO consumos (aparelho_id, data_hora, kwh) VALUES (%s, %s, %s)",
                        (aparelho_id, data_hora, kwh),
                    )
        conn.commit()
        conn.close()


def iniciar_banco():
    # o banco pode demorar para subir, entao tenta algumas vezes
    for _ in range(30):
        try:
            criar_tabelas()
            popular_dados()
            print("Banco pronto")
            return
        except psycopg2.OperationalError:
            print("Aguardando o banco...")
            time.sleep(2)
    raise RuntimeError("Nao foi possivel conectar ao banco")


@app.route("/saude")
def saude():
    return jsonify({"status": "ok"})


@app.route("/aparelhos", methods=["GET"])
def listar_aparelhos():
    return jsonify(consultar("SELECT * FROM aparelhos ORDER BY id"))


@app.route("/aparelhos", methods=["POST"])
def criar_aparelho():
    corpo = request.get_json()
    executar(
        "INSERT INTO aparelhos (nome, potencia_w, deslocavel) VALUES (%s, %s, %s)",
        (corpo["nome"], corpo["potencia_w"], corpo.get("deslocavel", False)),
    )
    return jsonify({"mensagem": "aparelho criado"}), 201


@app.route("/consumos", methods=["GET"])
def listar_consumos():
    linhas = consultar("SELECT id, aparelho_id, data_hora, kwh FROM consumos ORDER BY data_hora")
    for linha in linhas:
        linha["data_hora"] = linha["data_hora"].isoformat()
        linha["kwh"] = float(linha["kwh"])
    return jsonify(linhas)


@app.route("/consumos", methods=["POST"])
def criar_consumo():
    corpo = request.get_json()
    executar(
        "INSERT INTO consumos (aparelho_id, data_hora, kwh) VALUES (%s, %s, %s)",
        (corpo["aparelho_id"], corpo["data_hora"], corpo["kwh"]),
    )
    return jsonify({"mensagem": "consumo registrado"}), 201


@app.route("/tarifas", methods=["GET"])
def listar_tarifas():
    linhas = consultar("SELECT * FROM tarifas ORDER BY hora")
    for linha in linhas:
        linha["preco_branca"] = float(linha["preco_branca"])
        linha["preco_convencional"] = float(linha["preco_convencional"])
    return jsonify(linhas)


if __name__ == "__main__":
    iniciar_banco()
    app.run(host="0.0.0.0", port=5001)
