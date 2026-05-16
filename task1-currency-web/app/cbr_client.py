# FILE: task1-currency-web/app/cbr_client.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Асинхронный HTTP-клиент к API ЦБ РФ с retry, таймаутом и валидацией формата ответа.
#   SCOPE: Класс CbrClient: запрос с экспоненциальным backoff, разбор ответа в RatesSnapshot.
#   DEPENDS: M-T1-CONFIG, M-T1-DOMAIN, M-T1-ERRORS
#   LINKS: M-T1-CBR-CLIENT
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CbrClient - async-клиент API ЦБ РФ; fetch_rates() -> RatesSnapshot
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация async-клиента с retry.
# END_CHANGE_SUMMARY
"""Асинхронный HTTP-клиент к API курсов валют ЦБ РФ."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx

from app.config import Settings
from app.domain import RatesSnapshot
from app.errors import CbrResponseError, CbrUnavailableError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_FLOOR = 500


class CbrClient:
    """Асинхронный клиент API ЦБ РФ.

    HTTP-клиент ``httpx.AsyncClient`` внедряется извне: его жизненным циклом
    владеет приложение (lifespan), что даёт переиспользование пула соединений
    и упрощает подмену в тестах.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    # START_CONTRACT: fetch_rates
    #   PURPOSE: Получить актуальный снимок курсов валют ЦБ РФ.
    #   INPUTS: none (URL и параметры retry берутся из Settings)
    #   OUTPUTS: { RatesSnapshot - валидированный снимок курсов }
    #   SIDE_EFFECTS: HTTP-запрос к внешнему API; asyncio.sleep между повторами
    #   LINKS: M-T1-CBR-CLIENT, M-T1-DOMAIN
    # END_CONTRACT: fetch_rates
    async def fetch_rates(self) -> RatesSnapshot:
        """Загрузить и разобрать курсы валют.

        :raises CbrUnavailableError: API недоступен после исчерпания retry.
        :raises CbrResponseError: ответ получен, но непригоден к разбору.
        """
        # START_BLOCK_FETCH_WITH_RETRY
        attempts = self._settings.retry_attempts
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(self._settings.cbr_api_url)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                logger.warning(
                    "[CbrClient][fetch_rates][BLOCK_FETCH_WITH_RETRY] "
                    "сетевая ошибка, попытка %d/%d: %s",
                    attempt, attempts, exc,
                )
                await self._sleep_before_retry(attempt, attempts)
                continue

            if response.status_code >= _RETRYABLE_STATUS_FLOOR:
                last_error = CbrUnavailableError(
                    f"API вернул статус {response.status_code}"
                )
                logger.warning(
                    "[CbrClient][fetch_rates][BLOCK_FETCH_WITH_RETRY] "
                    "статус %d, попытка %d/%d",
                    response.status_code, attempt, attempts,
                )
                await self._sleep_before_retry(attempt, attempts)
                continue

            if response.status_code >= 400:
                raise CbrResponseError(
                    f"API вернул клиентскую ошибку {response.status_code}"
                )

            logger.info(
                "[CbrClient][fetch_rates][BLOCK_FETCH_WITH_RETRY] "
                "успешный ответ с попытки %d/%d",
                attempt, attempts,
            )
            return self._parse_response(response)
        # END_BLOCK_FETCH_WITH_RETRY

        raise CbrUnavailableError(
            f"API ЦБ РФ недоступен после {attempts} попыток"
        ) from last_error

    async def _sleep_before_retry(self, attempt: int, attempts: int) -> None:
        """Выдержать экспоненциальную паузу перед следующей попыткой."""
        if attempt >= attempts:
            return
        delay = self._settings.retry_backoff * (2 ** (attempt - 1))
        if delay > 0:
            await asyncio.sleep(delay)

    def _parse_response(self, response: httpx.Response) -> RatesSnapshot:
        """Разобрать тело успешного ответа в RatesSnapshot."""
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise CbrResponseError("Ответ API не является корректным JSON") from exc
        return RatesSnapshot.from_api_payload(payload)
