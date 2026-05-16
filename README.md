# Утилиты курсов валют ЦБ РФ — тестовое задание

Монорепозиторий из трёх независимых утилит вокруг публичного API курсов валют
ЦБ РФ (`cbr-xml-daily.ru`). Итоговый документ сдачи — **[SUBMISSION.md](SUBMISSION.md)**.

## Проекты

| Папка | Задача | Стек | Запуск |
|---|---|---|---|
| [`task1-currency-web/`](task1-currency-web/) | Веб-конвертер валют | FastAPI + async + фронтенд | `docker build` / `uvicorn` |
| [`task2-cbr-cli/`](task2-cbr-cli/) | CLI-аналитик курсов | Python + async + Docker | `docker build` / `python -m cbr_cli` |
| [`task3-apps-script/`](task3-apps-script/) | Выгрузка в Google Таблицу | Google Apps Script | установка в таблицу |

У каждого проекта свой `README.md` с инструкцией запуска.

## Особенности

- **ООП и асинхронность** во всех Python-проектах: сервисы-классы, `httpx.AsyncClient`,
  async-роуты FastAPI.
- **Устойчивость к сбоям:** retry с экспоненциальным backoff, таймауты,
  иерархия исключений, строгая валидация ответов внешнего API.
- **65 автотестов** (pytest, замоканный HTTP) — реальная сеть в тестах не нужна.
- **Docker** для обоих Python-проектов.

## Методология

Проект разработан по методологии **GRACE** (контракт-ориентированная разработка).
Артефакты — в `docs/`: требования, технологический стек, план разработки,
граф знаний, план верификации. Инженерный протокол — в `AGENTS.md`.

## Быстрый старт

```bash
# Задача 1 — веб-конвертер
cd task1-currency-web && docker build -t currency-web . && docker run -p 8000:8000 currency-web

# Задача 2 — CLI-аналитик
cd task2-cbr-cli && docker build -t cbr-cli . && docker run --rm cbr-cli --no-export

# Задача 3 — см. task3-apps-script/README.md
```
