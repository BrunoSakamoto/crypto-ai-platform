# ADR 0003: estratégias de autoscaling diferentes por workload

## Contexto
O cluster tem workloads com perfis de carga muito diferentes: processing
workers reagem ao tamanho da fila de eventos, a API reage a requisições
HTTP, e os workers de ingestão têm carga previsível e constante.

## Decisão
- **Ingestion workers**: réplicas fixas (não escalam), pois a carga é
  limitada pelo número de fontes de dados, não por volume de tráfego.
- **Processing workers**: HPA baseado em métrica customizada do tamanho da
  fila (via KEDA), já que picos de mercado geram rajadas de eventos que
  CPU sozinha não capturaria a tempo.
- **RAG engine**: HPA por CPU, já que gerar embeddings é CPU-bound e a
  fila de notícias tem volume muito menor e mais previsível que a de
  preços.
- **API**: HPA por CPU/latência, padrão para workloads request-response.

## Consequências
- Cada workload escala pelo sinal que de fato reflete sua carga real, em
  vez de aplicar a mesma regra de CPU em tudo.
- Introduz a dependência do KEDA para métricas customizadas baseadas em
  fila, que precisa ser instalada no cluster além do HPA nativo.
