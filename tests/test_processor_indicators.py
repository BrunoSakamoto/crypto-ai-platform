"""Testes unitários para o cálculo de indicadores do processor.
Não dependem de Redis/Postgres — testam só a lógica pura.
"""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "processor"))

from main import compute_indicators  # noqa: E402


def test_sma_is_mean_of_window():
    prices = deque([10, 20, 30], maxlen=3)
    result = compute_indicators(prices)
    assert result["sma_20"] == 20.0


def test_volatility_zero_for_constant_prices():
    prices = deque([100, 100, 100], maxlen=3)
    result = compute_indicators(prices)
    assert result["volatility"] == 0.0


def test_ema_stays_between_first_and_last_price():
    # com span=20 (alpha baixo), a EMA se move pouco em poucas amostras —
    # o teste garante que ela fica dentro do intervalo dos preços, sem
    # assumir uma reação forte que só apareceria com uma janela maior.
    prices = deque([10, 10, 10, 100], maxlen=4)
    result = compute_indicators(prices)
    assert 10 <= result["ema_20"] <= 100
