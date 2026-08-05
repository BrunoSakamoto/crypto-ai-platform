"""
API pública da plataforma. Expõe preços, indicadores e o endpoint de
perguntas (RAG). Autenticação via JWT e rate limiting por IP.
"""
import os
from datetime import datetime, timedelta

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Request
from jose import JWTError, jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://crypto:change_me@localhost:5432/crypto_platform",
)
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_too")
JWT_ALGORITHM = "HS256"

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Crypto AI Platform API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

db_pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup() -> None:
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)


@app.on_event("shutdown")
async def shutdown() -> None:
    if db_pool:
        await db_pool.close()


def verify_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/prices/{symbol}")
@limiter.limit("60/minute")
async def get_prices(symbol: str, request: Request, user: str = Depends(verify_token)) -> list[dict]:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT time, price FROM price_ticks
               WHERE symbol = $1 ORDER BY time DESC LIMIT 100""",
            symbol.upper(),
        )
    return [dict(row) for row in rows]


@app.get("/indicators/{symbol}")
@limiter.limit("60/minute")
async def get_indicators(symbol: str, request: Request, user: str = Depends(verify_token)) -> list[dict]:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT time, sma_20, ema_20, volatility FROM indicators
               WHERE symbol = $1 ORDER BY time DESC LIMIT 50""",
            symbol.upper(),
        )
    return [dict(row) for row in rows]


@app.post("/ask")
@limiter.limit("10/minute")
async def ask(question: str, request: Request, user: str = Depends(verify_token)) -> dict:
    from query import get_answer  # import local para não acoplar startup ao modelo de embeddings
    return await get_answer(db_pool, question)


def create_access_token(subject: str, expires_minutes: int = 60) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode({"sub": subject, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)
