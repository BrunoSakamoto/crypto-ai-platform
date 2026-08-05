# Helm charts

Placeholder para os charts de deploy em Kubernetes, um por serviço,
espelhando a topologia documentada em `docs/architecture.md`:

- `ingestion-binance/` — Deployment, réplicas fixas
- `ingestion-coingecko/` — Deployment, réplicas fixas
- `processor/` — Deployment + HPA baseado em KEDA (fila)
- `rag-engine/` — Deployment + HPA por CPU
- `api/` — Deployment + HPA por CPU/latência + Ingress
- `postgres/` — StatefulSet + PVC (ou usar um chart gerenciado como Bitnami)
- `redis/` — StatefulSet + PVC

Próximo passo: gerar os charts com `helm create <nome>` e adaptar os
templates de Deployment/Service/HPA para os valores definidos nos ADRs.
