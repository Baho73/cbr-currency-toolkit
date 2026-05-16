# Task 1 — Веб-конвертер валют ЦБ РФ (FastAPI)

Веб-утилита: конвертация сумм между валютами по официальным курсам ЦБ РФ.
Асинхронный бэкенд на FastAPI с HTTP-клиентом к API ЦБ РФ, TTL-кэшем курсов
и кросс-конвертацией через рубль; фронтенд на чистом HTML/CSS/JS.

## Что делает

- Загружает курсы с `https://www.cbr-xml-daily.ru/daily_json.js` (JSON, без авторизации).
- Показывает таблицу курсов с суточной динамикой (цветовая подсветка).
- Конвертирует сумму между **любыми** двумя валютами по кросс-курсу через рубль,
  корректно учитывая номинал (например, иена с номиналом 100).
- Кэширует курсы (ЦБ обновляет раз в сутки) — не дёргает внешний API на каждый запрос.

## Нетривиальная логика

**Кросс-конвертация через рубль с учётом номинала.** API ЦБ даёт стоимость
`Nominal` единиц валюты в рублях. Курс приводится к одной единице
(`rate_per_unit = value / nominal`), сумма переводится в рубли и затем в целевую
валюту. Расчёт ведётся в `Decimal` для денежной точности. См. `app/converter.py`.

## Архитектура

Проект построен по принципам GRACE: контракт на каждый модуль, ООП, async.

| Модуль | Файл | Ответственность |
|---|---|---|
| Config | `app/config.py` | Конфигурация (pydantic-settings) |
| Errors | `app/errors.py` | Иерархия исключений |
| Domain | `app/domain.py` | Модели курсов + парсер ответа API + синтетический рубль |
| ApiSchemas | `app/schemas.py` | Pydantic-схемы запросов/ответов |
| CbrClient | `app/cbr_client.py` | Async HTTP-клиент с retry и backoff |
| RatesCache | `app/cache.py` | Async TTL-кэш с single-flight |
| CurrencyConverter | `app/converter.py` | Кросс-конвертация через рубль |
| ApiRoutes | `app/api.py` | HTTP-роуты REST API |
| AppFactory | `app/main.py` | Сборка FastAPI: lifespan, DI, статика |
| Frontend | `static/` | UI (ООП-классы `ApiClient`, `ConverterController`) |

**Устойчивость:** async ввод-вывод (`httpx.AsyncClient`, async-роуты FastAPI),
retry с экспоненциальным backoff и таймаутом, TTL-кэш с защитой от гонок
(`asyncio.Lock`, single-flight), иерархия исключений с трансляцией в HTTP-коды
(502/400/422), типизация и неизменяемые модели, 33 теста с замоканным HTTP.

## REST API

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/health` | Health-check |
| `GET` | `/api/rates` | Снимок курсов валют |
| `POST` | `/api/convert` | Конвертация суммы (`{amount, from_code, to_code}`) |
| `GET` | `/` | Фронтенд (статика) |

## Запуск через Docker (рекомендуется)

```bash
docker build -t currency-web .
docker run --rm -p 8000:8000 currency-web
```

Открыть <http://localhost:8000>.

## Локальный запуск

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Открыть <http://localhost:8000>.

## Деплой

Файл `render.yaml` описывает деплой на [Render.com](https://render.com) (free tier,
Docker). В дашборде Render: **New → Blueprint** и указать репозиторий — сервис
поднимется автоматически, health-check по `/api/health`.

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

## Конфигурация

Переменные окружения с префиксом `APP_` (см. `app/config.py`):
`APP_HTTP_TIMEOUT`, `APP_RETRY_ATTEMPTS`, `APP_CACHE_TTL_SECONDS` и др.
