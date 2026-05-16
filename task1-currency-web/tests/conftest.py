# FILE: task1-currency-web/tests/conftest.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Общие тестовые фикстуры: образец ответа API ЦБ РФ и разобранный снимок.
#   SCOPE: Фикстуры sample_payload и sample_snapshot.
#   DEPENDS: M-T1-DOMAIN
#   LINKS: V-M-T1-DOMAIN, V-M-T1-CBR-CLIENT, V-M-T1-CONVERTER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   sample_payload - сырое тело ответа API с предсказуемыми курсами
#   sample_snapshot - разобранный RatesSnapshot
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация.
# END_CHANGE_SUMMARY
"""Общие тестовые фикстуры веб-конвертера."""

from __future__ import annotations

import copy

import pytest

from app.domain import RatesSnapshot

# Предсказуемые курсы для устной проверки конвертации:
#   USD: 1 ед. = 100 ₽
#   EUR: 1 ед. = 110 ₽
#   JPY: 100 ед. = 60 ₽  ->  1 ед. = 0.6 ₽  (валюта с номиналом > 1)
_SAMPLE_PAYLOAD: dict = {
    "Date": "2024-01-10T11:30:00+03:00",
    "PreviousDate": "2024-01-09T11:30:00+03:00",
    "Valute": {
        "USD": {"CharCode": "USD", "Name": "Доллар США", "Nominal": 1,
                "Value": 100.0, "Previous": 90.0},
        "EUR": {"CharCode": "EUR", "Name": "Евро", "Nominal": 1,
                "Value": 110.0, "Previous": 115.0},
        "JPY": {"CharCode": "JPY", "Name": "Японских иен", "Nominal": 100,
                "Value": 60.0, "Previous": 60.0},
    },
}


@pytest.fixture
def sample_payload() -> dict:
    """Свежая копия образца сырого ответа API."""
    return copy.deepcopy(_SAMPLE_PAYLOAD)


@pytest.fixture
def sample_snapshot(sample_payload: dict) -> RatesSnapshot:
    """Разобранный снимок курсов на основе образца."""
    return RatesSnapshot.from_api_payload(sample_payload)
