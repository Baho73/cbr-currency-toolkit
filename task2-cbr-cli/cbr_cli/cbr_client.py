# FILE: task2-cbr-cli/cbr_cli/cbr_client.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Асинхронный HTTP-клиент к API ЦБ РФ с retry, таймаутом и валидацией формата ответа.
#   SCOPE: Класс CbrClient: выполнение запроса с экспоненциальным backoff, разбор ответа в RatesSnapshot.
#   DEPENDS: M-T2-CONFIG, M-T2-DOMAIN, M-T2-ERRORS
#   LINKS: M-T2-CBR-CLIENT
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CbrClient - async-клиент API ЦБ РФ; метод fetch_rates() -> RatesSnapshot
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация async-клиента с retry и валидацией.
# END_CHANGE_SUMMARY
"""Асинхронный HTTP-клиент к API курсов валют ЦБ РФ."""

from __future__ import annotations

import asyncio
import json
import logging
from types import TracebackType

import httpx

from cbr_cli.config import Settings
from cbr_cli.domain import RatesSnapshot
from cbr_cli.errors import CbrResponseError, CbrUnavailableError

_logger = logging.getLogger(__name__)

# 5xx считаем временными сбоями сервера — их имеет смысл повторять.
_RETRYABLE_STATUS_FLOOR = 500


class CbrClient:
    """Асинхронный клиент API ЦБ РФ.

    Используется как async context manager. При получении ``client`` извне
    клиент не владеет его жизненным циклом (удобно для тестов и переиспользования
    пула соединений), иначе создаёт и закрывает ``httpx.AsyncClient`` сам.
    """

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "CbrClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._settings.http_timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # START_CONTRACT: fetch_rates
    #   PURPOSE: Получить актуальный снимок курсов валют ЦБ РФ.
    #   INPUTS: none (URL и параметры retry берутся из Settings)
    #   OUTPUTS: { RatesSnapshot - валидированный снимок курсов }
    #   SIDE_EFFECTS: HTTP-запрос к внешнему API; asyncio.sleep между повторами
    #   LINKS: M-T2-CBR-CLIENT, M-T2-DOMAIN
    # END_CONTRACT: fetch_rates
    async def fetch_rates(self) -> RatesSnapshot:
        """Загрузить и разобрать курсы валют.

        :raises CbrUnavailableError: API недоступен после исчерпания retry.
        :raises CbrResponseError: ответ получен, но непригоден к разбору.
        """
        if self._client is None:
            raise RuntimeError("CbrClient используется вне 'async with' контекста")

        # START_BLOCK_FETCH_WITH_RETRY
        attempts = self._settings.retry_attempts
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(self._settings.cbr_api_url)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                # Сетевой сбой или таймаут — кандидат на повтор.
                last_error = exc
                _logger.warning(
                    "[CbrClient][fetch_rates][BLOCK_FETCH_WITH_RETRY] "
                    "сетевая ошибка, попытка %d/%d: %s",
                    attempt,
                    attempts,
                    exc,
                )
                await self._sleep_before_retry(attempt, attempts)
                continue

            if response.status_code >= _RETRYABLE_STATUS_FLOOR:
                # 5xx — временный сбой сервера, повторяем.
                last_error = CbrUnavailableError(
                    f"API вернул статус {response.status_code}"
                )
                _logger.warning(
                    "[CbrClient][fetch_rates][BLOCK_FETCH_WITH_RETRY] "
                    "статус %d, попытка %d/%d",
                    response.status_code,
                    attempt,
                    attempts,
                )
                await self._sleep_before_retry(attempt, attempts)
                continue

            if response.status_code >= 400:
                # 4xx — ошибка запроса; повтор не поможет, прекращаем сразу.
                raise CbrResponseError(
                    f"API вернул клиентскую ошибку {response.status_code}"
                )

            _logger.info(
                "[CbrClient][fetch_rates][BLOCK_FETCH_WITH_RETRY] "
                "успешный ответ с попытки %d/%d",
                attempt,
                attempts,
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
