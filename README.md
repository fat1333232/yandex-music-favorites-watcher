# Yandex Music Favorites Watcher

Telegram-бот, который отслеживает изменения в вашем плейлисте «Избранное» в Яндекс Музыке и уведомляет, если трек пропал из лайкнутых.

## Особенности

- Мониторинг избранного — периодическая проверка плейлиста «Мне нравится»
- Уведомления в Telegram — мгновенное оповещение, если трек удалён
- Сохранение истории — кэширование состояния для сравнения
- Docker-поддержка — готовый контейнер для развёртывания
- Гибкая настройка — интервал проверки, путь к кэшу через .env

## Как это работает

1. Бот получает список лайкнутых треков через неофициальное API Яндекс Музыки
2. Сравнивает с предыдущим состоянием (хранится в JSON-файле)
3. Если находит треки, которые пропали — отправляет уведомление в Telegram с названием, артистом и ссылкой

## Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/fat1333232/yandex-music-favorites-watcher.git
cd yandex-music-favorites-watcher
```

### 2. Настройка

Создайте файл .env на основе .env.example:

```bash
cp .env.example .env
```

Заполните переменные:

```bash
YANDEX_TOKEN=your_yandex_oauth_token
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=123456789
DATA_FILE=/app/data/favorites_cache.json
CHECK_INTERVAL=3600
```

#### Получение токенов

Yandex Music OAuth Token:
```bash
pip install yandex-music
python -m yandex_music.oauth
```
Или через браузер: oauth.yandex.ru

Telegram Bot Token:
- Создайте бота через @BotFather
- Получите токен

Telegram Chat ID:
- Напишите @userinfobot — получите ваш ID

### 3. Запуск

Docker Compose (рекомендуется):

```bash
docker-compose up -d --build
```

Просмотр логов:

```bash
docker-compose logs -f
```

Только Docker:

```bash
docker build -t yandex-music-bot .
docker run -d --name yandex-music-bot --env-file .env -v bot_data:/app/data yandex-music-bot
```

Локально (Python):

```bash
pip install -r requirements.txt
python bot.py
```

## Команды бота

/start — Информация о боте
/check — Ручная проверка изменений
/status — Показать текущий статус
/stop — Остановить бота

## Конфигурация

- YANDEX_TOKEN — OAuth-токен Яндекс Музыки
- TELEGRAM_TOKEN — Токен Telegram-бота
- TELEGRAM_CHAT_ID — ID чата для уведомлений
- DATA_FILE — Путь к файлу кэша (по умолчанию /app/data/favorites_cache.json)
- CHECK_INTERVAL — Интервал проверки в секундах (по умолчанию 3600)

## Логи

Бот пишет подробные логи в stdout. В Docker Compose настроена ротация: максимум 3 файла, до 10 МБ каждый.

Просмотр:

```bash
docker-compose logs -f
```

## Пример уведомления

❌ Трек удалён из избранного:

Arctic Monkeys — Do I Wanna Know?

Ссылка: https://music.yandex.ru/album/123456/track/789012

## Технологии

- aiogram — асинхронный Telegram Bot API
- yandex-music-api — неофициальное API Яндекс Музыки
- python-dotenv — загрузка переменных из .env

## Disclaimer

Проект использует неофициальное API Яндекс Музыки и не связан с Яндексом. Используйте на свой страх и риск.
