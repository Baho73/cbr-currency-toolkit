# FILE: task2-cbr-cli/tests/unit/test_domain.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки доменных моделей и парсера ответа API (M-T2-DOMAIN).
#   SCOPE: Парсинг валидного payload, поведение rate_per_unit, отказ на битой структуре.
#   DEPENDS: M-T2-DOMAIN, M-T2-ERRORS
#   LINKS: V-M-T2-DOMAIN
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_parses_valid_payload - валидный ответ разбирается в RatesSnapshot
#   test_rate_per_unit_accounts_for_nominal - rate_per_unit делит на номинал
#   test_rejects_* - битые структуры дают CbrResponseError
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация.
# END_CHANGE_SUMMARY
"""Тесты доменных моделей CLI-аналитика."""

from __future__ import annotations

import pytest

from cbr_cli.domain import Currency, RatesSnapshot
from cbr_cli.errors import CbrResponseError


def test_parses_valid_payload(sample_payload: dict) -> None:
    """Валидное тело ответа разбирается в снимок с верным числом валют."""
    snapshot = RatesSnapshot.from_api_payload(sample_payload)

    assert len(snapshot) == 3
    codes = {currency.code for currency in snapshot}
    assert codes == {"USD", "EUR", "JPY"}


def test_rate_per_unit_accounts_for_nominal() -> None:
    """rate_per_unit учитывает номинал: 60 руб за 100 иен -> 0.6 руб за иену."""
    jpy = Currency(code="JPY", name="Иена", nominal=100, value=60.0, previous=60.0)

    assert jpy.rate_per_unit == pytest.approx(0.6)


def test_currency_is_immutable() -> None:
    """Currency неизменяем — снимок курсов нельзя случайно мутировать."""
    usd = Currency(code="USD", name="Доллар", nominal=1, value=100.0, previous=90.0)

    with pytest.raises(AttributeError):
        usd.value = 1.0  # type: ignore[misc]


def test_rejects_non_dict_payload() -> None:
    """Не-объект на входе парсера приводит к CbrResponseError."""
    with pytest.raises(CbrResponseError):
        RatesSnapshot.from_api_payload(["not", "a", "dict"])


def test_rejects_payload_without_valute() -> None:
    """Отсутствие ключа 'Valute' приводит к CbrResponseError."""
    with pytest.raises(CbrResponseError):
        RatesSnapshot.from_api_payload({"Date": "2024-01-10T11:30:00+03:00"})


def test_rejects_malformed_currency(sample_payload: dict) -> None:
    """Запись валюты без обязательного поля приводит к CbrResponseError."""
    del sample_payload["Valute"]["USD"]["Value"]

    with pytest.raises(CbrResponseError):
        RatesSnapshot.from_api_payload(sample_payload)


def test_rejects_bad_date(sample_payload: dict) -> None:
    """Некорректная дата в ответе приводит к CbrResponseError."""
    sample_payload["Date"] = "не-дата"

    with pytest.raises(CbrResponseError):
        RatesSnapshot.from_api_payload(sample_payload)
