# FILE: task1-currency-web/tests/unit/test_config.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки конфигурации веб-приложения (M-T1-CONFIG).
#   SCOPE: Дефолты, переопределение через окружение, кэширование get_settings.
#   DEPENDS: M-T1-CONFIG
#   LINKS: V-M-T1-CONFIG
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_defaults - применяются дефолтные значения
#   test_env_overrides - переменные окружения переопределяют дефолты
#   test_get_settings_is_cached - get_settings возвращает один и тот же объект
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация.
# END_CHANGE_SUMMARY
"""Тесты конфигурации веб-конвертера."""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings


def test_defaults() -> None:
    """Без переменных окружения применяются дефолтные значения."""
    settings = Settings()

    assert settings.cbr_api_url.startswith("https://")
    assert settings.retry_attempts >= 1
    assert settings.cache_ttl_seconds >= 0


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Переменные окружения с префиксом APP_ переопределяют дефолты."""
    monkeypatch.setenv("APP_HTTP_TIMEOUT", "30")
    monkeypatch.setenv("APP_CACHE_TTL_SECONDS", "120")

    settings = Settings()

    assert settings.http_timeout == 30.0
    assert settings.cache_ttl_seconds == 120


def test_get_settings_is_cached() -> None:
    """get_settings возвращает закэшированный синглтон."""
    assert get_settings() is get_settings()
