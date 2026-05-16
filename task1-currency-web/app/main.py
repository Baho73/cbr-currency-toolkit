# FILE: task1-currency-web/app/main.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Сборка приложения FastAPI: lifespan, DI кэша/клиента, статика, обработчики ошибок.
#   SCOPE: Фабрика create_app и ASGI-инстанс app для uvicorn.
#   DEPENDS: M-T1-API, M-T1-CONFIG, M-T1-CACHE, M-T1-CBR-CLIENT
#   LINKS: M-T1-APP
#   ROLE: ENTRY_POINT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   create_app - фабрика FastAPI-приложения
#   app - ASGI-инстанс для uvicorn
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация сборки приложения.
# END_CHANGE_SUMMARY
"""Сборка ASGI-приложения веб-конвертера валют."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import build_router
from app.cache import RatesCache
from app.cbr_client import CbrClient
from app.config import Settings, get_settings
from app.converter import CurrencyConverter
from app.errors import CbrError, ConversionError

logger = logging.getLogger(__name__)

# Статика лежит рядом с пакетом app/ — каталог static/ в корне проекта.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# START_CONTRACT: create_app
#   PURPOSE: Собрать и сконфигурировать экземпляр приложения FastAPI.
#   INPUTS: { settings: Settings | None - конфигурация, по умолчанию get_settings() }
#   OUTPUTS: { FastAPI - готовое ASGI-приложение }
#   SIDE_EFFECTS: регистрация роутов, обработчиков ошибок и монтирование статики
#   LINKS: M-T1-APP, M-T1-API
# END_CONTRACT: create_app
def create_app(settings: Settings | None = None) -> FastAPI:
    """Создать ASGI-приложение веб-конвертера."""
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # START_BLOCK_LIFESPAN
        # Один httpx.AsyncClient на всё приложение: переиспользование пула соединений.
        http_client = httpx.AsyncClient(timeout=resolved.http_timeout)
        cbr_client = CbrClient(resolved, http_client)
        application.state.cache = RatesCache(cbr_client, resolved.cache_ttl_seconds)
        application.state.converter = CurrencyConverter()
        logger.info("[AppFactory][lifespan][BLOCK_LIFESPAN] приложение инициализировано")
        try:
            yield
        finally:
            await http_client.aclose()
            logger.info("[AppFactory][lifespan][BLOCK_LIFESPAN] ресурсы освобождены")
        # END_BLOCK_LIFESPAN

    application = FastAPI(
        title="Конвертер валют ЦБ РФ",
        version=__version__,
        description="Веб-утилита: курсы валют ЦБ РФ и кросс-конвертация сумм.",
        lifespan=lifespan,
    )
    application.include_router(build_router())
    _register_exception_handlers(application)

    # Статика монтируется последней, чтобы не перехватывать /api/*.
    if _STATIC_DIR.is_dir():
        application.mount(
            "/", StaticFiles(directory=_STATIC_DIR, html=True), name="static"
        )
    return application


def _register_exception_handlers(application: FastAPI) -> None:
    """Транслировать доменные исключения в корректные HTTP-коды."""

    async def handle_cbr_error(_: Request, exc: Exception) -> JSONResponse:
        # Сбой внешнего API -> 502 Bad Gateway.
        logger.warning("[AppFactory][handle_cbr_error] %s", exc)
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    async def handle_conversion_error(_: Request, exc: Exception) -> JSONResponse:
        # Некорректный запрос конвертации (валюта/сумма) -> 400 Bad Request.
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    application.add_exception_handler(CbrError, handle_cbr_error)
    application.add_exception_handler(ConversionError, handle_conversion_error)


# ASGI-инстанс по умолчанию: `uvicorn app.main:app`.
app = create_app()
