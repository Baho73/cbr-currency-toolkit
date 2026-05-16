# FILE: task1-currency-web/app/config.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Типизированная конфигурация веб-конвертера из переменных окружения.
#   SCOPE: Модель Settings (pydantic-settings) и кэшированный доступ get_settings.
#   DEPENDS: none
#   LINKS: M-T1-CONFIG
#   ROLE: CONFIG
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   Settings - конфигурация приложения (URL API, таймауты, retry, TTL, host, port)
#   get_settings - кэшированный синглтон Settings
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация конфигурации веб-приложения.
# END_CHANGE_SUMMARY
"""Конфигурация веб-конвертера валют."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Значения читаются из переменных окружения с префиксом ``APP_``."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    cbr_api_url: str = Field(
        default="https://www.cbr-xml-daily.ru/daily_json.js",
        description="URL публичного API курсов валют ЦБ РФ.",
    )
    http_timeout: float = Field(default=10.0, gt=0, description="Таймаут HTTP-запроса, сек.")
    retry_attempts: int = Field(default=3, ge=1, description="Число попыток запроса к API.")
    retry_backoff: float = Field(default=0.5, ge=0, description="Базовая пауза backoff, сек.")
    cache_ttl_seconds: int = Field(
        default=600, ge=0, description="Время жизни кэша курсов, сек (ЦБ обновляет раз в сутки)."
    )
    host: str = Field(default="0.0.0.0", description="Адрес прослушивания сервера.")
    port: int = Field(default=8000, gt=0, le=65535, description="Порт сервера.")


# START_CONTRACT: get_settings
#   PURPOSE: Вернуть кэшированный синглтон конфигурации приложения.
#   INPUTS: none
#   OUTPUTS: { Settings - конфигурация приложения }
#   SIDE_EFFECTS: чтение переменных окружения при первом вызове
#   LINKS: M-T1-CONFIG
# END_CONTRACT: get_settings
@lru_cache
def get_settings() -> Settings:
    """Собрать и закэшировать конфигурацию приложения."""
    return Settings()
