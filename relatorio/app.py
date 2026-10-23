import csv
import io
import os

import requests
from flask import Flask, Response, jsonify, render_template_string

app = Flask(__name__)

PROCESSAMENTO_URL = os.getenv("PROCESSAMENTO_URL", "http://processamento:5002")

NOMES_FAIXA = {
    "ponta": "Ponta (18h-20h)",
    "intermediaria": "Intermediaria (17h e 21h)",
    "fora_ponta": "Fora de ponta",
}

PAGINA = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Relatorio de Energia</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 30px auto; color: #333; }
        h1 { color: #1a5276; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 25px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background: #1a5276; color: white; }
        .destaque { background: #eafaf1; padding: 12px; border-left: 5px solid #27ae60; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>Relatorio de Consumo de Energia</h1>
    <p>Periodo analisado: {{ r.dias_analisados }} dias | Consumo total: {{ r.total_kwh }} kWh |
       Hora de maior consumo: {{ r.hora_pico }}h</p>

    <h2>Fatura mensal estimada</h2>
    <table>
        <tr><th>Tarifa convencional</th><th>Tarifa branca</th></tr>
        <tr><td>R$ {{ r.fatura_mensal_convencional }}</td><td>R$ {{ r.fatura_mensal_branca }}</td></tr>
    </table>
    <div class="destaque">
        Melhor opcao: tarifa <b>{{ r.melhor_tarifa }}</b>.<br>
        Deslocando o uso dos aparelhos flexiveis para fora da ponta,
        a economia possivel e de <b>R$ {{ r.economia_mensal_possivel }}</b> por mes.
    </div>

    <h2>Consumo por faixa horaria</h2>
    <table>
        <tr><th>Faixa</th><th>kWh</th><th>Custo (R$)</th></tr>
        {% for faixa, v in r.por_faixa.items() %}
        <tr><td>{{ nomes[faixa] }}</td><td>{{ v.kwh }}</td><td>{{ v.custo }}</td></tr>
        {% endfor %}
    </table>

    <h2>Ranking de aparelhos</h2>
    <table>
        <tr><th>Aparelho</th><th>kWh</th><th>Custo (R$)</th><th>Pode mudar de horario?</th></tr>
        {% for a in r.ranking_aparelhos %}
        <tr>
            <td>{{ a.aparelho }}</td><td>{{ a.kwh }}</td><td>{{ a.custo }}</td>
            <td>{{ "Sim" if a.deslocavel else "Nao" }}</td>
        </tr>
        {% endfor %}
    </table>

    <h2>Sugestoes</h2>
    <ul>
        {% for s in r.sugestoes %}<li>{{ s }}</li>{% endfor %}
    </ul>

    <p><a href="/relatorio.json">Ver em JSON</a> | <a href="/relatorio.csv">Baixar CSV</a></p>
</body>
</html>
"""


def buscar_analise():
    resposta = requests.get(f"{PROCESSAMENTO_URL}/analise", timeout=30)
    resposta.raise_for_status()
    return resposta.json()


@app.route("/")
def relatorio_html():
    return render_template_string(PAGINA, r=buscar_analise(), nomes=NOMES_FAIXA)


@app.route("/relatorio.json")
def relatorio_json():
    return jsonify(buscar_analise())


@app.route("/relatorio.csv")
def relatorio_csv():
    r = buscar_analise()
    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(["aparelho", "kwh", "custo", "deslocavel"])
    for a in r["ranking_aparelhos"]:
        escritor.writerow([a["aparelho"], a["kwh"], a["custo"], a["deslocavel"]])
    return Response(
        saida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=relatorio_energia.csv"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
