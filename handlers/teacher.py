from aiogram import types, F, Router
from services.redis_service import set_role, set_teacher_name
from services.excel_service import get_all_teachers
from keyboards.builders import teachers_kb
from keyboards.reply import main_menu

router = Router()

@router.callback_query(F.data == "role_teacher")
async def role_teacher(cb: types.CallbackQuery):
    await set_role(cb.from_user.id, "teacher")
    await cb.message.edit_text(
        "💼 Оберіть себе зі списку:",
        reply_markup=teachers_kb(get_all_teachers(), page=0)
    )

@router.callback_query(F.data.startswith("set_teach_"))
async def set_teach(cb: types.CallbackQuery):
    name = cb.data.split("_", 2)[2]
    await set_teacher_name(cb.from_user.id, name)
    await cb.message.delete()
    await cb.message.answer(f"✅ Вітаємо, {name}!", reply_markup=main_menu())

@router.callback_query(F.data.startswith("teach_page_"))
async def teacher_page(cb: types.CallbackQuery):
    """Навігація по сторінках списку викладачів"""
    try:
        page = int(cb.data.split("_")[2])
    except (IndexError, ValueError):
        await cb.answer()
        return
    teachers = get_all_teachers()
    await cb.message.edit_reply_markup(reply_markup=teachers_kb(teachers, page=page))
    await cb.answer()

@router.callback_query(F.data == "noop")
async def noop_cb(cb: types.CallbackQuery):
    """Порожній обробник для кнопки-лічильника сторінок"""
    await cb.answer()
