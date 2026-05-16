# FILE: task1-currency-web/tests/unit/test_cache.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки async TTL-кэша курсов (M-T1-CACHE).
#   SCOPE: Кэш в пределах TTL, обновление по истечении TTL, single-flight при конкуренции.
#   DEPENDS: M-T1-CACHE, M-T1-DOMAIN
#   LINKS: V-M-T1-CACHE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CountingSource - тестовый источник курсов со счётчиком обращений
#   MutableClock - управляемые часы для проверки TTL
#   test_caches_within_ttl / test_refreshes_after_ttl / test_single_flight
# END_MODULE_MAP
"""Тесты async TTL-кэша курсов валют."""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.cache import RatesCache
from app.domain import RatesSnapshot


def _empty_snapshot() -> RatesSnapshot:
    """Минимальный снимок для подстановки в тестах кэша."""
    return RatesSnapshot(
        date=datetime(2024, 1, 10),
        previous_date=datetime(2024, 1, 9),
        _by_code={},
    )


class CountingSource:
    """Источник курсов, считающий число обращений к fetch_rates."""

    def __init__(self) -> None:
        self.calls = 0

    async def fetch_rates(self) -> RatesSnapshot:
        self.calls += 1
        # Небольшая уступка циклу событий — провоцирует гонку в тесте single-flight.
        await asyncio.sleep(0)
        return _empty_snapshot()


class MutableClock:
    """Управляемые часы: возвращают заданное значение времени."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def test_caches_within_ttl() -> None:
    """Повторный запрос в пределах TTL не обращается к источнику."""
    source = CountingSource()
    cache = RatesCache(source, ttl_seconds=100, clock=MutableClock())

    await cache.get_snapshot()
    await cache.get_snapshot()

    assert source.calls == 1


async def test_refreshes_after_ttl() -> None:
    """По истечении TTL выполняется новое обращение к источнику."""
    source = CountingSource()
    clock = MutableClock()
    cache = RatesCache(source, ttl_seconds=100, clock=clock)

    await cache.get_snapshot()
    clock.now = 150.0  # TTL истёк
    await cache.get_snapshot()

    assert source.calls == 2


async def test_single_flight_on_cold_cache() -> None:
    """Конкурентные запросы при холодном кэше дают ровно один внешний вызов."""
    source = CountingSource()
    cache = RatesCache(source, ttl_seconds=100, clock=MutableClock())

    await asyncio.gather(*(cache.get_snapshot() for _ in range(10)))

    assert source.calls == 1
