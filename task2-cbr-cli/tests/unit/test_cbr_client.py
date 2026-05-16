# FILE: task2-cbr-cli/tests/unit/test_cbr_client.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки async HTTP-клиента API ЦБ РФ (M-T2-CBR-CLIENT).
#   SCOPE: Успешный разбор, retry на 5xx, восстановление после сбоя, ошибки формата, таймаут.
#   DEPENDS: M-T2-CBR-CLIENT, M-T2-CONFIG, M-T2-ERRORS
#   LINKS: V-M-T2-CBR-CLIENT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_fetch_parses_valid_response - валидный ответ -> RatesSnapshot
#   test_retries_on_5xx_then_raises - 5xx повторяется retry-раз -> CbrUnavailableError
#   test_recovers_after_transient_5xx - повтор после временного сбоя
#   test_non_json_raises_response_error - не-JSON -> CbrResponseError
#   test_missing_valute_raises_response_error - нет 'Valute' -> CbrResponseError
#   test_timeout_raises_unavailable - таймаут -> CbrUnavailableError
# END_MODULE_MAP
"""Тесты async HTTP-клиента API ЦБ РФ."""

from __future__ import annotations

import httpx
import pytest
import respx

from cbr_cli.cbr_client import CbrClient
from cbr_cli.config import Settings
from cbr_cli.errors import CbrResponseError, CbrUnavailableError

# Backoff 0 — тесты retry не должны реально спать.
_SETTINGS = Settings(
    cbr_api_url="https://api.test/daily_json.js",
    retry_attempts=3,
    retry_backoff=0.0,
)


@respx.mock
async def test_fetch_parses_valid_response(sample_payload: dict) -> None:
    """Валидный ответ 200 разбирается в снимок курсов."""
    respx.get(_SETTINGS.cbr_api_url).mock(
        return_value=httpx.Response(200, json=sample_payload)
    )

    async with CbrClient(_SETTINGS) as client:
        snapshot = await client.fetch_rates()

    assert len(snapshot) == 3


@respx.mock
async def test_retries_on_5xx_then_raises() -> None:
    """Повторяющийся 5xx исчерпывает retry и приводит к CbrUnavailableError."""
    route = respx.get(_SETTINGS.cbr_api_url).mock(
        return_value=httpx.Response(503)
    )

    async with CbrClient(_SETTINGS) as client:
        with pytest.raises(CbrUnavailableError):
            await client.fetch_rates()

    # Ровно retry_attempts запросов и ни одного сверх — после исчерпания не стучимся.
    assert route.call_count == _SETTINGS.retry_attempts


@respx.mock
async def test_recovers_after_transient_5xx(sample_payload: dict) -> None:
    """После временного 5xx следующая попытка с 200 завершается успехом."""
    respx.get(_SETTINGS.cbr_api_url).mock(
        side_effect=[
            httpx.Response(502),
            httpx.Response(200, json=sample_payload),
        ]
    )

    async with CbrClient(_SETTINGS) as client:
        snapshot = await client.fetch_rates()

    assert len(snapshot) == 3


@respx.mock
async def test_non_json_raises_response_error() -> None:
    """Тело ответа, не являющееся JSON, приводит к CbrResponseError."""
    respx.get(_SETTINGS.cbr_api_url).mock(
        return_value=httpx.Response(200, text="<html>error</html>")
    )

    async with CbrClient(_SETTINGS) as client:
        with pytest.raises(CbrResponseError):
            await client.fetch_rates()


@respx.mock
async def test_missing_valute_raises_response_error() -> None:
    """JSON без ключа 'Valute' приводит к CbrResponseError."""
    respx.get(_SETTINGS.cbr_api_url).mock(
        return_value=httpx.Response(200, json={"Date": "2024-01-10T11:30:00+03:00"})
    )

    async with CbrClient(_SETTINGS) as client:
        with pytest.raises(CbrResponseError):
            await client.fetch_rates()


@respx.mock
async def test_timeout_raises_unavailable() -> None:
    """Таймаут соединения после retry приводит к CbrUnavailableError."""
    route = respx.get(_SETTINGS.cbr_api_url).mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )

    async with CbrClient(_SETTINGS) as client:
        with pytest.raises(CbrUnavailableError):
            await client.fetch_rates()

    assert route.call_count == _SETTINGS.retry_attempts


@respx.mock
async def test_client_error_4xx_not_retried() -> None:
    """4xx не повторяется (повтор бессмыслен) и даёт CbrResponseError."""
    route = respx.get(_SETTINGS.cbr_api_url).mock(
        return_value=httpx.Response(404)
    )

    async with CbrClient(_SETTINGS) as client:
        with pytest.raises(CbrResponseError):
            await client.fetch_rates()

    assert route.call_count == 1
