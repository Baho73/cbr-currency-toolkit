# FILE: task1-currency-web/app/errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Иерархия доменных исключений конвертера для управляемой обработки и трансляции в HTTP.
#   SCOPE: Базовые CbrError и ConversionError с подклассами.
#   DEPENDS: none
#   LINKS: M-T1-ERRORS
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CbrError - базовое исключение интеграции с API ЦБ РФ
#   CbrUnavailableError - API недоступен после retry
#   CbrResponseError - некорректный формат ответа API
#   ConversionError - базовое исключение конвертации валют
#   UnknownCurrencyError - запрошена валюта вне снимка курсов
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация иерархии исключений.
# END_CHANGE_SUMMARY
"""Иерархия исключений веб-конвертера валют."""

from __future__ import annotations


class CbrError(Exception):
    """Базовое исключение для сбоев интеграции с API ЦБ РФ."""


class CbrUnavailableError(CbrError):
    """API недоступен: сеть, таймаут или 5xx после всех retry."""


class CbrResponseError(CbrError):
    """Ответ получен, но непригоден к разбору: не-JSON или нарушена структура."""


class ConversionError(Exception):
    """Базовое исключение ошибок конвертации валют."""


class UnknownCurrencyError(ConversionError):
    """Запрошена валюта, отсутствующая в текущем снимке курсов."""
