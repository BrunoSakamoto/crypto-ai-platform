"""
RAG engine — trilha de indexação: consome o Redis Stream 'news_events',
divide o conteúdo em chunks, gera embeddings e persiste no pgvector.

Usa o mesmo modelo de embeddings que a trilha de resposta (query.py) usa
para a pergunta do usuário — isso é essencial, embeddings de modelos
diferentes não são comparáveis no mesmo índice.
"""
import asyncio
import os

import asyncpg
import redis.asyncio as redis
from sentence_transformers import SentenceTransformer

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_NAME = "news_events"
GROUP_NAME = "rag-indexer-group"
CONSUMER_NAME = os.getenv("HOSTNAME", "rag-engine-1")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://crypto:change_me@localhost:5432/crypto_platform",
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE_CHARS = 800


def chunk_text(text: str, size: int = CHUNK_SIZE_CHARS) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [text]


async def ensure_group(redis_client: redis.Redis) -> None:
    try:
        await redis_client.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except redis.ResponseError:
        pass


async def index_loop(redis_client: redis.Redis, db_pool: asyncpg.Pool, model: SentenceTransformer) -> None:
    await ensure_group(redis_client)
    while True:
        response = await redis_client.xreadgroup(
            GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=20, block=5000
        )
        if not response:
            continue

        for _, messages in response:
            for message_id, fields in messages:
                chunks = chunk_text(fields.get("content", ""))
                embeddings = model.encode(chunks)

                async with db_pool.acquire() as conn:
                    for chunk, embedding in zip(chunks, embeddings):
                        await conn.execute(
                            """INSERT INTO news_chunks (source, title, published_at, content, embedding)
                               VALUES ($1, $2, now(), $3, $4)""",
                            fields.get("source", "unknown"),
                            fields.get("title", ""),
                            chunk,
                            str(embedding.tolist()),
                        )

                await redis_client.xack(STREAM_NAME, GROUP_NAME, message_id)


async def main() -> None:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    model = SentenceTransformer(EMBEDDING_MODEL)
    await index_loop(redis_client, db_pool, model)


if __name__ == "__main__":
    asyncio.run(main())
