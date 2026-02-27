from aiogram.utils.keyboard import ReplyKeyboardBuilder

def main_menu():
    b = ReplyKeyboardBuilder()
    b.button(text="🔴 Яка зараз пара?")
    b.button(text="📅 Розклад на сьогодні")
    b.button(text="🗓 Розклад на тиждень")
    b.button(text="🔔 Дзвінки")
    b.button(text="⚙️ Налаштування")
    b.button(text="🛑 Завершити роботу")
    
    # Схема кнопок:
    # 1 рядок: Яка зараз пара?
    # 2 рядок: Сьогодні, Тиждень
    # 3 рядок: Дзвінки
    # 4 рядок: Налаштування
    # 5 рядок: Завершити роботу
    b.adjust(1, 2, 1, 1, 1)
    
    return b.as_markup(resize_keyboard=True)