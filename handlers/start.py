from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
from core.states import Form
from keyboards.builders import role_kb, settings_kb
from keyboards.reply import main_menu
from services.redis_service import (
    get_notification_status, set_notification_status,
    get_role, get_groups, get_teacher_name
)

router = Router()

@router.message(Command("start"))
async def cmd_start(msg: types.Message, state):
    uid = msg.from_user.id
    role = get_role(uid)

    # Якщо роль вже є — перевіряємо що налаштування повні
    if role == "student":
        groups = get_groups(uid)
        if groups:
            await state.clear()
            await msg.answer(
                "✅ Ви вже авторизовані як студент. Користуйтесь меню.",
                reply_markup=main_menu()
            )
            return

    elif role == "teacher":
        teacher_name = get_teacher_name(uid)
        if teacher_name:
            await state.clear()
            await msg.answer(
                "✅ Ви вже авторизовані як викладач. Користуйтесь меню.",
                reply_markup=main_menu()
            )
            return

    # Якщо ролі немає або налаштування неповні — починаємо з нуля
    await state.clear()
    await msg.answer(
        "👋 <b>Вітаю!</b>\nОберіть вашу роль:",
        parse_mode="HTML",
        reply_markup=role_kb()
    )

@router.message(F.text == "⚙️ Налаштування")
async def settings(msg: types.Message):
    uid = msg.from_user.id
    notif_on = get_notification_status(uid)
    await msg.answer("⚙️ <b>Налаштування</b>", parse_mode="HTML", reply_markup=settings_kb(notif_on))

@router.callback_query(F.data.startswith("toggle_notif_"))
async def toggle_notif(cb: types.CallbackQuery):
    action = cb.data.split("_")[2]
    uid = cb.from_user.id
    new_status = action == "on"
    set_notification_status(uid, new_status)
    await cb.message.edit_reply_markup(reply_markup=settings_kb(new_status))
    await cb.answer("Налаштування збережено!")

@router.callback_query(F.data == "change_role")
async def change_role_cb(cb: types.CallbackQuery, state):
    # Очищаємо Redis і починаємо з нуля
    from services.redis_service import clear_groups
    uid = cb.from_user.id
    clear_groups(uid)
    # Скидаємо роль теж
    from services.redis_service import r
    r.delete(f"user:{uid}:role")
    r.delete(f"user:{uid}:teacher_name")

    await state.clear()
    await cb.message.answer(
        "👋 Оберіть нову роль:",
        reply_markup=role_kb()
    )
    await cb.message.delete()

@router.message(F.text == "🛑 Завершити роботу")
async def stop_work(msg: types.Message, state):
    await state.clear()
    await msg.answer(
        "🛑 Роботу завершено. Щоб почати знову, натисніть /start",
        reply_markup=ReplyKeyboardRemove()
    )