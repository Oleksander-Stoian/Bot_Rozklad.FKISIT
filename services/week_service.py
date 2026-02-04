from datetime import datetime
from zoneinfo import ZoneInfo
from config import INVERT_WEEK_LOGIC

def get_week_type(date_obj=None):
 
    # Якщо дата не передана, беремо поточний час саме в Києві
    if date_obj is None:
        date_obj = datetime.now(ZoneInfo("Europe/Kyiv"))
    
    # Отримуємо номер тижня
    week_num = date_obj.isocalendar()[1]
    is_even = (week_num % 2 == 0)

    # Логіка інверсії (якщо в config.py стоїть True, то парний тиждень стане Верхнім)
    if INVERT_WEEK_LOGIC:
        return "upper" if is_even else "lower"
    
    return "lower" if is_even else "upper"

def week_label(w_type):
    """
    Повертає гарну назву для виводу користувачу.
    """
    return "🟥 Верхній (Непарний)" if w_type == "upper" else "🟦 Нижній (Парний)"
