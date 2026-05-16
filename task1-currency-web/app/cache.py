# FILE: task1-currency-web/app/cache.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Async-safe TTL-кэш снимка курсов поверх источника данных.
#   SCOPE: Протокол RatesSource и класс RatesCache с single-flight обновлением.
#   DEPENDS: M-T1-CBR-CLIENT, M-T1-CONFIG
#   LINKS: M-T1-CACHE
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   RatesSource - протокол источника курсов (async fetch_rates)
#   RatesCache - TTL-кэш снимка курсов; get_snapshot() с single-flight
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация TTL-кэша курсов.
# END_CHANGE_SUMMARY
"""Async-safe TTL-кэш снимка курсов валют."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Protocol

from app.domain import RatesSnapshot

logger = logging.getLogger(__name__)


class RatesSource(Protocol):
    """Источник снимков курсов (реализуется CbrClient)."""

    async def fetch_rates(self) -> RatesSnapshot:  # pragma: no cover - протокол
        ...


class RatesCache:
    """TTL-кэш снимка курсов валют.

    Курс ЦБ РФ обновляется раз в сутки, поэтому держать TTL и не дёргать API
    на каждый запрос — корректно и снижает нагрузку. Обновление защищено
    ``asyncio.Lock``: при одновременных запросах с холодным кэшем внешний вызов
    выполняется ровно один раз (single-flight).
    """

    def __init__(
        self,
        source: RatesSource,
        ttl_seconds: int,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._source = source
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = asyncio.Lock()
        self._snapshot: RatesSnapshot | None = None
        self._fetched_at: float = 0.0

    # START_CONTRACT: get_snapshot
    #   PURPOSE: Вернуть снимок курсов из кэша или обновить его при истёкшем TTL.
    #   INPUTS: none
    #   OUTPUTS: { RatesSnapshot - актуальный снимок курсов }
    #   SIDE_EFFECTS: возможный HTTP-запрос через источник при холодном/устаревшем кэше
    #   LINKS: M-T1-CACHE, M-T1-CBR-CLIENT
    # END_CONTRACT: get_snapshot
    async def get_snapshot(self) -> RatesSnapshot:
        """Отдать снимок курсов, обновив его при необходимости."""
        # START_BLOCK_REFRESH_IF_STALE
        # Lock удерживается на время обновления — конкурентные запросы при
        # холодном кэше дождутся первого и получат уже свежий снимок.
        async with self._lock:
            if self._snapshot is not None and not self._is_stale():
                logger.debug(
                    "[RatesCache][get_snapshot][BLOCK_REFRESH_IF_STALE] отдан кэш"
                )
                return self._snapshot

            logger.info(
                "[RatesCache][get_snapshot][BLOCK_REFRESH_IF_STALE] обновление курсов"
            )
            snapshot = await self._source.fetch_rates()
            self._snapshot = snapshot
            self._fetched_at = self._clock()
            return snapshot
        # END_BLOCK_REFRESH_IF_STALE

    def _is_stale(self) -> bool:
        """Истёк ли TTL текущего снимка."""
        return (self._clock() - self._fetched_at) >= self._ttl
