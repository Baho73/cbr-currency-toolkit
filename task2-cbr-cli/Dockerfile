# Образ CLI-аналитика курсов валют ЦБ РФ.
FROM python:3.12-slim

# UTF-8 вывод и небуферизованные логи — стабильное поведение в контейнере.
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Сначала зависимости — слой кэшируется, пока requirements.txt не изменился.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем исходный код пакета.
COPY cbr_cli ./cbr_cli

# Запуск без аргументов выгружает курсы и сохраняет экспорт в /app/output.
ENTRYPOINT ["python", "-m", "cbr_cli"]
