FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY bot.py .

# Создаём директорию для данных (кэш)
RUN mkdir -p /app/data

# Переменная для пути к файлу кэша
ENV DATA_FILE=/app/data/favorites_cache.json

# Запуск бота
CMD ["python", "bot.py"]