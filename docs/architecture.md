# Arquitetura

## Fluxo de dados

```
Binance WebSocket ─┐
                    ├─→ Ingestion workers ─→ Redis Streams ─┬─→ Processing workers ─┐
CoinGecko REST ─────┘                                       └─→ RAG engine ─────────┤
                                                                                     ↓
                                                                TimescaleDB + pgvector
                                                                                     ↓
                                                                     API (FastAPI) → cliente
```

- Ingestion workers normalizam eventos das duas fontes e publicam em Redis
  Streams — o ponto de desacoplamento entre produtores e consumidores.
- Processing workers e RAG engine consomem via consumer groups distintos:
  o mesmo evento pode ser lido por ambos sem competirem entre si.
- Ambos persistem no mesmo Postgres (TimescaleDB para séries temporais,
  pgvector para embeddings) — ver ADR 0002.

## RAG engine — trilha de indexação e trilha de resposta

```
indexação: notícia bruta → chunking → embeddings ─┐
                                                   ├─→ índice vetorial (pgvector)
resposta: pergunta → embedding da pergunta ────────┘         ↓
                              busca por similaridade ←────────┘
                                        ↓
                          geração da resposta (contexto + pergunta no LLM)
```

O mesmo modelo de embeddings é usado nas duas trilhas — embeddings de
modelos diferentes não são comparáveis no mesmo índice. A avaliação da
qualidade do RAG roda offline, separada do fluxo síncrono de produção,
comparando um conjunto de perguntas-resposta esperadas.

## Deploy em Kubernetes

| Workload | Tipo | Escala |
|---|---|---|
| Ingestion workers | Deployment | fixa (2 réplicas) |
| Message broker (Redis) | StatefulSet | fixa (3 réplicas) |
| Processing workers | Deployment | HPA por tamanho de fila (KEDA), 2–8 |
| RAG engine | Deployment | HPA por CPU, 1–4 |
| Camada de dados (Postgres) | StatefulSet | fixa, fora do autoscaling |
| API | Deployment | HPA por CPU/latência, 2–6, atrás de Ingress |

Ver ADR 0003 para a justificativa de cada estratégia de escala.

## Decisões documentadas (ADRs)

- [0001 — Redis Streams como broker](adr/0001-message-broker-choice.md)
- [0002 — pgvector no mesmo Postgres](adr/0002-vector-db-same-postgres.md)
- [0003 — estratégias de HPA por workload](adr/0003-hpa-strategy.md)
