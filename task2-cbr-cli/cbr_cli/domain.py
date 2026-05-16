# FILE: task2-cbr-cli/cbr_cli/domain.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Неизменяемые доменные модели курсов валют и разбор сырого ответа API ЦБ РФ.
#   SCOPE: Currency, RatesSnapshot, RateAnalysis; классовый парсер RatesSnapshot.from_api_payload.
#   DEPENDS: M-T2-ERRORS
#   LINKS: M-T2-DOMAIN
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   Currency - frozen-модель курса одной валюты (code, name, nominal, value, previous)
#   RateAnalysis - frozen-модель результата аналитического разбора валюты
#   RatesSnapshot - frozen-модель снимка курсов на дату; парсер from_api_payload
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация доменных моделей и парсера ответа API.
# END_CHANGE_SUMMARY
"""Доменные модели курсов валют ЦБ РФ для CLI-аналитика."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cbr_cli.errors import CbrResponseError


@dataclass(frozen=True, slots=True)
class Currency:
    """Курс одной валюты из снимка ЦБ РФ.

    ``value`` — стоимость ``nominal`` единиц валюты в рублях. ``previous`` —
    та же стоимость на предыдущую дату публикации.
    """

    code: str
    name: str
    nominal: int
    value: float
    previous: float

    @property
    def rate_per_unit(self) -> float:
        """Курс одной единицы валюты в рублях (с поправкой на номинал)."""
        return self.value / self.nominal


@dataclass(frozen=True, slots=True)
class RateAnalysis:
    """Результат аналитического разбора одной валюты (производные значения)."""

    code: str
    name: str
    nominal: int
    value: float
    previous: float
    delta_abs: float
    delta_pct: float
    direction: str  # "up" | "down" | "flat"


@dataclass(frozen=True, slots=True)
class RatesSnapshot:
    """Снимок курсов валют на конкретную дату публикации ЦБ РФ."""

    date: datetime
    previous_date: datetime
    currencies: tuple[Currency, ...]

    def __iter__(self) -> Iterator[Currency]:
        return iter(self.currencies)

    def __len__(self) -> int:
        return len(self.currencies)

    # START_CONTRACT: from_api_payload
    #   PURPOSE: Разобрать и провалидировать сырой JSON-ответ API ЦБ РФ в RatesSnapshot.
    #   INPUTS: { payload: Any - десериализованное тело ответа (ожидается dict) }
    #   OUTPUTS: { RatesSnapshot - валидированный снимок курсов }
    #   SIDE_EFFECTS: none
    #   LINKS: M-T2-DOMAIN, M-T2-ERRORS
    # END_CONTRACT: from_api_payload
    @classmethod
    def from_api_payload(cls, payload: Any) -> "RatesSnapshot":
        """Построить снимок из тела ответа cbr-xml-daily.ru.

        Любое отклонение от ожидаемой структуры приводит к
        :class:`CbrResponseError` — вызывающий код получает единый понятный сбой
        вместо случайного ``KeyError`` / ``TypeError`` где-то в недрах.
        """
        # START_BLOCK_VALIDATE_ROOT
        if not isinstance(payload, dict):
            raise CbrResponseError(
                f"Ожидался JSON-объект, получен {type(payload).__name__}"
            )
        valute = payload.get("Valute")
        if not isinstance(valute, dict) or not valute:
            raise CbrResponseError("В ответе API отсутствует непустой объект 'Valute'")
        # END_BLOCK_VALIDATE_ROOT

        # START_BLOCK_PARSE_DATES
        date = cls._parse_date(payload.get("Date"), "Date")
        previous_date = cls._parse_date(payload.get("PreviousDate"), "PreviousDate")
        # END_BLOCK_PARSE_DATES

        # START_BLOCK_PARSE_CURRENCIES
        currencies = tuple(
            cls._parse_currency(code, raw) for code, raw in valute.items()
        )
        # END_BLOCK_PARSE_CURRENCIES
        return cls(date=date, previous_date=previous_date, currencies=currencies)

    @staticmethod
    def _parse_date(raw: Any, field: str) -> datetime:
        """Разобрать ISO-дату из ответа API, иначе бросить CbrResponseError."""
        if not isinstance(raw, str):
            raise CbrResponseError(f"Поле '{field}' отсутствует или не является строкой")
        try:
            return datetime.fromisoformat(raw)
        except ValueError as exc:
            raise CbrResponseError(f"Поле '{field}' содержит некорректную дату: {raw!r}") from exc

    @staticmethod
    def _parse_currency(code: Any, raw: Any) -> Currency:
        """Разобрать один элемент объекта 'Valute' в модель Currency."""
        if not isinstance(raw, dict):
            raise CbrResponseError(f"Запись валюты {code!r} не является объектом")
        try:
            return Currency(
                code=str(raw["CharCode"]),
                name=str(raw["Name"]),
                nominal=int(raw["Nominal"]),
                value=float(raw["Value"]),
                previous=float(raw["Previous"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CbrResponseError(
                f"Запись валюты {code!r} имеет некорректную структуру: {exc}"
            ) from exc
