# Crypto AI Platform

Plataforma de análise de criptomoedas em tempo real com uma camada de IA (RAG)
para responder perguntas sobre o mercado usando notícias e dados on-chain como
contexto.

## Arquitetura

```
Binance WS ─┐
            ├─→ Ingestion workers ─→ Redis Streams ─┬─→ Processing workers ─┐
CoinGecko ──┘                                       └─→ RAG engine ─────────┤
                                                                             ↓
                                                         TimescaleDB + pgvector
                                                                             ↓
                                                              API (FastAPI) → cliente
```

Detalhes de cada decisão de arquitetura estão documentados em `docs/adr/`.
Diagramas completos (fluxo de dados, RAG interno, topologia Kubernetes) em
`docs/architecture.md`.

## Serviços

| Serviço | Responsabilidade | Escala |
|---|---|---|
| `services/ingestion-binance` | Consome WebSocket da Binance, publica eventos de preço | fixa |
| `services/ingestion-coingecko` | Faz polling da API do CoinGecko (fundamentos, notícias) | fixa |
| `services/processor` | Consome eventos de preço, calcula indicadores, persiste | HPA por tamanho de fila |
| `services/rag-engine` | Embeda notícias, responde perguntas com contexto | HPA por CPU |
| `services/api` | Expõe REST, autenticação, rate limiting | HPA por CPU/latência |

## Rodando localmente

Pré-requisitos: Docker e Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

A API sobe em `http://localhost:8000/docs`.

## Roadmap

- [x] Ingestão de preços (Binance) e fundamentos (CoinGecko)
- [x] Pipeline assíncrono via Redis Streams
- [x] Cálculo de indicadores técnicos
- [x] RAG sobre notícias (embeddings em pgvector)
- [x] API REST com autenticação
- [ ] Deploy em Kubernetes (Helm charts em `infra/helm`)
- [ ] Autoscaling com KEDA (fila) + HPA padrão (CPU)
- [ ] Dataset de avaliação do RAG (offline eval)
- [ ] Observabilidade (Prometheus + Grafana)

## Testes

```bash
pytest tests/
```
