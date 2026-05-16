# FILE: task2-cbr-cli/tests/unit/test_config.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки модуля конфигурации CLI (M-T2-CONFIG).
#   SCOPE: Дефолты без окружения, переопределение через env, устойчивость к мусорным значениям.
#   DEPENDS: M-T2-CONFIG
#   LINKS: V-M-T2-CONFIG
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_defaults_without_env - дефолты применяются без переменных окружения
#   test_env_overrides - переменные окружения переопределяют дефолты
#   test_invalid_env_falls_back - мусорные значения откатываются к дефолтам
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация.
# END_CHANGE_SUMMARY
"""Тесты конфигурации CLI-аналитика."""

from cbr_cli.config import (
    DEFAULT_API_URL,
    DEFAULT_RETRY_ATTEMPTS,
    Settings,
    load_settings,
)


def test_defaults_without_env() -> None:
    """Без переменных окружения возвращаются дефолтные значения."""
    settings = load_settings(env={})

    assert isinstance(settings, Settings)
    assert settings.cbr_api_url == DEFAULT_API_URL
    assert settings.retry_attempts == DEFAULT_RETRY_ATTEMPTS
    assert settings.http_timeout > 0


def test_env_overrides() -> None:
    """Переменные окружения переопределяют дефолты."""
    settings = load_settings(
        env={
            "CBR_API_URL": "https://example.test/rates.json",
            "CBR_HTTP_TIMEOUT": "25",
            "CBR_RETRY_ATTEMPTS": "5",
            "CBR_RETRY_BACKOFF": "1.5",
        }
    )

    assert settings.cbr_api_url == "https://example.test/rates.json"
    assert settings.http_timeout == 25.0
    assert settings.retry_attempts == 5
    assert settings.retry_backoff == 1.5


def test_invalid_env_falls_back() -> None:
    """Некорректные значения в окружении не ломают запуск — используется дефолт."""
    settings = load_settings(
        env={"CBR_HTTP_TIMEOUT": "not-a-number", "CBR_RETRY_ATTEMPTS": "-3"}
    )

    assert settings.http_timeout == Settings().http_timeout
    assert settings.retry_attempts == Settings().retry_attempts


def test_settings_is_immutable() -> None:
    """Settings неизменяем — конфигурацию нельзя случайно мутировать в рантайме."""
    settings = load_settings(env={})

    try:
        settings.http_timeout = 1.0  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("Settings должен быть неизменяемым (frozen dataclass)")
