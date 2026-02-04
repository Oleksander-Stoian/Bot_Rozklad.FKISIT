import asyncio
import logging
import sys
import redis
from core.bot import bot, dp
from core.scheduler import scheduler
from handlers import start, student, teacher, schedule, bells, admin
from config import REDIS_HOST, REDIS_PORT

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Перевірка Redis перед запуском
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=1)
        r.ping()
        print("✅ Підключення до Redis успішне!")
    except Exception as e:
        print("\n❌ ПОМИЛКА: Не вдалося підключитися до Redis!")
        print(f"Деталі: {e}")
        print(f"Переконайтеся, що Redis-сервер запущений на {REDIS_HOST}:{REDIS_PORT}")
        print("Запустіть redis-server.exe і спробуйте знову.\n")
        return

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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
