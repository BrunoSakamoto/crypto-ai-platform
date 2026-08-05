"""
Processing worker: consome o Redis Stream 'price_ticks' via consumer group,
calcula indicadores técnicos simples (SMA, EMA, volatilidade) sobre uma
janela deslizante em memória, e persiste no TimescaleDB.

O uso de consumer group é o que permite escalar horizontalmente este
worker (múltiplas réplicas dividem o trabalho automaticamente).
"""
import asyncio
import os
from collections import defaultdict, deque

import asyncpg
import numpy as np
import redis.asyncio as redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_NAME = "price_ticks"
GROUP_NAME = "processor-group"
CONSUMER_NAME = os.getenv("HOSTNAME", "processor-1")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://crypto:change_me@localhost:5432/crypto_platform",
)

WINDOW_SIZE = 20
price_windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))


async def ensure_group(redis_client: redis.Redis) -> None:
    try:
        await redis_client.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except redis.ResponseError:
        pass  # grupo já existe


def compute_indicators(prices: deque) -> dict:
    arr = np.array(prices, dtype=float)
    return {
        "sma_20": float(arr.mean()),
        "ema_20": float(_ema(arr)),
        "volatility": float(arr.std()),
    }


def _ema(arr: np.ndarray, span: int = 20) -> float:
    alpha = 2 / (span + 1)
    ema = arr[0]
    for price in arr[1:]:
        ema = alpha * price + (1 - alpha) * ema
    return ema


async def consume_loop(redis_client: redis.Redis, db_pool: asyncpg.Pool) -> None:
    await ensure_group(redis_client)
    while True:
        response = await redis_client.xreadgroup(
            GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=50, block=5000
        )
        if not response:
            continue

        for _, messages in response:
            for message_id, fields in messages:
                symbol = fields["symbol"]
                price = float(fields["price"])
                price_windows[symbol].append(price)

                async with db_pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO price_ticks (time, symbol, price) VALUES (now(), $1, $2)",
                        symbol, price,
                    )
                    if len(price_windows[symbol]) == WINDOW_SIZE:
                        indicators = compute_indicators(price_windows[symbol])
                        await conn.execute(
                            """INSERT INTO indicators (time, symbol, sma_20, ema_20, volatility)
                               VALUES (now(), $1, $2, $3, $4)""",
                            symbol, indicators["sma_20"], indicators["ema_20"], indicators["volatility"],
                        )

                await redis_client.xack(STREAM_NAME, GROUP_NAME, message_id)


async def main() -> None:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    await consume_loop(redis_client, db_pool)


if __name__ == "__main__":
    asyncio.run(main())
