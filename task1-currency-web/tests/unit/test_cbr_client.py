# FILE: task1-currency-web/tests/unit/test_cbr_client.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки async HTTP-клиента API ЦБ РФ (M-T1-CBR-CLIENT).
#   SCOPE: Успешный разбор, retry на 5xx, восстановление, ошибки формата, таймаут.
#   DEPENDS: M-T1-CBR-CLIENT, M-T1-CONFIG, M-T1-ERRORS
#   LINKS: V-M-T1-CBR-CLIENT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_fetch_parses_valid_response - валидный ответ -> RatesSnapshot
#   test_retries_on_5xx_then_raises - 5xx исчерпывает retry -> CbrUnavailableError
#   test_recovers_after_transient_5xx - восстановление после временного сбоя
#   test_non_json_raises_response_error - не-JSON -> CbrResponseError
#   test_timeout_raises_unavailable - таймаут -> CbrUnavailableError
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация.
# END_CHANGE_SUMMARY
"""Тесты async HTTP-клиента API ЦБ РФ."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.cbr_client import CbrClient
from app.config import Settings
from app.errors import CbrResponseError, CbrUnavailableError

_SETTINGS = Settings(
    cbr_api_url="https://api.test/daily_json.js",
    retry_attempts=3,
    retry_backoff=0.0,
)


@respx.mock
async def test_fetch_parses_valid_response(sample_payload: dict) -> None:
    """Валидный ответ 200 разбирается в снимок курсов (3 валюты + рубль)."""
    respx.get(_SETTINGS.cbr_api_url).mock(
        return_value=httpx.Response(200, json=sample_payload)
    )

    async with httpx.AsyncClient() as http:
        snapshot = await CbrClient(_SETTINGS, http).fetch_rates()

    assert len(snapshot) == 4


@respx.mock
async def test_retries_on_5xx_then_raises() -> None:
    """Повторяющийся 5xx исчерпывает retry и приводит к CbrUnavailableError."""
    route = respx.get(_SETTINGS.cbr_api_url).mock(return_value=httpx.Response(503))

    async with httpx.AsyncClient() as http:
        with pytest.raises(CbrUnavailableError):
            await CbrClient(_SETTINGS, http).fetch_rates()

    assert route.call_count == _SETTINGS.retry_attempts


@respx.mock
async def test_recovers_after_transient_5xx(sample_payload: dict) -> None:
    """После временного 5xx следующая попытка с 200 завершается успехом."""
    respx.get(_SETTINGS.cbr_api_url).mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json=sample_payload)]
    )

    async with httpx.AsyncClient() as http:
        snapshot = await CbrClient(_SETTINGS, http).fetch_rates()

    assert len(snapshot) == 4


@respx.mock
async def test_non_json_raises_response_error() -> None:
    """Тело ответа, не являющееся JSON, приводит к CbrResponseError."""
    respx.get(_SETTINGS.cbr_api_url).mock(
        return_value=httpx.Response(200, text="<html></html>")
    )

    async with httpx.AsyncClient() as http:
        with pytest.raises(CbrResponseError):
            await CbrClient(_SETTINGS, http).fetch_rates()


@respx.mock
async def test_timeout_raises_unavailable() -> None:
    """Таймаут соединения после retry приводит к CbrUnavailableError."""
    respx.get(_SETTINGS.cbr_api_url).mock(side_effect=httpx.ConnectTimeout("timeout"))

    async with httpx.AsyncClient() as http:
        with pytest.raises(CbrUnavailableError):
            await CbrClient(_SETTINGS, http).fetch_rates()
