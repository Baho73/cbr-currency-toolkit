# FILE: task2-cbr-cli/tests/test_cli.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: End-to-end проверки точки входа CLI (M-T2-CLI) с замоканным HTTP.
#   SCOPE: Успешный прогон и экспорт, флаг --no-export, коды возврата на путях ошибок.
#   DEPENDS: M-T2-CLI, M-T2-CBR-CLIENT, M-T2-ERRORS
#   LINKS: V-M-T2-CLI
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_successful_run_exports_file - успешный прогон: exit 0 и файл экспорта
#   test_no_export_flag_skips_file - --no-export: exit 0 без файла
#   test_api_unavailable_exit_1 - недоступный API -> exit 1
#   test_bad_response_exit_2 - некорректный ответ -> exit 2
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация.
# END_CHANGE_SUMMARY
"""End-to-end тесты CLI-аналитика."""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from cbr_cli.__main__ import main

_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"


@respx.mock
async def test_successful_run_exports_file(sample_payload: dict, tmp_path: Path) -> None:
    """Успешный прогon возвращает 0 и создаёт файл экспорта."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=sample_payload))
    output = tmp_path / "rates.csv"

    exit_code = await main(["--format", "csv", "--output", str(output), "--top", "2"])

    assert exit_code == 0
    assert output.exists()


@respx.mock
async def test_no_export_flag_skips_file(sample_payload: dict, tmp_path: Path) -> None:
    """Флаг --no-export завершает успешно и не создаёт файл."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json=sample_payload))
    output = tmp_path / "should-not-exist.csv"

    exit_code = await main(["--no-export", "--output", str(output)])

    assert exit_code == 0
    assert not output.exists()


@respx.mock
async def test_api_unavailable_exit_1() -> None:
    """Недоступный API (постоянный 5xx) приводит к коду возврата 1."""
    respx.get(_API_URL).mock(return_value=httpx.Response(503))

    exit_code = await main(["--no-export"])

    assert exit_code == 1


@respx.mock
async def test_bad_response_exit_2() -> None:
    """Некорректный формат ответа приводит к коду возврата 2."""
    respx.get(_API_URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))

    exit_code = await main(["--no-export"])

    assert exit_code == 2
