# FILE: task2-cbr-cli/tests/unit/test_analytics.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки аналитики курсов (M-T2-ANALYTICS).
#   SCOPE: Расчёт дельт и %, направление, сортировка топа движений, агрегаты, защита от деления на ноль.
#   DEPENDS: M-T2-ANALYTICS, M-T2-DOMAIN
#   LINKS: V-M-T2-ANALYTICS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_computes_delta_and_pct - дельта и % считаются верно
#   test_direction_classification - направление up/down/flat
#   test_top_movers_sorted_by_abs_pct - топ движений отсортирован по |delta_pct|
#   test_summary_aggregates - агрегаты сводки корректны
#   test_zero_previous_does_not_crash - previous = 0 не валит расчёт
# END_MODULE_MAP
"""Тесты аналитики курсов валют."""

from __future__ import annotations

import pytest

from cbr_cli.analytics import RateAnalyzer
from cbr_cli.domain import Currency, RatesSnapshot


def _analysis_by_code(analyzer: RateAnalyzer, code: str):
    """Вспомогательный поиск разбора по коду валюты."""
    return next(item for item in analyzer.analyze() if item.code == code)


def test_computes_delta_and_pct(sample_snapshot: RatesSnapshot) -> None:
    """USD 90 -> 100 даёт +10 абсолютной и ~+11.11% относительной дельты."""
    analyzer = RateAnalyzer(sample_snapshot)
    usd = _analysis_by_code(analyzer, "USD")

    assert usd.delta_abs == pytest.approx(10.0)
    assert usd.delta_pct == pytest.approx(11.1111, rel=1e-3)


def test_direction_classification(sample_snapshot: RatesSnapshot) -> None:
    """Направление изменения классифицируется как up/down/flat."""
    analyzer = RateAnalyzer(sample_snapshot)

    assert _analysis_by_code(analyzer, "USD").direction == "up"
    assert _analysis_by_code(analyzer, "EUR").direction == "down"
    assert _analysis_by_code(analyzer, "JPY").direction == "flat"


def test_top_movers_sorted_by_abs_pct(sample_snapshot: RatesSnapshot) -> None:
    """top_movers отсортирован по убыванию модуля процентного изменения."""
    analyzer = RateAnalyzer(sample_snapshot)
    movers = analyzer.top_movers(2)

    assert len(movers) == 2
    assert movers[0].code == "USD"  # |+11.11%| — наибольшее
    assert abs(movers[0].delta_pct) >= abs(movers[1].delta_pct)


def test_summary_aggregates(sample_snapshot: RatesSnapshot) -> None:
    """Сводка содержит корректные агрегаты и экстремумы."""
    summary = RateAnalyzer(sample_snapshot).summary()

    assert summary.total_currencies == 3
    assert summary.strongest.code == "USD"  # сильнее всего укрепился
    assert summary.weakest.code == "EUR"  # сильнее всего ослаб
    assert summary.average_abs_pct > 0


def test_zero_previous_does_not_crash() -> None:
    """Валюта с previous = 0 не приводит к делению на ноль."""
    snapshot = RatesSnapshot(
        date=__import__("datetime").datetime(2024, 1, 10),
        previous_date=__import__("datetime").datetime(2024, 1, 9),
        currencies=(
            Currency(code="XXX", name="Тест", nominal=1, value=5.0, previous=0.0),
        ),
    )

    analysis = RateAnalyzer(snapshot).analyze()[0]

    assert analysis.delta_pct == 0.0
    assert analysis.delta_abs == pytest.approx(5.0)


def test_empty_snapshot_summary_raises() -> None:
    """Пустой снимок не позволяет построить сводку — явная ошибка."""
    snapshot = RatesSnapshot(
        date=__import__("datetime").datetime(2024, 1, 10),
        previous_date=__import__("datetime").datetime(2024, 1, 9),
        currencies=(),
    )

    with pytest.raises(ValueError):
        RateAnalyzer(snapshot).summary()
