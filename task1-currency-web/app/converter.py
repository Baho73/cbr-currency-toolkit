# FILE: task1-currency-web/app/converter.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Кросс-конвертация суммы из любой валюты в любую через рубль с учётом номинала.
#   SCOPE: Класс CurrencyConverter и тип ConversionResult.
#   DEPENDS: M-T1-DOMAIN, M-T1-ERRORS
#   LINKS: M-T1-CONVERTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ConversionResult - результат конвертации (сумма, коды, результат, эффективный курс)
#   CurrencyConverter - конвертер: convert(amount, from_code, to_code, snapshot)
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация конвертера валют.
# END_CHANGE_SUMMARY
"""Кросс-конвертация валют по курсам ЦБ РФ через рубль."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from app.domain import RatesSnapshot
from app.errors import ConversionError

_logger = logging.getLogger(__name__)

# Точность округления: результат — до копеек×100, курс — до 6 знаков.
_RESULT_QUANT = Decimal("0.0001")
_RATE_QUANT = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """Результат конвертации суммы между валютами."""

    amount: float
    from_code: str
    to_code: str
    result: float
    rate: float  # эффективный курс: 1 единица исходной валюты в целевой


class CurrencyConverter:
    """Конвертирует суммы между валютами снимка курсов через рубль."""

    # START_CONTRACT: convert
    #   PURPOSE: Пересчитать сумму из исходной валюты в целевую по кросс-курсу через рубль.
    #   INPUTS: { amount: float - сумма > 0, from_code: str, to_code: str, snapshot: RatesSnapshot }
    #   OUTPUTS: { ConversionResult - результат с эффективным курсом }
    #   SIDE_EFFECTS: none
    #   LINKS: M-T1-CONVERTER, M-T1-DOMAIN
    # END_CONTRACT: convert
    def convert(
        self,
        amount: float,
        from_code: str,
        to_code: str,
        snapshot: RatesSnapshot,
    ) -> ConversionResult:
        """Сконвертировать ``amount`` из ``from_code`` в ``to_code``.

        :raises ConversionError: сумма неположительна.
        :raises UnknownCurrencyError: одна из валют отсутствует в снимке.
        """
        if amount <= 0:
            raise ConversionError("Сумма конвертации должна быть положительной")

        # snapshot.get бросает UnknownCurrencyError для неизвестных кодов.
        from_currency = snapshot.get(from_code)
        to_currency = snapshot.get(to_code)

        # START_BLOCK_CROSS_RATE
        # Decimal — денежная арифметика без накопления ошибок float.
        # rate_per_unit — стоимость единицы валюты в рублях. Кросс-курс получаем
        # делением: (₽ за единицу from) / (₽ за единицу to).
        from_rate = Decimal(str(from_currency.rate_per_unit))
        to_rate = Decimal(str(to_currency.rate_per_unit))
        amount_dec = Decimal(str(amount))

        effective_rate = from_rate / to_rate
        result = amount_dec * effective_rate
        # END_BLOCK_CROSS_RATE

        _logger.info(
            "[CurrencyConverter][convert][BLOCK_CROSS_RATE] %s %s -> %s, курс %s",
            amount, from_currency.code, to_currency.code, effective_rate,
        )
        return ConversionResult(
            amount=amount,
            from_code=from_currency.code,
            to_code=to_currency.code,
            result=float(result.quantize(_RESULT_QUANT)),
            rate=float(effective_rate.quantize(_RATE_QUANT)),
        )
