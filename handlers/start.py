from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
from core.states import Form
from keyboards.builders import role_kb, settings_kb
from services.redis_service import get_notification_status, set_notification_status

router = Router()

ONBOARDING_TEXT = (
    "👋 <b>Вітаємо!</b> Я — бот розкладу ФКІСТ.\n\n"
    "Можу показати:\n"
    "• Яка пара зараз ⚡\n"
    "• Розклад на сьогодні та тиждень 📅\n"
    "• Нагадати перед парою 🔔\n\n"
    "Будь ласка, оберіть Вашу роль:"
)

@router.message(Command("start"))
async def cmd_start(msg: types.Message, state):
    await state.clear()
    await msg.answer(ONBOARDING_TEXT, parse_mode="HTML", reply_markup=role_kb())

@router.message(F.text == "⚙️ Налаштування")
async def settings(msg: types.Message):
    uid = msg.from_user.id
    notif_on = await get_notification_status(uid)
    await msg.answer("⚙️ <b>Налаштування</b>", parse_mode="HTML", reply_markup=settings_kb(notif_on))

@router.callback_query(F.data.startswith("toggle_notif_"))
async def toggle_notif(cb: types.CallbackQuery):
    action = cb.data.split("_")[2]
    uid = cb.from_user.id
    new_status = True if action == "on" else False
    await set_notification_status(uid, new_status)
    await cb.message.edit_reply_markup(reply_markup=settings_kb(new_status))
    await cb.answer("Налаштування збережено!")

@router.callback_query(F.data == "change_role")
async def change_role_cb(cb: types.CallbackQuery, state):
    await state.clear()
    await cb.message.edit_text(ONBOARDING_TEXT, parse_mode="HTML", reply_markup=role_kb())
    await cb.answer()

@router.callback_query(F.data == "stop_work")
async def stop_work_cb(cb: types.CallbackQuery, state):
    await state.clear()
    await cb.message.delete()
    await cb.message.answer(
        "🛑 Роботу завершено.\nЩоб розпочати знову — натисніть /start",
        reply_markup=ReplyKeyboardRemove()
    )
    await cb.answer()

@router.message(Command("status"))
async def status(msg: types.Message):
    import os, platform, socket
    from datetime import datetime
    name = os.getenv("INSTANCE_NAME") or platform.node()
    tz = datetime.now().astimezone().tzname()
    text = (
        f"Статус інстансу\n"
        f"Назва: {name}\n"
        f"Host: {platform.node()}\n"
        f"OS: {platform.platform()}\n"
        f"TZ: {tz}\n"
        f"IP: {socket.gethostbyname(socket.gethostname())}"
    )
    await msg.answer(text)
