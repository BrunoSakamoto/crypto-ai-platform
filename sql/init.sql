-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;

-- Preços em tempo real (série temporal)
CREATE TABLE IF NOT EXISTS price_ticks (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    price       DOUBLE PRECISION NOT NULL,
    volume      DOUBLE PRECISION
);
SELECT create_hypertable('price_ticks', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_price_ticks_symbol_time ON price_ticks (symbol, time DESC);

-- Indicadores calculados pelo processor
CREATE TABLE IF NOT EXISTS indicators (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    sma_20      DOUBLE PRECISION,
    ema_20      DOUBLE PRECISION,
    volatility  DOUBLE PRECISION
);
SELECT create_hypertable('indicators', 'time', if_not_exists => TRUE);

-- Notícias e eventos indexados para o RAG
CREATE TABLE IF NOT EXISTS news_chunks (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    title       TEXT,
    published_at TIMESTAMPTZ,
    content     TEXT NOT NULL,
    embedding   VECTOR(384)
);
CREATE INDEX IF NOT EXISTS idx_news_chunks_embedding
    ON news_chunks USING hnsw (embedding vector_cosine_ops);
