from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def role_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🎓 Я Студент", callback_data="role_student")
    b.button(text="💼 Я Викладач", callback_data="role_teacher")
    b.adjust(1)
    return b.as_markup()

def courses_kb(courses):
    b = InlineKeyboardBuilder()
    for c in courses: b.button(text=f"{c} курс", callback_data=f"course_{c}")
    b.adjust(2)
    return b.as_markup()

def settings_kb(notifications_on: bool):
    b = InlineKeyboardBuilder()
    text = "🔔 Нагадування: ВВІМК" if notifications_on else "🔕 Нагадування: ВИМК"
    b.button(text=text, callback_data=f"toggle_notif_{'off' if notifications_on else 'on'}")
    b.button(text="🔄 Змінити роль", callback_data="change_role")
    b.adjust(1)
    return b.as_markup()

def groups_kb(groups, current_course, selected_groups):
    b = InlineKeyboardBuilder()
    for g in groups:
        text = f"✅ {g}" if g in selected_groups else g
        b.button(text=text, callback_data=f"toggle_group_{g}_{current_course}")
    b.adjust(3)
    b.row(types.InlineKeyboardButton(text="💾 Зберегти", callback_data="save_groups"))
    return b.as_markup()

def teachers_kb(teachers):
    b = InlineKeyboardBuilder()
    for t in teachers[:60]: b.button(text=t, callback_data=f"set_teach_{t}")
    b.adjust(2)
    return b.as_markup()
