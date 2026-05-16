# FILE: task1-currency-web/tests/unit/test_domain.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки доменных моделей и парсера ответа API (M-T1-DOMAIN).
#   SCOPE: rate_per_unit, синтетический рубль, get по коду, отказ на битой структуре.
#   DEPENDS: M-T1-DOMAIN, M-T1-ERRORS
#   LINKS: V-M-T1-DOMAIN
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_parses_and_adds_rub - снимок содержит валюты API плюс синтетический рубль
#   test_rate_per_unit_accounts_for_nominal - rate_per_unit делит на номинал
#   test_get_is_case_insensitive - get не зависит от регистра
#   test_get_unknown_raises - неизвестный код -> UnknownCurrencyError
#   test_rejects_* - битые структуры дают CbrResponseError
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация.
# END_CHANGE_SUMMARY
"""Тесты доменных моделей веб-конвертера."""

from __future__ import annotations

import pytest

from app.domain import RUB_CODE, Currency, RatesSnapshot
from app.errors import CbrResponseError, UnknownCurrencyError


def test_parses_and_adds_rub(sample_snapshot: RatesSnapshot) -> None:
    """Снимок содержит валюты из API и синтетический рубль."""
    assert len(sample_snapshot) == 4  # USD, EUR, JPY + RUB
    rub = sample_snapshot.get(RUB_CODE)
    assert rub.rate_per_unit == 1.0


def test_rate_per_unit_accounts_for_nominal(sample_snapshot: RatesSnapshot) -> None:
    """JPY с номиналом 100: 60 ₽ за 100 иен -> 0.6 ₽ за иену."""
    jpy = sample_snapshot.get("JPY")

    assert jpy.rate_per_unit == pytest.approx(0.6)


def test_delta_properties() -> None:
    """delta_abs и delta_pct считаются от previous."""
    usd = Currency(code="USD", name="Доллар", nominal=1, value=100.0, previous=90.0)

    assert usd.delta_abs == pytest.approx(10.0)
    assert usd.delta_pct == pytest.approx(11.1111, rel=1e-3)


def test_get_is_case_insensitive(sample_snapshot: RatesSnapshot) -> None:
    """Поиск валюты не зависит от регистра кода."""
    assert sample_snapshot.get("usd").code == "USD"


def test_get_unknown_raises(sample_snapshot: RatesSnapshot) -> None:
    """Запрос неизвестной валюты приводит к UnknownCurrencyError."""
    with pytest.raises(UnknownCurrencyError):
        sample_snapshot.get("XXX")


def test_rejects_non_dict_payload() -> None:
    """Не-объект на входе парсера приводит к CbrResponseError."""
    with pytest.raises(CbrResponseError):
        RatesSnapshot.from_api_payload("not a dict")


def test_rejects_payload_without_valute() -> None:
    """Отсутствие ключа 'Valute' приводит к CbrResponseError."""
    with pytest.raises(CbrResponseError):
        RatesSnapshot.from_api_payload({"Date": "2024-01-10T11:30:00+03:00"})


def test_rejects_malformed_currency(sample_payload: dict) -> None:
    """Запись валюты без обязательного поля приводит к CbrResponseError."""
    del sample_payload["Valute"]["USD"]["Value"]

    with pytest.raises(CbrResponseError):
        RatesSnapshot.from_api_payload(sample_payload)
