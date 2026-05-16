# FILE: task2-cbr-cli/cbr_cli/analytics.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Расчёт производных значений по курсам: суточная дельта, % изменения, сортировка, агрегаты.
#   SCOPE: Класс RateAnalyzer и тип AnalysisSummary; превращение RatesSnapshot в аналитические выводы.
#   DEPENDS: M-T2-DOMAIN
#   LINKS: M-T2-ANALYTICS
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AnalysisSummary - агрегированная сводка по всему снимку курсов
#   RateAnalyzer - анализатор: analyze(), top_movers(), summary()
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация аналитики курсов.
# END_CHANGE_SUMMARY
"""Аналитика курсов валют ЦБ РФ: дельты, проценты, топ движений, агрегаты."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cbr_cli.domain import Currency, RateAnalysis, RatesSnapshot

_logger = logging.getLogger(__name__)

# Порог, ниже которого изменение считается отсутствующим (защита от шума float).
_FLAT_EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class AnalysisSummary:
    """Агрегированная сводка по снимку курсов."""

    total_currencies: int
    average_abs_pct: float
    strongest: RateAnalysis  # сильнее всего укрепилась к рублю (макс. delta_pct)
    weakest: RateAnalysis  # сильнее всего ослабла к рублю (мин. delta_pct)


class RateAnalyzer:
    """Считает производные значения по снимку курсов валют."""

    def __init__(self, snapshot: RatesSnapshot) -> None:
        self._snapshot = snapshot
        self._analyses: list[RateAnalysis] | None = None

    # START_CONTRACT: analyze
    #   PURPOSE: Посчитать суточную дельту и % изменения по каждой валюте снимка.
    #   INPUTS: none (снимок передан в конструкторе)
    #   OUTPUTS: { list[RateAnalysis] - разбор по каждой валюте }
    #   SIDE_EFFECTS: кэширование результата внутри экземпляра
    #   LINKS: M-T2-ANALYTICS, M-T2-DOMAIN
    # END_CONTRACT: analyze
    def analyze(self) -> list[RateAnalysis]:
        """Вернуть аналитический разбор каждой валюты снимка."""
        if self._analyses is not None:
            return self._analyses

        # START_BLOCK_COMPUTE_DELTAS
        analyses = [self._analyze_one(currency) for currency in self._snapshot]
        _logger.info(
            "[RateAnalyzer][analyze][BLOCK_COMPUTE_DELTAS] разобрано валют: %d",
            len(analyses),
        )
        # END_BLOCK_COMPUTE_DELTAS
        self._analyses = analyses
        return analyses

    def top_movers(self, count: int) -> list[RateAnalysis]:
        """Вернуть ``count`` валют с наибольшим по модулю изменением курса."""
        ranked = sorted(
            self.analyze(), key=lambda item: abs(item.delta_pct), reverse=True
        )
        return ranked[: max(count, 0)]

    def summary(self) -> AnalysisSummary:
        """Посчитать агрегированную сводку по всему снимку."""
        analyses = self.analyze()
        if not analyses:
            raise ValueError("Снимок курсов пуст — сводка не может быть построена")

        average_abs_pct = sum(abs(item.delta_pct) for item in analyses) / len(analyses)
        strongest = max(analyses, key=lambda item: item.delta_pct)
        weakest = min(analyses, key=lambda item: item.delta_pct)
        return AnalysisSummary(
            total_currencies=len(analyses),
            average_abs_pct=average_abs_pct,
            strongest=strongest,
            weakest=weakest,
        )

    @staticmethod
    def _analyze_one(currency: Currency) -> RateAnalysis:
        """Посчитать производные значения для одной валюты."""
        delta_abs = currency.value - currency.previous
        # previous может быть нулевым/отсутствующим в крайних случаях — не делим на 0.
        if abs(currency.previous) > _FLAT_EPSILON:
            delta_pct = delta_abs / currency.previous * 100.0
        else:
            delta_pct = 0.0

        if delta_abs > _FLAT_EPSILON:
            direction = "up"
        elif delta_abs < -_FLAT_EPSILON:
            direction = "down"
        else:
            direction = "flat"

        return RateAnalysis(
            code=currency.code,
            name=currency.name,
            nominal=currency.nominal,
            value=currency.value,
            previous=currency.previous,
            delta_abs=delta_abs,
            delta_pct=delta_pct,
            direction=direction,
        )
