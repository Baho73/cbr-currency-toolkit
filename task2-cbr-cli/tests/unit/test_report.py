# FILE: task2-cbr-cli/tests/unit/test_report.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Проверки отчёта и экспорта (M-T2-REPORT).
#   SCOPE: Содержимое консольной таблицы, валидность CSV и JSON, отказ на неизвестном формате.
#   DEPENDS: M-T2-REPORT, M-T2-ANALYTICS, M-T2-DOMAIN
#   LINKS: V-M-T2-REPORT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_console_lists_all_currencies - таблица содержит все валюты и сводку
#   test_csv_export_valid - CSV пишется с корректным заголовком и строками
#   test_json_export_valid - JSON пишется валидным и с кириллицей
#   test_unknown_format_rejected - неизвестный формат -> ValueError
# END_MODULE_MAP
"""Тесты отчёта и экспорта результатов аналитики."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from cbr_cli.analytics import RateAnalyzer
from cbr_cli.domain import RatesSnapshot
from cbr_cli.report import ConsoleReporter, FileExporter


def test_console_lists_all_currencies(sample_snapshot: RatesSnapshot) -> None:
    """Консольная таблица содержит все валюты и блок сводки."""
    analyzer = RateAnalyzer(sample_snapshot)
    text = ConsoleReporter().render(analyzer.analyze(), analyzer.summary())

    for code in ("USD", "EUR", "JPY"):
        assert code in text
    assert "Всего валют: 3" in text


def test_csv_export_valid(sample_snapshot: RatesSnapshot, tmp_path: Path) -> None:
    """Экспорт в CSV даёт файл с корректным заголовком и числом строк."""
    analyzer = RateAnalyzer(sample_snapshot)
    target = tmp_path / "out" / "rates.csv"

    result_path = FileExporter().export(analyzer.analyze(), target, "csv")

    assert result_path == target
    with result_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert set(rows[0].keys()) == {
        "code", "name", "nominal", "value", "previous",
        "delta_abs", "delta_pct", "direction",
    }


def test_json_export_valid(sample_snapshot: RatesSnapshot, tmp_path: Path) -> None:
    """Экспорт в JSON даёт валидный файл с сохранённой кириллицей."""
    analyzer = RateAnalyzer(sample_snapshot)
    target = tmp_path / "rates.json"

    FileExporter().export(analyzer.analyze(), target, "json")

    data = json.loads(target.read_text(encoding="utf-8"))
    assert len(data) == 3
    names = {row["name"] for row in data}
    assert "Доллар США" in names  # кириллица не экранирована в \uXXXX


def test_unknown_format_rejected(sample_snapshot: RatesSnapshot, tmp_path: Path) -> None:
    """Неподдерживаемый формат экспорта приводит к ValueError."""
    analyzer = RateAnalyzer(sample_snapshot)

    with pytest.raises(ValueError):
        FileExporter().export(analyzer.analyze(), tmp_path / "x.xml", "xml")
