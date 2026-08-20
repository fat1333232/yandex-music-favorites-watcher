# bot.py
import asyncio
import json
import logging
import os
import signal
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from yandex_music import ClientAsync
from dotenv import load_dotenv

# === Загрузка .env ===
load_dotenv()

# === КОНФИГ из env ===
YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
DATA_FILE = Path(os.getenv("DATA_FILE", "favorites_cache.json"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))

# === Логирование ===
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# === Инициализация ===
yandex_client = ClientAsync(YANDEX_TOKEN)
telegram_bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# === Флаг остановки ===
stop_event = asyncio.Event()

# === Хелперы ===
async def load_cache() -> set[tuple[int, int]]:
    logger.debug(f"Загрузка кэша из {DATA_FILE}")
    if not DATA_FILE.exists():
        logger.debug("Кэш не найден, создаём пустой")
        return set()
    data = json.loads(DATA_FILE.read_text())
    logger.debug(f"Загружено {len(data)} треков из кэша")
    return {(t["track_id"], t["album_id"]) for t in data}

async def save_cache(tracks: list[dict]):
    logger.debug(f"Сохранение {len(tracks)} треков в кэш")
    DATA_FILE.write_text(json.dumps(tracks, ensure_ascii=False, indent=2))
    logger.debug("Кэш успешно сохранён")

async def get_liked_tracks() -> list[dict]:
    logger.debug("Получение списка лайкнутых треков...")
    
    status = await yandex_client.account_status()
    uid = status.account.uid
    logger.debug(f"UID пользователя: {uid}")

    likes = await yandex_client.users_likes_tracks(uid)
    logger.debug(f"Получено {len(likes.tracks)} лайкнутых треков")
    
    track_ids = [f"{t.id}:{t.album_id}" for t in likes.tracks]
    logger.debug(f"Track IDs: {track_ids[:5]}... (показано первые 5)")

    if not track_ids:
        logger.warning("Список лайкнутых треков пуст")
        return []

    all_tracks = []
    for i in range(0, len(track_ids), 200):
        batch = track_ids[i:i+200]
        logger.debug(f"Загрузка метаданных для пачки {i//200 + 1} ({len(batch)} треков)")
        tracks = await yandex_client.tracks(batch)
        logger.debug(f"Получено {len(tracks)} треков из API")
        
        for t in tracks:
            track_data = {
                "track_id": t.id,
                "album_id": t.albums[0].id if t.albums else None,
                "title": t.title,
                "artists": ", ".join(a.name for a in t.artists),
                "link": f"https://music.yandex.ru/album/{t.albums[0].id if t.albums else '0'}/track/{t.id}"
            }
            all_tracks.append(track_data)
            logger.debug(f"  Трек: {track_data['artists']} — {track_data['title']}")

    logger.info(f"Всего загружено {len(all_tracks)} треков с метаданными")
    return all_tracks

async def check_changes():
    logger.info("=== Начало проверки изменений ===")
    
    old_cache = await load_cache()
    logger.debug(f"Старый кэш: {len(old_cache)} треков")
    
    new_tracks = await get_liked_tracks()
    new_cache = {(t["track_id"], t["album_id"]) for t in new_tracks}
    logger.debug(f"Новый кэш: {len(new_cache)} треков")

    removed = old_cache - new_cache
    added = new_cache - old_cache
    
    logger.info(f"Удалено треков: {len(removed)}")
    logger.info(f"Добавлено треков: {len(added)}")

    if removed:
        logger.warning(f"Обнаружено {len(removed)} удалённых треков!")
        old_tracks_data = json.loads(DATA_FILE.read_text()) if DATA_FILE.exists() else []
        old_map = {(t["track_id"], t["album_id"]): t for t in old_tracks_data}

        for track_id, album_id in removed:
            track_info = old_map.get((track_id, album_id), {})
            title = track_info.get("title", "Неизвестно")
            artists = track_info.get("artists", "Неизвестно")
            link = track_info.get("link", "")

            msg = f"❌ Трек удалён из избранного:\n\n🎵 {artists} — {title}\n\n🔗 {link}"
            logger.info(f"Отправка уведомления: {artists} — {title}")
            
            try:
                await telegram_bot.send_message(
                    chat_id=YOUR_TELEGRAM_CHAT_ID,
                    text=msg
                )
                logger.debug("Уведомление успешно отправлено")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления: {e}")
    else:
        logger.debug("Удалённых треков не обнаружено")

    await save_cache(new_tracks)
    logger.info("=== Проверка завершена ===\n")

# === Команды бота ===
@dp.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"Пользователь {message.from_user.id} отправил /start")
    await message.answer(
        "Бот запущен. Я буду уведомлять, если трек пропадёт из избранного Яндекс Музыки.\n\n"
        "Команды:\n"
        "/check — проверить вручную\n"
        "/stop — остановить бота\n"
        "/status — показать статус"
    )

@dp.message(Command("check"))
async def cmd_check(message: Message):
    logger.info(f"Пользователь {message.from_user.id} отправил /check")
    await message.answer("Запускаю проверку...")
    try:
        await check_changes()
        await message.answer("Проверка завершена.")
    except Exception as e:
        logger.error(f"Ошибка при ручной проверке: {e}")
        await message.answer(f"Ошибка: {e}")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    logger.info(f"Пользователь {message.from_user.id} отправил /status")
    cache_size = len(await load_cache())
    await message.answer(f"📊 Статус:\n\nВ кэше: {cache_size} треков\nИнтервал: {CHECK_INTERVAL} сек\nСтатус: {'Работает' if not stop_event.is_set() else 'Остановлен'}")

@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    logger.info(f"Пользователь {message.from_user.id} отправил /stop")
    await message.answer("Останавливаю бота...")
    stop_event.set()

# === Основной цикл ===
async def periodic_check():
    logger.info("Запуск цикла периодической проверки")
    iteration = 0
    
    while not stop_event.is_set():
        iteration += 1
        logger.debug(f"=== Итерация {iteration} ===")
        
        try:
            logger.debug(f"Ожидание {CHECK_INTERVAL} секунд до следующей проверки...")
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=CHECK_INTERVAL
            )
            logger.info("Получен сигнал остановки, завершение цикла")
            break
            
        except asyncio.TimeoutError:
            logger.debug("Таймаут истёк, начинаю проверку")
            try:
                await check_changes()
            except Exception as e:
                logger.error(f"Ошибка при проверке: {e}", exc_info=True)

    logger.info("Цикл периодической проверки завершён")

async def main():
    logger.info("Запуск бота...")
    logger.info(f"DATA_FILE = {DATA_FILE}")
    logger.info(f"CHECK_INTERVAL = {CHECK_INTERVAL} сек")
    
    # Создаём задачи
    polling_task = asyncio.create_task(dp.start_polling(telegram_bot))
    check_task = asyncio.create_task(periodic_check())
    
    try:
        # Ждём завершения любой из задач
        done, pending = await asyncio.wait(
            [polling_task, check_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Если одна задача завершилась — отменяем остальные
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt")
        stop_event.set()
        polling_task.cancel()
        check_task.cancel()
    finally:
        logger.info("Закрытие соединения с Telegram...")
        await telegram_bot.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())