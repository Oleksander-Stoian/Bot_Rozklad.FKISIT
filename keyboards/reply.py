from aiogram.utils.keyboard import ReplyKeyboardBuilder

def main_menu():
    b = ReplyKeyboardBuilder()
    b.button(text="⚡ Зараз")
    b.button(text="📅 Сьогодні")
    b.button(text="🗓 На тиждень")
    b.button(text="🕐 Розклад дзвінків")
    b.button(text="⚙️ Налаштування")

    # Схема кнопок:
    # [         ⚡ Зараз         ]
    # [ 📅 Сьогодні | 🗓 На тиждень ]
    # [  🕐 Розклад дзвінків     ]
    # [    ⚙️ Налаштування       ]
    b.adjust(1, 2, 1, 1)
    return b.as_markup(resize_keyboard=True)