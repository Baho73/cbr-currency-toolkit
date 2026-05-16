# FILE: task2-cbr-cli/cbr_cli/report.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Форматирование результата аналитики: читаемая консольная таблица и экспорт в CSV/JSON.
#   SCOPE: Классы ConsoleReporter (render -> str) и FileExporter (export -> Path).
#   DEPENDS: M-T2-DOMAIN
#   LINKS: M-T2-REPORT
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ConsoleReporter - рендер выровненной таблицы курсов и сводки в строку
#   FileExporter - экспорт результата аналитики в CSV или JSON
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация отчёта и экспорта.
# END_CHANGE_SUMMARY
"""Отчёт по курсам валют: консольная таблица и экспорт в файл."""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from cbr_cli.analytics import AnalysisSummary
from cbr_cli.domain import RateAnalysis

logger = logging.getLogger(__name__)

# Текстовые маркеры направления — устойчивы к любой кодировке консоли.
_DIRECTION_MARK = {"up": "▲", "down": "▼", "flat": "—"}

# Порядок и заголовки колонок экспорта; единый источник для CSV и консоли.
_EXPORT_FIELDS: tuple[str, ...] = (
    "code",
    "name",
    "nominal",
    "value",
    "previous",
    "delta_abs",
    "delta_pct",
    "direction",
)


class ConsoleReporter:
    """Формирует выровненную текстовую таблицу курсов и сводку."""

    # START_CONTRACT: render
    #   PURPOSE: Собрать человекочитаемый отчёт по курсам и сводке в одну строку.
    #   INPUTS: { analyses: Sequence[RateAnalysis], summary: AnalysisSummary }
    #   OUTPUTS: { str - готовый к печати многострочный отчёт }
    #   SIDE_EFFECTS: none
    #   LINKS: M-T2-REPORT
    # END_CONTRACT: render
    def render(self, analyses: Sequence[RateAnalysis], summary: AnalysisSummary) -> str:
        """Вернуть отчёт в виде многострочной строки."""
        header = f"{'Код':<5}{'Валюта':<32}{'Курс, ₽':>12}{'Δ за сутки':>14}{'Δ %':>10}  Напр."
        separator = "-" * len(header)

        lines = [header, separator]
        for item in sorted(analyses, key=lambda a: a.code):
            lines.append(
                f"{item.code:<5}"
                f"{self._truncate(item.name, 31):<32}"
                f"{item.value:>12.4f}"
                f"{item.delta_abs:>+14.4f}"
                f"{item.delta_pct:>+9.2f}%"
                f"  {_DIRECTION_MARK[item.direction]}"
            )

        lines.append(separator)
        lines.append(
            f"Всего валют: {summary.total_currencies}   "
            f"Среднее |Δ %|: {summary.average_abs_pct:.2f}%"
        )
        lines.append(
            f"Сильнее всех укрепилась: {summary.strongest.code} "
            f"({summary.strongest.delta_pct:+.2f}%)"
        )
        lines.append(
            f"Сильнее всех ослабла:   {summary.weakest.code} "
            f"({summary.weakest.delta_pct:+.2f}%)"
        )
        return "\n".join(lines)

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        """Обрезать длинное название валюты, чтобы не ломать выравнивание."""
        return text if len(text) <= limit else text[: limit - 1] + "…"


class FileExporter:
    """Экспортирует результат аналитики в файл CSV или JSON."""

    SUPPORTED_FORMATS = ("csv", "json")

    # START_CONTRACT: export
    #   PURPOSE: Сохранить разбор курсов в файл выбранного формата.
    #   INPUTS: { analyses: Sequence[RateAnalysis], path: Path, fmt: str }
    #   OUTPUTS: { Path - путь записанного файла }
    #   SIDE_EFFECTS: создание/перезапись файла на диске
    #   LINKS: M-T2-REPORT
    # END_CONTRACT: export
    def export(self, analyses: Sequence[RateAnalysis], path: Path, fmt: str) -> Path:
        """Записать результат аналитики в файл.

        :raises ValueError: запрошен неподдерживаемый формат.
        :raises OSError: каталог назначения недоступен для записи.
        """
        fmt = fmt.lower()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Неподдерживаемый формат экспорта: {fmt!r}. "
                f"Доступны: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # START_BLOCK_WRITE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "csv":
            self._write_csv(analyses, path)
        else:
            self._write_json(analyses, path)
        logger.info(
            "[Reporter][export][BLOCK_WRITE_FILE] записано %d валют в %s (%s)",
            len(analyses),
            path,
            fmt,
        )
        # END_BLOCK_WRITE_FILE
        return path

    @staticmethod
    def _write_csv(analyses: Sequence[RateAnalysis], path: Path) -> None:
        """Записать разбор курсов в CSV с заголовком."""
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=_EXPORT_FIELDS)
            writer.writeheader()
            for item in analyses:
                writer.writerow({field: getattr(item, field) for field in _EXPORT_FIELDS})

    @staticmethod
    def _write_json(analyses: Sequence[RateAnalysis], path: Path) -> None:
        """Записать разбор курсов в JSON (кириллица сохраняется как есть)."""
        rows = [
            {field: getattr(item, field) for field in _EXPORT_FIELDS}
            for item in analyses
        ]
        with path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
