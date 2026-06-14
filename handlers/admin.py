import os
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_IDS
from services.excel_service import clear_cache
from services.redis_service import get_all_users_keys
from core.bot import bot

router = Router()

@router.message(Command("reload_schedule"))
async def reload_schedule(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return  # Ігноруємо користувачів, які не є адмінами
    clear_cache()
    await msg.answer("✅ Кеш розкладу успішно очищено у пам'яті бота!")

@router.message(Command("admin"))
async def open_admin_panel(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return  # Ігноруємо користувачів, які не є адмінами
    
    # Динамічно зчитуємо посилання на веб-панель з нашого .env файлу
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000/")
    
    # Будуємо inline-кнопку для запуску Mini App прямо всередині шторки Telegram
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="🎛 Відкрити панель управління",
                web_app=types.WebAppInfo(url=webapp_url)
            )
        ]
    ])
    
    await msg.answer(
        "👋 Вітаємо в адмін-меню Telegram Mini App!\n\n"
        "Натисніть на кнопку нижче, щоб керувати розкладом як у зручних Google-таблицях та робити фонові розсилки повідомлень:",
        reply_markup=kb
    )

@router.message(Command("broadcast"))
async def broadcast(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
        
    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        await msg.answer("❌ Будь ласка, введіть текст оголошення після команди. Наприклад:\n`/broadcast Завтра лекція на 9:00`")
        return
        
    await msg.answer("⏳ Запуск масової розсилки повідомлень з бота...")
    
    success_count = 0
    # Зчитуємо ключі користувачів з вашого Redis сервісу
    for key in get_all_users_keys():
        parts = key.split(":")
        if len(parts) >= 2:
            uid = parts[1]
            try:
                await bot.send_message(chat_id=int(uid), text=f"📢 <b>ОГОЛОШЕННЯ:</b>\n\n{text}", parse_mode="HTML")
                success_count += 1
                await asyncio.sleep(0.05)  # Anti-flood затримка для стабільності Telegram API
            except Exception:
                pass  # Пропускаємо, якщо користувач заблокував бота
                
    await msg.answer(f"✅ Масову розсилку завершено! Повідомлення отримали {success_count} користувачів.")