"""Testes unitários para a montagem do prompt do RAG (sem chamar o modelo)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "rag-engine"))

from query import build_prompt  # noqa: E402


def test_build_prompt_includes_question_and_context():
    chunks = [{"title": "Notícia A", "content": "Bitcoin subiu 5% hoje."}]
    prompt = build_prompt("Por que o Bitcoin subiu?", chunks)

    assert "Por que o Bitcoin subiu?" in prompt
    assert "Notícia A" in prompt
    assert "Bitcoin subiu 5% hoje." in prompt


def test_build_prompt_handles_empty_context():
    prompt = build_prompt("Alguma pergunta", [])
    assert "Alguma pergunta" in prompt
