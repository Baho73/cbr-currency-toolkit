# FILE: task1-currency-web/app/schemas.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Pydantic-схемы запросов и ответов REST API конвертера валют.
#   SCOPE: ConvertRequest, ConvertResponse, RateItem, RatesResponse с валидацией ввода.
#   DEPENDS: none
#   LINKS: M-T1-SCHEMAS
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ConvertRequest - тело запроса конвертации (amount > 0, коды валют)
#   ConvertResponse - результат конвертации
#   RateItem - одна валюта в ответе списка курсов
#   RatesResponse - снимок курсов: дата и список RateItem
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация схем API.
# END_CHANGE_SUMMARY
"""Схемы запросов и ответов REST API веб-конвертера."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# Код валюты — ровно 3 буквы; нормализуется к верхнему регистру на входе.
CurrencyCode = Annotated[
    str,
    StringConstraints(min_length=3, max_length=3, to_upper=True, pattern=r"^[A-Za-z]{3}$"),
]


class ConvertRequest(BaseModel):
    """Тело запроса конвертации суммы между двумя валютами."""

    amount: float = Field(gt=0, description="Сумма к конвертации, должна быть положительной.")
    from_code: CurrencyCode = Field(description="Код исходной валюты (ISO, 3 буквы).")
    to_code: CurrencyCode = Field(description="Код целевой валюты (ISO, 3 буквы).")


class ConvertResponse(BaseModel):
    """Результат конвертации суммы."""

    amount: float = Field(description="Исходная сумма.")
    from_code: str = Field(description="Код исходной валюты.")
    to_code: str = Field(description="Код целевой валюты.")
    result: float = Field(description="Результат конвертации.")
    rate: float = Field(description="Эффективный курс: единица исходной валюты в целевой.")
    snapshot_date: str = Field(description="Дата снимка курсов ЦБ РФ.")


class RateItem(BaseModel):
    """Одна валюта в ответе со списком курсов."""

    code: str
    name: str
    nominal: int
    value: float = Field(description="Стоимость nominal единиц валюты в рублях.")
    previous: float = Field(description="Та же стоимость на предыдущую дату.")
    delta_abs: float = Field(description="Абсолютное суточное изменение курса.")
    delta_pct: float = Field(description="Процентное суточное изменение курса.")


class RatesResponse(BaseModel):
    """Снимок курсов валют: метаданные и список валют."""

    date: str
    previous_date: str
    count: int
    rates: list[RateItem]
