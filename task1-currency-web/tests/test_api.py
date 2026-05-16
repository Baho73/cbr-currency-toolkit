# FILE: task1-currency-web/tests/test_api.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Интеграционные проверки HTTP-API конвертера (M-T1-API, M-T1-APP).
#   SCOPE: health, список курсов, конвертация, валидация 422, ошибки 400/502.
#   DEPENDS: M-T1-API, M-T1-APP, M-T1-CBR-CLIENT, M-T1-ERRORS
#   LINKS: V-M-T1-API, V-M-T1-APP, V-M-T1-SCHEMAS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   client - фикстура TestClient с поднятым через lifespan приложением
#   test_health_ok / test_rates_lists_currencies / test_convert_ok
#   test_convert_validation_422 / test_convert_unknown_currency_400
#   test_api_unavailable_502
# END_MODULE_MAP
"""Интеграционные тесты HTTP-API веб-конвертера."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

_API_URL = get_settings().cbr_api_url


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient с приложением, поднятым через lifespan."""
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_ok(client: TestClient) -> None:
    """GET /api/health отвечает 200 и статусом ok."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@respx.mock
def test_rates_lists_currencies(client: TestClient, sample_payload: dict) -> None:
    """GET /api/rates возвращает список валют (с замоканным API)."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=sample_payload))

    response = client.get("/api/rates")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4  # USD, EUR, JPY + RUB
    codes = {item["code"] for item in body["rates"]}
    assert "USD" in codes


@respx.mock
def test_convert_ok(client: TestClient, sample_payload: dict) -> None:
    """POST /api/convert с валидным телом возвращает корректный результат."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=sample_payload))

    response = client.post(
        "/api/convert", json={"amount": 1000, "from_code": "rub", "to_code": "usd"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == pytest.approx(10.0)  # 1000 ₽ / 100 ₽ за USD
    assert body["from_code"] == "RUB"


def test_convert_validation_422(client: TestClient) -> None:
    """POST /api/convert с неположительной суммой даёт 422."""
    response = client.post(
        "/api/convert", json={"amount": -5, "from_code": "USD", "to_code": "RUB"}
    )

    assert response.status_code == 422


@respx.mock
def test_convert_unknown_currency_400(client: TestClient, sample_payload: dict) -> None:
    """POST /api/convert с неизвестной валютой даёт 400."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=sample_payload))

    response = client.post(
        "/api/convert", json={"amount": 100, "from_code": "USD", "to_code": "ZZZ"}
    )

    assert response.status_code == 400


@respx.mock
def test_api_unavailable_502(client: TestClient) -> None:
    """Недоступность внешнего API транслируется в 502."""
    respx.get(_API_URL).mock(return_value=httpx.Response(503))

    response = client.get("/api/rates")

    assert response.status_code == 502
