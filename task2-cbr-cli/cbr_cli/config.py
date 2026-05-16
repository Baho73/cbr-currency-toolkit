# FILE: task2-cbr-cli/cbr_cli/config.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Типизированная конфигурация CLI-аналитика курсов валют.
#   SCOPE: Описание модели Settings и её сборка из переменных окружения с безопасными дефолтами.
#   DEPENDS: none
#   LINKS: M-T2-CONFIG
#   ROLE: CONFIG
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DEFAULT_API_URL - дефолтный URL API ЦБ РФ
#   DEFAULT_HTTP_TIMEOUT - дефолтный таймаут HTTP-запроса
#   DEFAULT_RETRY_ATTEMPTS - дефолтное число попыток запроса
#   DEFAULT_RETRY_BACKOFF - дефолтная база экспоненциального backoff
#   Settings - неизменяемая конфигурация (URL API, таймауты, retry)
#   load_settings - сборка Settings из переменных окружения
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация конфигурации CLI.
# END_CHANGE_SUMMARY
"""Конфигурация CLI-аналитика курсов валют ЦБ РФ."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

# Дефолты вынесены в константы модуля, чтобы их можно было переиспользовать в справке CLI.
DEFAULT_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
DEFAULT_HTTP_TIMEOUT = 10.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 0.5


@dataclass(frozen=True, slots=True)
class Settings:
    """Неизменяемая конфигурация запуска CLI-аналитика."""

    cbr_api_url: str = DEFAULT_API_URL
    http_timeout: float = DEFAULT_HTTP_TIMEOUT
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    retry_backoff: float = DEFAULT_RETRY_BACKOFF


# START_CONTRACT: load_settings
#   PURPOSE: Собрать Settings из переменных окружения, опираясь на дефолты при их отсутствии.
#   INPUTS: { env: Mapping[str, str] | None - источник переменных, по умолчанию os.environ }
#   OUTPUTS: { Settings - неизменяемая конфигурация }
#   SIDE_EFFECTS: чтение переменных окружения процесса (когда env не передан)
#   LINKS: M-T2-CONFIG
# END_CONTRACT: load_settings
def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Построить :class:`Settings` из окружения.

    Передача явного ``env`` (а не только чтение ``os.environ``) делает функцию
    детерминированной и удобной для модульного тестирования.
    """
    source: Mapping[str, str] = os.environ if env is None else env

    # START_BLOCK_PARSE_ENV
    # Каждое числовое поле парсится через защищённый helper: некорректное значение
    # из окружения не должно ронять весь запуск — используем дефолт.
    return Settings(
        cbr_api_url=source.get("CBR_API_URL", DEFAULT_API_URL),
        http_timeout=_read_float(source, "CBR_HTTP_TIMEOUT", DEFAULT_HTTP_TIMEOUT),
        retry_attempts=_read_int(source, "CBR_RETRY_ATTEMPTS", DEFAULT_RETRY_ATTEMPTS),
        retry_backoff=_read_float(source, "CBR_RETRY_BACKOFF", DEFAULT_RETRY_BACKOFF),
    )
    # END_BLOCK_PARSE_ENV


def _read_float(source: Mapping[str, str], key: str, default: float) -> float:
    """Прочитать число с плавающей точкой из окружения, вернуть дефолт при ошибке."""
    raw = source.get(key)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _read_int(source: Mapping[str, str], key: str, default: int) -> int:
    """Прочитать целое число из окружения, вернуть дефолт при ошибке."""
    raw = source.get(key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
