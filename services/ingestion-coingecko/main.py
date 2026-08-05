"""
Ingestion worker: faz polling periódico da API pública do CoinGecko
(dados fundamentais + notícias por moeda) e publica no Redis Stream
consumido pelo RAG engine.
"""
import asyncio
import os

import httpx
import orjson
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_NAME = "news_events"
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/status_updates"
POLL_INTERVAL_SECONDS = 300


async def fetch_and_publish(redis_client: redis.Redis) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(COINGECKO_URL)
        response.raise_for_status()
        data = response.json()

    for update in data.get("status_updates", []):
        event = {
            "source": "coingecko",
            "title": update.get("project", {}).get("name", ""),
            "content": update.get("description", ""),
            "published_at": update.get("created_at", ""),
        }
        await redis_client.xadd(STREAM_NAME, orjson.loads(orjson.dumps(event)))


async def main() -> None:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_publish, "interval", seconds=POLL_INTERVAL_SECONDS, args=[redis_client])
    scheduler.start()

    # roda uma vez imediatamente e depois mantém o loop vivo
    await fetch_and_publish(redis_client)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
