# Деплой веб-конвертера на VPS (nginx + Docker)

Боевая версия: <https://converter.teamplan.ru>

Сценарий: VPS с уже работающим nginx как reverse proxy и другими проектами.
Приложение добавляется отдельным субдоменом 3-го уровня, не затрагивая остальные
сайты — nginx разводит запросы по `server_name`.

```
Интернет → nginx (443, HTTPS) → 127.0.0.1:8003 → Docker-контейнер currency-web
```

## Предпосылки

- VPS с nginx, Docker и certbot.
- DNS: A-запись субдомена (`converter.teamplan.ru`) → IP сервера.
- Свободный локальный порт (здесь `8003`).

## Шаги

**1. Код и контейнер**
```bash
cd /opt
git clone https://github.com/Baho73/cbr-currency-toolkit
cd cbr-currency-toolkit/task1-currency-web
docker build -t currency-web .
docker run -d --name currency-web --restart unless-stopped \
  -p 127.0.0.1:8003:8000 currency-web
```
Контейнер привязан к `127.0.0.1` — наружу не открыт, единственная точка входа — nginx.

**2. nginx — HTTP-блок (для выпуска сертификата)**

Временно положить конфиг только с `listen 80` (acme-challenge + proxy_pass),
затем `nginx -t && systemctl reload nginx`.

**3. HTTPS-сертификат (Let's Encrypt, webroot)**
```bash
mkdir -p /var/www/letsencrypt
certbot certonly --webroot -w /var/www/letsencrypt \
  -d converter.teamplan.ru --non-interactive --agree-tos
```

**4. Финальный конфиг nginx**

Скопировать `nginx-converter.teamplan.ru.conf` в
`/etc/nginx/sites-enabled/converter.teamplan.ru`, затем:
```bash
nginx -t && systemctl reload nginx
```
`nginx -t` перед каждым `reload` — обязателен: гарантирует, что соседние сайты не упадут.

## Обновление версии

```bash
cd /opt/cbr-currency-toolkit && git pull
cd task1-currency-web
docker build -t currency-web .
docker rm -f currency-web
docker run -d --name currency-web --restart unless-stopped \
  -p 127.0.0.1:8003:8000 currency-web
```

## Проверка

```bash
curl -I https://converter.teamplan.ru/            # 200
curl -I http://converter.teamplan.ru/             # 301 → https
curl https://converter.teamplan.ru/api/health     # {"status":"ok"}
```
