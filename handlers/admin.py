from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_IDS
from services.excel_service import clear_cache

router = Router()

@router.message(Command("reload_schedule"))
async def reload_schedule(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return # Ignore non-admins
    
    clear_cache()
    await msg.answer("✅ Розклад успішно оновлено (кеш очищено)!")
