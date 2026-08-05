# ADR 0002: pgvector no mesmo Postgres em vez de um vector DB dedicado

## Contexto
O RAG engine precisa de um índice vetorial para busca por similaridade
sobre embeddings de notícias. Existem vector DBs dedicados (Qdrant, Weaviate,
Pinecone) e a extensão pgvector, que roda dentro do próprio Postgres.

## Decisão
Usar pgvector na mesma instância do TimescaleDB que já armazena preços e
indicadores.

## Alternativas consideradas
- **Vector DB dedicado (Qdrant/Weaviate)**: melhor desempenho em escala
  muito grande e features avançadas de filtragem, mas adiciona mais um
  serviço stateful para operar, monitorar e fazer backup.

## Consequências
- Uma peça de infraestrutura a menos: um único banco para operar, uma
  única estratégia de backup.
- Transações que envolvem dados relacionais e busca vetorial na mesma
  query ficam triviais (ex.: filtrar notícias por data E similaridade).
- Índice HNSW do pgvector é suficiente para o volume de notícias deste
  projeto; se o volume de vetores crescer ordens de grandeza, um vector DB
  dedicado passa a fazer mais sentido — decisão revisável.
