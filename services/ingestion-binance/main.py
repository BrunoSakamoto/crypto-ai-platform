"""
Ingestion worker: conecta no WebSocket público da Binance e publica cada
tick de preço em um Redis Stream, para ser consumido pelo processor.

Este é um esqueleto funcional — não trata reconexão exponencial nem
backpressure de produção, mas já ilustra a estrutura do worker.
"""
import asyncio
import os
import orjson
import redis.asyncio as redis
import websockets

BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_NAME = "price_ticks"


async def consume_binance(redis_client: redis.Redis) -> None:
    async for websocket in _reconnecting_ws(BINANCE_WS_URL):
        try:
            async for raw_message in websocket:
                payload = orjson.loads(raw_message)
                event = {
                    "symbol": payload["s"],
                    "price": payload["p"],
                    "quantity": payload["q"],
                    "trade_time": payload["T"],
                }
                await redis_client.xadd(STREAM_NAME, event)
        except websockets.ConnectionClosed:
            continue


async def _reconnecting_ws(url: str):
    """Gera conexões WebSocket, reconectando com backoff simples."""
    backoff = 1
    while True:
        try:
            async with websockets.connect(url) as ws:
                backoff = 1
                yield ws
        except OSError:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


async def main() -> None:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    await consume_binance(redis_client)


if __name__ == "__main__":
    asyncio.run(main())
