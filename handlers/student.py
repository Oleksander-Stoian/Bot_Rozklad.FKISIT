from aiogram import types, F, Router
from services.redis_service import set_role, clear_groups, toggle_group, get_groups
from services.excel_service import get_all_courses, get_groups_by_course
from keyboards.builders import courses_kb, groups_kb
from keyboards.reply import main_menu

router = Router()

@router.callback_query(F.data == "role_student")
async def role_student(cb: types.CallbackQuery):
    await set_role(cb.from_user.id, "student")
    await cb.message.edit_text("🎓 Оберіть курс:", reply_markup=courses_kb(get_all_courses()))

@router.callback_query(F.data.startswith("course_"))
async def course_chosen(cb: types.CallbackQuery):
    course = cb.data.split("_")[1]
    await clear_groups(cb.from_user.id)
    groups = get_groups_by_course(course)
    await cb.message.edit_text(f"✅ {course} курс. Оберіть групи:", reply_markup=groups_kb(groups, course, []))

@router.callback_query(F.data.startswith("toggle_group_"))
async def toggle_grp(cb: types.CallbackQuery):
    try:
        # maxsplit=3 коректно обробляє назви груп з підкресленням (напр. ФКІ_21)
        # формат: toggle_group_{grp}_{course}
        parts = cb.data.split("_", 3)
        grp, course = parts[2], parts[3]
        await toggle_group(cb.from_user.id, grp)
        selected = await get_groups(cb.from_user.id)
        groups = get_groups_by_course(course)
        await cb.message.edit_reply_markup(reply_markup=groups_kb(groups, course, selected))
    except Exception:
        pass

@router.callback_query(F.data == "save_groups")
async def save(cb: types.CallbackQuery, state):
    await state.clear()
    await cb.message.delete()
    await cb.message.answer("✅ Налаштовано! Тепер користуйтесь меню знизу.", reply_markup=main_menu())