# FILE: task2-cbr-cli/tests/conftest.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Общие фикстуры тестов: детерминированный образец ответа API ЦБ РФ.
#   SCOPE: Фикстуры sample_payload и sample_snapshot для модульных и end-to-end тестов.
#   DEPENDS: M-T2-DOMAIN
#   LINKS: V-M-T2-DOMAIN, V-M-T2-CBR-CLIENT, V-M-T2-ANALYTICS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   sample_payload - сырое тело ответа API (dict) с предсказуемыми курсами
#   sample_snapshot - разобранный RatesSnapshot на основе sample_payload
# END_MODULE_MAP
"""Общие тестовые фикстуры CLI-аналитика."""

from __future__ import annotations

import pytest

from cbr_cli.domain import RatesSnapshot

# Образец построен так, чтобы дельты считались устно:
#   USD: 90 -> 100  (+10, укрепление на ~11.11%)
#   EUR: 100 -> 95  (-5, ослабление на -5%)
#   JPY: nominal 100, 60 -> 60 (без изменений)
_SAMPLE_PAYLOAD: dict = {
    "Date": "2024-01-10T11:30:00+03:00",
    "PreviousDate": "2024-01-09T11:30:00+03:00",
    "Valute": {
        "USD": {
            "CharCode": "USD",
            "Name": "Доллар США",
            "Nominal": 1,
            "Value": 100.0,
            "Previous": 90.0,
        },
        "EUR": {
            "CharCode": "EUR",
            "Name": "Евро",
            "Nominal": 1,
            "Value": 95.0,
            "Previous": 100.0,
        },
        "JPY": {
            "CharCode": "JPY",
            "Name": "Японских иен",
            "Nominal": 100,
            "Value": 60.0,
            "Previous": 60.0,
        },
    },
}


@pytest.fixture
def sample_payload() -> dict:
    """Свежая копия образца сырого ответа API на каждый тест."""
    import copy

    return copy.deepcopy(_SAMPLE_PAYLOAD)


@pytest.fixture
def sample_snapshot(sample_payload: dict) -> RatesSnapshot:
    """Разобранный снимок курсов на основе образца ответа."""
    return RatesSnapshot.from_api_payload(sample_payload)
