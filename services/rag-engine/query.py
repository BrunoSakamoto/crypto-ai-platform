"""
RAG engine — trilha de resposta: dado uma pergunta do usuário, embeda a
pergunta, busca os trechos mais relevantes no pgvector (top-k por
similaridade de cosseno) e monta o prompt final para o LLM.

Chamado pela API (services/api/main.py) através de get_answer().
"""
import os

import asyncpg

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
TOP_K = 5

_model = None


def _get_model():
    """Import e carrega o modelo só quando necessário — evita puxar
    sentence-transformers (pesado) apenas para montar um prompt em testes."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


async def retrieve_context(db_pool: asyncpg.Pool, question: str, top_k: int = TOP_K) -> list[dict]:
    embedding = _get_model().encode(question).tolist()

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT title, content, 1 - (embedding <=> $1::vector) AS similarity
               FROM news_chunks
               ORDER BY embedding <=> $1::vector
               LIMIT $2""",
            str(embedding), top_k,
        )
    return [dict(row) for row in rows]


def build_prompt(question: str, context_chunks: list[dict]) -> str:
    context_text = "\n\n".join(f"- {c['title']}: {c['content']}" for c in context_chunks)
    return (
        "Responda à pergunta usando apenas o contexto abaixo. "
        "Se o contexto não for suficiente, diga que não sabe.\n\n"
        f"Contexto:\n{context_text}\n\nPergunta: {question}"
    )


async def get_answer(db_pool: asyncpg.Pool, question: str) -> dict:
    """Ponto de entrada usado pela API. A chamada real ao LLM (Anthropic API)
    fica de fora deste esqueleto — plugue seu client aqui."""
    context_chunks = await retrieve_context(db_pool, question)
    prompt = build_prompt(question, context_chunks)
    return {
        "prompt": prompt,
        "sources": [c["title"] for c in context_chunks],
    }
