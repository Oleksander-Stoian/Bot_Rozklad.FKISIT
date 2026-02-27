from aiogram import types, F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from services.week_service import get_week_type, week_label
from services.redis_service import get_role, get_groups, get_teacher_name
from services.excel_service import filter_schedule
from services.bell_service import is_lesson_active
from utils.formatters import format_lesson_week, get_current_lesson_info

router = Router()

ADMIN_USERNAME = "NeonTheFox"
ERROR_FOOTER = f"\n\n💬 <i>Знайшли помилку? Пишіть сюди: @{ADMIN_USERNAME}</i>"

def get_format_icon(row):
    if 'Формат' in row and str(row['Формат']).lower().strip() == 'дистанційно':
        return "💻 Дистанційно"
    return "🏫 Очно"

@router.message(F.text == "🔴 Яка зараз пара?")
async def current(msg: types.Message):
    uid = msg.from_user.id
    role = get_role(uid)
    w_type = get_week_type()
    today = datetime.now().strftime("%A")
    
    groups = get_groups(uid) if role == "student" else None
    teach = get_teacher_name(uid) if role == "teacher" else None
    df = filter_schedule(day=today, role=role, groups=groups, teacher_name=teach)
    
    if role == "student" and groups:
        header_info = f"(Групи: {', '.join(groups)})"
    elif role == "teacher" and teach:
        header_info = f"(Викладач: {teach})"
    else:
        header_info = ""

    found = []
    for _, row in df.iterrows():
        if is_lesson_active(row["Час"]):
            subj, curr_teach = get_current_lesson_info(row['Предмет'], row['Викладач'], w_type)
            if subj:
                if role == "teacher" and teach and teach not in curr_teach:
                    continue
                
                info = f"Група: {row['Група']}" if role == "teacher" else f"👨‍🏫 {curr_teach}"
                link = str(row['Кабінет/Zoom'])
                fmt_icon = get_format_icon(row)
                
                if fmt_icon == "💻 Дистанційно":
                    link_txt = f"\n🔗 Лінк: {link}" if link not in ['-', 'nan', ''] else ""
                else:
                    link_txt = f"\n🚪 Кабінет: {link}" if link not in ['-', 'nan', ''] else ""

                found.append(f"🔥 <b>ЗАРАЗ ({week_label(w_type)})</b> {header_info}:\n{fmt_icon}\n📚 {subj}\n⏰ {row['Час']}\n{info}{link_txt}")
    
    if found: 
        text = "\n\n➖ ➖ ➖\n\n".join(found) + ERROR_FOOTER
        await msg.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    else:
        df = df.sort_values("Час")
        now = datetime.now()
        next_lesson = None
        next_subj = None
        next_curr_teach = None
        
        for _, row in df.iterrows():
            try:
                lesson_start = datetime.strptime(str(row['Час']), "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                
                if lesson_start > now:
                    subj, curr_teach = get_current_lesson_info(row['Предмет'], row['Викладач'], w_type)
                    if subj:
                        if role == "teacher" and teach and teach not in curr_teach:
                            continue
                        
                        next_lesson = row
                        next_subj = subj
                        next_curr_teach = curr_teach
                        break
            except Exception:
                continue

        if next_lesson is not None:
            delta_minutes = int((lesson_start - now).total_seconds() / 60)
            info = f"Група: {next_lesson['Група']}" if role == "teacher" else f"👨‍🏫 {next_curr_teach}"
            link = str(next_lesson['Кабінет/Zoom'])
            next_fmt = get_format_icon(next_lesson)
            
            if next_fmt == "💻 Дистанційно":
                link_txt = f"\n🔗 Лінк: {link}" if link not in ['-', 'nan', ''] else ""
            else:
                link_txt = f"\n🚪 Кабінет: {link}" if link not in ['-', 'nan', ''] else ""
            
            txt = (
                f"☕ <b>Зараз перерва</b> ({week_label(w_type)}) {header_info}\n\n"
                f"🔜 Наступна пара: <b>{next_subj}</b>\n"
                f"{next_fmt}\n"
                f"⏰ Початок о <b>{next_lesson['Час']}</b> (через {delta_minutes} хв)\n"
                f"<i>{info}</i>{link_txt}"
                f"{ERROR_FOOTER}"
            )
            await msg.answer(txt, parse_mode="HTML")
        else:
            await msg.answer(f"🎉 <b>На сьогодні все!</b> ({week_label(w_type)}) {header_info}\nБільше пар немає. Відпочивайте!{ERROR_FOOTER}", parse_mode="HTML")

@router.message(F.text == "📅 Розклад на сьогодні")
async def today(msg: types.Message):
    uid = msg.from_user.id
    day = datetime.now().strftime("%A")
    w_type = get_week_type()
    role = get_role(uid)
    groups = get_groups(uid) if role == "student" else None
    teach = get_teacher_name(uid) if role == "teacher" else None
    
    df = filter_schedule(day=day, role=role, groups=groups, teacher_name=teach).sort_values("Час")
    
    if role == "student" and groups:
        header_info = f"\n👥 Групи: {', '.join(groups)}"
    elif role == "teacher" and teach:
        header_info = f"\n👤 Викладач: {teach}"
    else:
        header_info = ""

    txt = f"📅 <b>СЬОГОДНІ</b> ({week_label(w_type)}){header_info}\n"
    has = False
    for _, row in df.iterrows():
        subj, curr_teach = get_current_lesson_info(row['Предмет'], row['Викладач'], w_type)
        if subj:
            if role == "teacher" and teach and teach not in curr_teach:
                continue
            
            has = True
            info = row['Група'] if role == "teacher" else curr_teach
            fmt_icon = get_format_icon(row)
            txt += f"\n⏰ {row['Час']} — {fmt_icon} <b>{subj}</b>\n   <i>{info}</i>"
            
    if not has: txt += "\nПар немає!"
    txt += ERROR_FOOTER
    await msg.answer(txt, parse_mode="HTML")


# ==========================================
# 🗓 ІНТЕРАКТИВНИЙ РОЗКЛАД НА ТИЖДЕНЬ
# ==========================================

def generate_day_schedule_text(day_en, role, groups, teach, w_type):
    """Генерує текст розкладу на один конкретний день"""
    df = filter_schedule(role=role, groups=groups, teacher_name=teach)
    
    ua_days_full = {
        'Monday': 'Понеділок', 'Tuesday': 'Вівторок', 'Wednesday': 'Середа', 
        'Thursday': 'Четвер', 'Friday': 'П\'ятниця', 'Saturday': 'Субота'
    }
    
    if role == "student" and groups:
        header = f"👥 Групи: {', '.join(groups)}"
    elif role == "teacher" and teach:
        header = f"👤 Викладач: {teach}"
    else:
        header = ""

    txt = f"🗓 <b>РОЗКЛАД НА ТИЖДЕНЬ</b>\n📌 {week_label(w_type)}\n{header}\n\n🔰 <b>{ua_days_full.get(day_en, day_en)}</b>:\n"
    
    d_df = df[df['День'] == day_en].sort_values("Час")
    if d_df.empty:
        txt += "\n🎉 Пар немає! Відпочивайте!\n"
    else:
        lessons = []
        for _, row in d_df.iterrows():
            lesson_fmt = row['Формат'] if 'Формат' in row else 'Аудиторія'
            entry = format_lesson_week(row['Предмет'], row['Викладач'], row['Кабінет/Zoom'], w_type, row['Група'], lesson_fmt)
            if entry: 
                lessons.append(f"⏰ <b>{row['Час']}</b>\n{entry}")
        
        if lessons:
            txt += "\n" + "\n\n".join(lessons) + "\n"
        else:
            txt += "\n🎉 Пар немає! Відпочивайте!\n"
            
    txt += ERROR_FOOTER
    return txt

def get_week_kb(current_day=None):
    """Створює клавіатуру з днями тижня (2 ряди по 3 кнопки)"""
    days = {
        'Monday': 'ПН', 'Tuesday': 'ВТ', 'Wednesday': 'СР', 
        'Thursday': 'ЧТ', 'Friday': 'ПТ', 'Saturday': 'СБ'
    }
    buttons = []
    for en_day, ua_day in days.items():
        # Додаємо візуальний маркер (крапку або галочку) для обраного дня
        text = f"🔹 {ua_day}" if en_day == current_day else ua_day
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"wd_{en_day}"))
    
    # Розбиваємо на 2 ряди по 3 кнопки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        buttons[0:3],
        buttons[3:6]
    ])
    return kb

@router.message(F.text == "🗓 Розклад на тиждень")
async def week_cmd(msg: types.Message):
    uid = msg.from_user.id
    role = get_role(uid)
    w_type = get_week_type()
    
    groups = get_groups(uid) if role == "student" else None
    teach = get_teacher_name(uid) if role == "teacher" else None
    
    # За замовчуванням показуємо сьогоднішній день. Якщо неділя - показуємо понеділок.
    today = datetime.now().strftime("%A")
    if today not in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
        today = 'Monday'
        
    text = generate_day_schedule_text(today, role, groups, teach, w_type)
    await msg.answer(text, reply_markup=get_week_kb(today), parse_mode="HTML")

@router.callback_query(F.data.startswith("wd_"))
async def process_wkday(cb: types.CallbackQuery):
    day_en = cb.data.split("_")[1] # Витягуємо день, наприклад 'Monday'
    uid = cb.from_user.id
    role = get_role(uid)
    w_type = get_week_type()
    
    groups = get_groups(uid) if role == "student" else None
    teach = get_teacher_name(uid) if role == "teacher" else None
    
    text = generate_day_schedule_text(day_en, role, groups, teach, w_type)
    
    try:
        # Оновлюємо текст і переміщуємо маркер 🔹 на нову кнопку
        await cb.message.edit_text(text, reply_markup=get_week_kb(day_en), parse_mode="HTML")
    except Exception:
        pass # Захист від помилки, якщо користувач двічі клікнув на один і той самий день
        
    await cb.answer() # Прибираємо "годинник" завантаження на кнопці