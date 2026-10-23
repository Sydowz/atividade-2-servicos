import os
from datetime import datetime

import requests
from flask import Flask, jsonify

app = Flask(__name__)

DADOS_URL = os.getenv("DADOS_URL", "http://dados:5001")


def buscar(caminho):
    resposta = requests.get(f"{DADOS_URL}{caminho}", timeout=10)
    resposta.raise_for_status()
    return resposta.json()


@app.route("/saude")
def saude():
    return jsonify({"status": "ok"})


@app.route("/analise")
def analise():
    aparelhos = {a["id"]: a for a in buscar("/aparelhos")}
    consumos = buscar("/consumos")
    tarifas = {t["hora"]: t for t in buscar("/tarifas")}

    # preco da faixa fora de ponta, usado para simular o deslocamento de uso
    preco_fora_ponta = min(t["preco_branca"] for t in tarifas.values())

    total_kwh = 0
    custo_branca = 0
    custo_convencional = 0
    por_faixa = {}
    por_aparelho = {}
    por_hora = {h: 0 for h in range(24)}
    dias = set()
    economia = 0

    for c in consumos:
        data_hora = datetime.fromisoformat(c["data_hora"])
        hora = data_hora.hour
        dias.add(data_hora.date())
        tarifa = tarifas[hora]
        kwh = c["kwh"]
        custo = kwh * tarifa["preco_branca"]

        total_kwh += kwh
        custo_branca += custo
        custo_convencional += kwh * tarifa["preco_convencional"]
        por_hora[hora] += kwh

        faixa = por_faixa.setdefault(tarifa["faixa"], {"kwh": 0, "custo": 0})
        faixa["kwh"] += kwh
        faixa["custo"] += custo

        aparelho = aparelhos[c["aparelho_id"]]
        item = por_aparelho.setdefault(
            aparelho["nome"], {"kwh": 0, "custo": 0, "deslocavel": aparelho["deslocavel"]}
        )
        item["kwh"] += kwh
        item["custo"] += custo

        # se o aparelho pode ser deslocado, o que foi gasto fora da faixa barata poderia custar menos
        if aparelho["deslocavel"]:
            economia += kwh * (tarifa["preco_branca"] - preco_fora_ponta)

    num_dias = len(dias) or 1
    hora_pico = max(por_hora, key=por_hora.get)

    ranking = [
        {
            "aparelho": nome,
            "kwh": round(v["kwh"], 2),
            "custo": round(v["custo"], 2),
            "deslocavel": v["deslocavel"],
        }
        for nome, v in sorted(por_aparelho.items(), key=lambda x: x[1]["custo"], reverse=True)
    ]

    faixas = {
        nome: {"kwh": round(v["kwh"], 2), "custo": round(v["custo"], 2)}
        for nome, v in por_faixa.items()
    }

    # projecao simples: media diaria multiplicada por 30
    fatura_branca = custo_branca / num_dias * 30
    fatura_convencional = custo_convencional / num_dias * 30
    economia_mensal = economia / num_dias * 30

    sugestoes = []
    for item in ranking:
        if item["deslocavel"]:
            sugestoes.append(
                f"Use {item['aparelho']} fora do horario de ponta (18h as 20h) para pagar menos."
            )
    if fatura_branca < fatura_convencional:
        melhor_tarifa = "branca"
    else:
        melhor_tarifa = "convencional"

    return jsonify({
        "dias_analisados": num_dias,
        "total_kwh": round(total_kwh, 2),
        "hora_pico": hora_pico,
        "consumo_por_hora": {h: round(v / num_dias, 3) for h, v in por_hora.items()},
        "por_faixa": faixas,
        "ranking_aparelhos": ranking,
        "fatura_mensal_branca": round(fatura_branca, 2),
        "fatura_mensal_convencional": round(fatura_convencional, 2),
        "melhor_tarifa": melhor_tarifa,
        "economia_mensal_possivel": round(economia_mensal, 2),
        "sugestoes": sugestoes,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
