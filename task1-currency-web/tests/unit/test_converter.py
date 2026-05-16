# FILE: task1-currency-web/tests/unit/test_converter.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки конвертера валют (M-T1-CONVERTER).
#   SCOPE: Конвертация через рубль, обратимость, кросс-курс, номинал > 1, ошибки.
#   DEPENDS: M-T1-CONVERTER, M-T1-DOMAIN, M-T1-ERRORS
#   LINKS: V-M-T1-CONVERTER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_rub_to_usd / test_usd_to_rub - конвертация с рублём
#   test_round_trip_is_stable - RUB->USD->RUB возвращает исходную сумму
#   test_cross_rate_usd_to_eur - кросс-курс между двумя валютами
#   test_currency_with_nominal - валюта с номиналом > 1 (JPY)
#   test_same_currency / test_unknown_currency / test_non_positive_amount
# END_MODULE_MAP
"""Тесты конвертера валют."""

from __future__ import annotations

import pytest

from app.converter import CurrencyConverter
from app.domain import RatesSnapshot
from app.errors import ConversionError, UnknownCurrencyError

# Курсы образца: USD = 100 ₽, EUR = 110 ₽, JPY = 0.6 ₽ за единицу.
_CONVERTER = CurrencyConverter()


def test_rub_to_usd(sample_snapshot: RatesSnapshot) -> None:
    """1000 ₽ при курсе 100 ₽/USD дают 10 USD."""
    result = _CONVERTER.convert(1000.0, "RUB", "USD", sample_snapshot)

    assert result.result == pytest.approx(10.0)


def test_usd_to_rub(sample_snapshot: RatesSnapshot) -> None:
    """10 USD при курсе 100 ₽/USD дают 1000 ₽."""
    result = _CONVERTER.convert(10.0, "USD", "RUB", sample_snapshot)

    assert result.result == pytest.approx(1000.0)


def test_round_trip_is_stable(sample_snapshot: RatesSnapshot) -> None:
    """Конвертация RUB->USD->RUB возвращает исходную сумму."""
    to_usd = _CONVERTER.convert(5000.0, "RUB", "USD", sample_snapshot)
    back = _CONVERTER.convert(to_usd.result, "USD", "RUB", sample_snapshot)

    assert back.result == pytest.approx(5000.0, rel=1e-6)


def test_cross_rate_usd_to_eur(sample_snapshot: RatesSnapshot) -> None:
    """Кросс-курс USD->EUR равен 100/110; 110 USD дают 100 EUR."""
    result = _CONVERTER.convert(110.0, "USD", "EUR", sample_snapshot)

    assert result.result == pytest.approx(100.0)
    assert result.rate == pytest.approx(100 / 110, rel=1e-5)


def test_currency_with_nominal(sample_snapshot: RatesSnapshot) -> None:
    """JPY с номиналом 100 (0.6 ₽/иена): 600 ₽ дают 1000 иен."""
    result = _CONVERTER.convert(600.0, "RUB", "JPY", sample_snapshot)

    assert result.result == pytest.approx(1000.0)


def test_same_currency_returns_same_amount(sample_snapshot: RatesSnapshot) -> None:
    """Конвертация валюты в саму себя возвращает ту же сумму."""
    result = _CONVERTER.convert(777.0, "EUR", "EUR", sample_snapshot)

    assert result.result == pytest.approx(777.0)
    assert result.rate == pytest.approx(1.0)


def test_unknown_currency_raises(sample_snapshot: RatesSnapshot) -> None:
    """Неизвестная валюта приводит к UnknownCurrencyError."""
    with pytest.raises(UnknownCurrencyError):
        _CONVERTER.convert(100.0, "USD", "XXX", sample_snapshot)


def test_non_positive_amount_raises(sample_snapshot: RatesSnapshot) -> None:
    """Неположительная сумma приводит к ConversionError."""
    with pytest.raises(ConversionError):
        _CONVERTER.convert(0.0, "USD", "RUB", sample_snapshot)
