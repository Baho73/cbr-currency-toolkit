# FILE: task2-cbr-cli/cbr_cli/errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Иерархия исключений CLI-аналитика для управляемой обработки ошибок и корректных exit codes.
#   SCOPE: Определение базового CbrError и его подклассов; маппинг подклассов на коды возврата.
#   DEPENDS: none
#   LINKS: M-T2-ERRORS
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CbrError - базовое исключение интеграции с API ЦБ РФ
#   CbrUnavailableError - API недоступен после исчерпания retry
#   CbrResponseError - ответ получен, но формат некорректен
#   EXIT_CODES - соответствие классов исключений кодам возврата CLI
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация иерархии исключений.
# END_CHANGE_SUMMARY
"""Иерархия исключений CLI-аналитика курсов валют."""

from __future__ import annotations


class CbrError(Exception):
    """Базовое исключение для любых сбоев интеграции с API ЦБ РФ.

    Перехват именно этого класса гарантирует, что прикладной код отлавливает
    все ожидаемые ошибки интеграции, не пряча при этом непредвиденные баги.
    """


class CbrUnavailableError(CbrError):
    """API недоступен: сетевая ошибка, таймаут или 5xx после всех retry."""


class CbrResponseError(CbrError):
    """Ответ получен, но непригоден к разбору: не-JSON или нарушена структура."""


# Соответствие исключений кодам возврата процесса. Базовый CbrError ловит
# подклассы по принципу «первое совпадение», поэтому порядок здесь не важен —
# CLI выбирает код по конкретному типу пойманного исключения.
EXIT_CODES: dict[type[CbrError], int] = {
    CbrUnavailableError: 1,
    CbrResponseError: 2,
}
