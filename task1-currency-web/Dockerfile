# Образ веб-конвертера валют ЦБ РФ (FastAPI + uvicorn).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Сначала зависимости — слой кэшируется до изменения requirements.txt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код приложения и статика фронтенда.
COPY app ./app
COPY static ./static

EXPOSE 8000

# Порт берётся из переменной PORT (нужно для облачных платформ вроде Render),
# по умолчанию 8000. Shell-форма CMD нужна для подстановки переменной.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
