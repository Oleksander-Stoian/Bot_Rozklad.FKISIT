from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_IDS
from services.excel_service import clear_cache
from services.redis_service import get_all_users_keys
from core.bot import bot
import asyncio

router = Router()

@router.message(Command("reload_schedule"))
async def reload_schedule(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return # Ignore non-admins
    
    clear_cache()
    await msg.answer("✅ Розклад успішно оновлено (кеш очищено)!")

@router.message(Command("broadcast"))
async def broadcast(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        await msg.answer("⚠️ Введіть текст розсилки.\nПриклад: `/broadcast Увага! Завтра скорочені пари.`", parse_mode="Markdown")
        return

    await msg.answer(f"🚀 Починаю розсилку...\nТекст: {text}")

    count = 0
    errors = 0
    
    # Використовуємо scan_iter (безпечний ітератор)
    keys = await get_all_users_keys()
    for key in keys:
        try:
            uid = key.split(":")[1]
            await bot.send_message(uid, f"📢 <b>ОГОЛОШЕННЯ</b>\n\n{text}", parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05) # Затримка щоб не ловити FloodWait
        except Exception as e:
            errors += 1
    
    await msg.answer(f"✅ Розсилку завершено!\nНадіслано: {count}\nПомилок: {errors}")
