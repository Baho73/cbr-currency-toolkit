# FILE: task1-currency-web/app/api.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: HTTP-роуты конвертера: список курсов, конвертация суммы, health-check.
#   SCOPE: Фабрика build_router и преобразование снимка в схему ответа.
#   DEPENDS: M-T1-SCHEMAS, M-T1-CACHE, M-T1-CONVERTER, M-T1-ERRORS
#   LINKS: M-T1-API
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   build_router - сборка APIRouter с роутами /api/rates, /api/convert, /api/health
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация HTTP-роутов.
# END_CHANGE_SUMMARY
"""HTTP-роуты REST API веб-конвертера валют."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.domain import RatesSnapshot
from app.schemas import ConvertRequest, ConvertResponse, RateItem, RatesResponse

logger = logging.getLogger(__name__)


# START_CONTRACT: build_router
#   PURPOSE: Собрать роутер REST API конвертера.
#   INPUTS: none (зависимости берутся из app.state в обработчиках)
#   OUTPUTS: { APIRouter - роутер с префиксом /api }
#   SIDE_EFFECTS: none
#   LINKS: M-T1-API
# END_CONTRACT: build_router
def build_router() -> APIRouter:
    """Создать APIRouter с эндпоинтами конвертера.

    Кэш и конвертер достаются из ``request.app.state`` — они инициализируются
    в lifespan приложения (см. M-T1-APP), что делает роуты тонкими и тестируемыми.
    """
    router = APIRouter(prefix="/api", tags=["currency"])

    @router.get("/health", summary="Проверка живости сервиса")
    async def health() -> dict[str, str]:
        """Лёгкий health-check без обращения к внешнему API."""
        return {"status": "ok"}

    @router.get("/rates", response_model=RatesResponse, summary="Актуальные курсы валют")
    async def rates(request: Request) -> RatesResponse:
        """Вернуть текущий снимок курсов валют ЦБ РФ."""
        snapshot = await request.app.state.cache.get_snapshot()
        return _snapshot_to_response(snapshot)

    @router.post("/convert", response_model=ConvertResponse, summary="Конвертация суммы")
    async def convert(request: Request, body: ConvertRequest) -> ConvertResponse:
        """Сконвертировать сумму между двумя валютами по текущему курсу."""
        # START_BLOCK_HANDLE_CONVERT
        snapshot = await request.app.state.cache.get_snapshot()
        result = request.app.state.converter.convert(
            body.amount, body.from_code, body.to_code, snapshot
        )
        logger.info(
            "[ApiRoutes][handle_convert][BLOCK_HANDLE_CONVERT] %s %s -> %s = %s",
            body.amount, result.from_code, result.to_code, result.result,
        )
        return ConvertResponse(
            amount=result.amount,
            from_code=result.from_code,
            to_code=result.to_code,
            result=result.result,
            rate=result.rate,
            snapshot_date=snapshot.date.isoformat(),
        )
        # END_BLOCK_HANDLE_CONVERT

    return router


def _snapshot_to_response(snapshot: RatesSnapshot) -> RatesResponse:
    """Преобразовать доменный снимок курсов в схему ответа API."""
    items = [
        RateItem(
            code=currency.code,
            name=currency.name,
            nominal=currency.nominal,
            value=currency.value,
            previous=currency.previous,
            delta_abs=round(currency.delta_abs, 4),
            delta_pct=round(currency.delta_pct, 4),
        )
        for currency in snapshot.currencies
    ]
    return RatesResponse(
        date=snapshot.date.isoformat(),
        previous_date=snapshot.previous_date.isoformat(),
        count=len(items),
        rates=items,
    )
