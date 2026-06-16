import asyncio
import logging
import sys
import redis
from core.bot import bot, dp
from core.scheduler import scheduler
from handlers import start, student, teacher, schedule, bells, admin
from config import REDIS_HOST, REDIS_PORT
from services.excel_service import clear_cache
from services.redis_service import consume_schedule_reload


async def schedule_watcher():
    """Опитує прапорець schedule:reload (його ставить веб-панель після збереження)
    і скидає кеш розкладу — щоб зміни застосовувались без ручного /reload_schedule."""
    while True:
        try:
            if await consume_schedule_reload():
                clear_cache()
                logging.info("Розклад оновлено з веб-панелі — кеш очищено.")
        except Exception as e:
            logging.warning(f"schedule_watcher: {e}")
        await asyncio.sleep(5)


async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Перевірка Redis перед запуском
    max_retries = 5
    for attempt in range(max_retries):
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=2)
            r.ping()
            print("✅ Підключення до Redis успішне!")
            break
        except Exception as e:
            print(f"⏳ Очікування Redis (спроба {attempt + 1}/{max_retries})...")
            if attempt == max_retries - 1:
                print("\n❌ ПОМИЛКА: Не вдалося підключитися до Redis!")
                print(f"Деталі: {e}")
                print(f"Переконайтеся, що Redis-сервер запущений на {REDIS_HOST}:{REDIS_PORT}")
                return
            await asyncio.sleep(2)

    print("🤖 Бот запущено (Full Fix)!")
    
    # Реєстрація роутерів
    dp.include_routers(
        admin.router, # Admin commands first
        start.router,
        student.router,
        teacher.router,
        schedule.router,
        bells.router
    )
    
    asyncio.create_task(scheduler())
    asyncio.create_task(schedule_watcher())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

