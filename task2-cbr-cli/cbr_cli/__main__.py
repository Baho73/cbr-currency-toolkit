# FILE: task2-cbr-cli/cbr_cli/__main__.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Точка входа CLI-аналитика: разбор аргументов, оркестрация fetch->analyze->report, exit codes.
#   SCOPE: build_parser, async main (оркестрация), синхронная обёртка run.
#   DEPENDS: M-T2-CONFIG, M-T2-ERRORS, M-T2-CBR-CLIENT, M-T2-ANALYTICS, M-T2-REPORT
#   LINKS: M-T2-CLI
#   ROLE: SCRIPT
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   build_parser - конфигурация argparse CLI-аналитика
#   main - async-оркестратор пайплайна; возвращает exit code
#   run - синхронная обёртка для запуска через python -m cbr_cli
# END_MODULE_MAP
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Первичная реализация точки входа CLI.
# END_CHANGE_SUMMARY
"""Точка входа CLI-аналитика курсов валют ЦБ РФ."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from cbr_cli.analytics import RateAnalyzer
from cbr_cli.cbr_client import CbrClient
from cbr_cli.config import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF,
    load_settings,
)
from cbr_cli.errors import EXIT_CODES, CbrError
from cbr_cli.report import ConsoleReporter, FileExporter

logger = logging.getLogger("cbr_cli")

_GENERIC_ERROR_EXIT = 3
_DEFAULT_TOP = 5


# START_CONTRACT: build_parser
#   PURPOSE: Описать аргументы командной строки CLI-аналитика.
#   INPUTS: none
#   OUTPUTS: { argparse.ArgumentParser - сконфигурированный парсер }
#   SIDE_EFFECTS: none
#   LINKS: M-T2-CLI
# END_CONTRACT: build_parser
def build_parser() -> argparse.ArgumentParser:
    """Собрать парсер аргументов CLI."""
    parser = argparse.ArgumentParser(
        prog="cbr-cli",
        description="Аналитик курсов валют ЦБ РФ: суточная динамика, топ движений, экспорт.",
    )
    parser.add_argument(
        "--format",
        choices=FileExporter.SUPPORTED_FORMATS,
        default="csv",
        help="Формат файла экспорта (по умолчанию csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Путь файла экспорта. По умолчанию output/cbr_rates_<дата>.<формат>.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=_DEFAULT_TOP,
        help=f"Сколько валют показать в топе движений (по умолчанию {_DEFAULT_TOP}).",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Не сохранять файл, только вывод в консоль.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Подробное логирование (уровень DEBUG).",
    )
    return parser


# START_CONTRACT: main
#   PURPOSE: Выполнить полный пайплайн аналитики и вернуть код возврата процесса.
#   INPUTS: { argv: list[str] | None - аргументы командной строки }
#   OUTPUTS: { int - код возврата (0 успех, >0 ошибка) }
#   SIDE_EFFECTS: HTTP-запрос, вывод в stdout, запись файла экспорта
#   LINKS: M-T2-CLI
# END_CONTRACT: main
async def main(argv: list[str] | None = None) -> int:
    """Оркестрировать загрузку курсов, аналитику, отчёт и экспорт."""
    args = build_parser().parse_args(argv)
    _configure_logging(verbose=args.verbose)

    settings = load_settings()
    logger.debug(
        "[Cli][main][BLOCK_RUN_PIPELINE] retry=%d backoff=%.2f",
        DEFAULT_RETRY_ATTEMPTS,
        DEFAULT_RETRY_BACKOFF,
    )

    try:
        # START_BLOCK_RUN_PIPELINE
        async with CbrClient(settings) as client:
            snapshot = await client.fetch_rates()

        analyzer = RateAnalyzer(snapshot)
        analyses = analyzer.analyze()
        summary = analyzer.summary()

        _print_report(snapshot.date, analyses, summary, analyzer, args.top)

        if not args.no_export:
            target = args.output or _default_output_path(snapshot.date, args.format)
            written = FileExporter().export(analyses, target, args.format)
            print(f"\nРезультат сохранён: {written}")
        # END_BLOCK_RUN_PIPELINE
    except CbrError as exc:
        # Ожидаемый сбой интеграции — понятное сообщение и код из таблицы.
        exit_code = EXIT_CODES.get(type(exc), _GENERIC_ERROR_EXIT)
        logger.error("[Cli][main][BLOCK_RUN_PIPELINE] сбой интеграции: %s", exc)
        print(f"Ошибка: {exc}", file=sys.stderr)
        return exit_code
    except Exception as exc:  # noqa: BLE001 - граница процесса: ловим всё, чтобы не падать traceback'ом
        logger.exception("[Cli][main][BLOCK_RUN_PIPELINE] непредвиденная ошибка")
        print(f"Непредвиденная ошибка: {exc}", file=sys.stderr)
        return _GENERIC_ERROR_EXIT

    logger.info("[Cli][main][BLOCK_RUN_PIPELINE] пайплайн завершён успешно")
    return 0


def _print_report(
    snapshot_date: datetime,
    analyses: list,
    summary: object,
    analyzer: RateAnalyzer,
    top: int,
) -> None:
    """Напечатать заголовок, таблицу курсов и блок топ-движений."""
    print(f"Курсы валют ЦБ РФ на {snapshot_date:%d.%m.%Y}\n")
    print(ConsoleReporter().render(analyses, summary))  # type: ignore[arg-type]

    movers = analyzer.top_movers(top)
    if movers:
        print(f"\nТоп-{len(movers)} движений за сутки:")
        for position, item in enumerate(movers, start=1):
            print(f"  {position}. {item.code}: {item.delta_pct:+.2f}% ({item.name})")


def _default_output_path(snapshot_date: datetime, fmt: str) -> Path:
    """Построить путь файла экспорта по умолчанию."""
    return Path("output") / f"cbr_rates_{snapshot_date:%Y-%m-%d}.{fmt}"


def _configure_logging(*, verbose: bool) -> None:
    """Настроить корневой логгер CLI."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


# START_CONTRACT: run
#   PURPOSE: Синхронная обёртка для запуска CLI как процесса.
#   INPUTS: none (argv берётся из sys.argv внутри main)
#   OUTPUTS: { int - код возврата процесса }
#   SIDE_EFFECTS: запускает event loop через asyncio.run
#   LINKS: M-T2-CLI
# END_CONTRACT: run
def run() -> int:
    """Запустить CLI и вернуть код возврата."""
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(run())
