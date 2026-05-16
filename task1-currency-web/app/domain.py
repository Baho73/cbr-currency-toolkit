# FILE: task1-currency-web/app/domain.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Неизменяемые доменные модели курсов валют и разбор ответа API ЦБ РФ.
#   SCOPE: Currency, RatesSnapshot; синтетический рубль; парсер from_api_payload; поиск get.
#   DEPENDS: M-T1-ERRORS
#   LINKS: M-T1-DOMAIN
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   RUB_CODE - код опорной валюты (рубль)
#   Currency - frozen-модель курса валюты; свойства rate_per_unit, delta_abs, delta_pct
#   RatesSnapshot - frozen-модель снимка курсов; парсер from_api_payload; поиск get
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация доменных моделей и парсера.
# END_CHANGE_SUMMARY
"""Доменные модели курсов валют ЦБ РФ для веб-конвертера."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.errors import CbrResponseError, UnknownCurrencyError

_FLAT_EPSILON = 1e-9

# Код рубля и его синтетическая запись: рубль не приходит из API, но нужен
# как опорная валюта для кросс-конвертации (его rate_per_unit == 1.0).
RUB_CODE = "RUB"


@dataclass(frozen=True, slots=True)
class Currency:
    """Курс одной валюты из снимка ЦБ РФ.

    ``value`` — стоимость ``nominal`` единиц валюты в рублях.
    """

    code: str
    name: str
    nominal: int
    value: float
    previous: float

    @property
    def rate_per_unit(self) -> float:
        """Стоимость одной единицы валюты в рублях (с поправкой на номинал)."""
        return self.value / self.nominal

    @property
    def delta_abs(self) -> float:
        """Абсолютное изменение курса за сутки."""
        return self.value - self.previous

    @property
    def delta_pct(self) -> float:
        """Процентное изменение курса за сутки (0.0 при нулевом previous)."""
        if abs(self.previous) <= _FLAT_EPSILON:
            return 0.0
        return self.delta_abs / self.previous * 100.0


def _synthetic_rub() -> Currency:
    """Создать синтетическую запись рубля как опорной валюты конвертации."""
    return Currency(code=RUB_CODE, name="Российский рубль", nominal=1, value=1.0, previous=1.0)


@dataclass(frozen=True, slots=True)
class RatesSnapshot:
    """Снимок курсов валют на дату публикации ЦБ РФ (включая синтетический рубль)."""

    date: datetime
    previous_date: datetime
    _by_code: dict[str, Currency]

    def __iter__(self) -> Iterator[Currency]:
        return iter(self._by_code.values())

    def __len__(self) -> int:
        return len(self._by_code)

    # START_CONTRACT: get
    #   PURPOSE: Найти валюту в снимке по коду (без учёта регистра).
    #   INPUTS: { code: str - код валюты (ISO) }
    #   OUTPUTS: { Currency - запись валюты }
    #   SIDE_EFFECTS: none
    #   LINKS: M-T1-DOMAIN, M-T1-ERRORS
    # END_CONTRACT: get
    def get(self, code: str) -> Currency:
        """Вернуть валюту по коду или бросить :class:`UnknownCurrencyError`."""
        # START_BLOCK_LOOKUP_CURRENCY
        currency = self._by_code.get(code.upper())
        if currency is None:
            raise UnknownCurrencyError(f"Валюта {code!r} отсутствует в снимке курсов")
        return currency
        # END_BLOCK_LOOKUP_CURRENCY

    @property
    def currencies(self) -> tuple[Currency, ...]:
        """Все валюты снимка, отсортированные по коду."""
        return tuple(sorted(self._by_code.values(), key=lambda c: c.code))

    # START_CONTRACT: from_api_payload
    #   PURPOSE: Разобрать и провалидировать сырой JSON-ответ API ЦБ РФ в RatesSnapshot.
    #   INPUTS: { payload: Any - десериализованное тело ответа (ожидается dict) }
    #   OUTPUTS: { RatesSnapshot - снимок курсов с синтетическим рублём }
    #   SIDE_EFFECTS: none
    #   LINKS: M-T1-DOMAIN, M-T1-ERRORS
    # END_CONTRACT: from_api_payload
    @classmethod
    def from_api_payload(cls, payload: Any) -> "RatesSnapshot":
        """Построить снимок из тела ответа cbr-xml-daily.ru.

        Любое отклонение от ожидаемой структуры приводит к :class:`CbrResponseError`.
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

        date = cls._parse_date(payload.get("Date"), "Date")
        previous_date = cls._parse_date(payload.get("PreviousDate"), "PreviousDate")

        by_code: dict[str, Currency] = {RUB_CODE: _synthetic_rub()}
        for code, raw in valute.items():
            currency = cls._parse_currency(code, raw)
            by_code[currency.code.upper()] = currency
        return cls(date=date, previous_date=previous_date, _by_code=by_code)

    @staticmethod
    def _parse_date(raw: Any, field: str) -> datetime:
        """Разобрать ISO-дату из ответа API, иначе бросить CbrResponseError."""
        if not isinstance(raw, str):
            raise CbrResponseError(f"Поле '{field}' отсутствует или не является строкой")
        try:
            return datetime.fromisoformat(raw)
        except ValueError as exc:
            raise CbrResponseError(
                f"Поле '{field}' содержит некорректную дату: {raw!r}"
            ) from exc

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
