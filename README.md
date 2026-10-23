# Gestão de Energia - Microsserviços

Atividade para Nota 2 (Serviços). O sistema analisa o consumo de energia de uma casa
e compara a **tarifa convencional** com a **tarifa branca** (preço varia por horário),
sugerindo quais aparelhos mudar de horário para economizar.

## Serviços

| Serviço | Porta | Função |
|---|---|---|
| `dados` | 5001 | API Flask com PostgreSQL: aparelhos, consumos e tarifas (leitura/escrita) |
| `processamento` | 5002 | Busca os dados e calcula custo por faixa, ranking, fatura e economia |
| `relatorio` | 5003 | Chama o processamento e gera o relatório (HTML, JSON ou CSV) |
| `banco` | - | PostgreSQL |

```
Navegador -> relatorio (5003) -> processamento (5002) -> dados (5001) -> banco (PostgreSQL)
```

## Como rodar

```
docker compose up --build
```

Depois acesse:

- Relatório HTML: http://localhost:5003
- Relatório JSON: http://localhost:5003/relatorio.json
- Relatório CSV: http://localhost:5003/relatorio.csv
- Análise (processamento): http://localhost:5002/analise
- Dados: http://localhost:5001/aparelhos, `/consumos`, `/tarifas`

Na primeira execução o serviço de dados cria as tabelas e gera 7 dias de consumo simulado.

## Registrando novos dados

```
curl -X POST http://localhost:5001/aparelhos -H "Content-Type: application/json" \
  -d '{"nome": "Microondas", "potencia_w": 1200, "deslocavel": false}'

curl -X POST http://localhost:5001/consumos -H "Content-Type: application/json" \
  -d '{"aparelho_id": 1, "data_hora": "2026-10-20T19:00:00", "kwh": 2.5}'
```

## Regras de cálculo

- **Tarifa branca:** ponta (18h-20h) R$ 1,20/kWh, intermediária (17h e 21h) R$ 0,80, fora de ponta R$ 0,50.
- **Tarifa convencional:** R$ 0,75/kWh fixo.
- **Fatura mensal:** média diária do período × 30.
- **Economia possível:** kWh dos aparelhos "deslocáveis" gastos fora da faixa barata × diferença para o preço fora de ponta.
