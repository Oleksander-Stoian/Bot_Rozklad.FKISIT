from aiogram import types, F, Router
from datetime import datetime
from services.week_service import get_week_type, week_label
from services.redis_service import get_role, get_groups, get_teacher_name
from services.excel_service import filter_schedule
from services.bell_service import is_lesson_active
from utils.formatters import filter_current_lesson_name, format_lesson_week

router = Router()

# ВПИШИ СЮДИ СВІЙ НІК (без @)
ADMIN_USERNAME = "NeonTheFox"
ERROR_FOOTER = f"\n\n💬 <i>Знайшли помилку? Пишіть сюди: @{ADMIN_USERNAME}</i>"

@router.message(F.text == "🔴 Яка зараз пара?")
async def current(msg: types.Message):
    uid = msg.from_user.id
    role = get_role(uid)
    w_type = get_week_type()
    today = datetime.now().strftime("%A")
    
    groups = get_groups(uid) if role == "student" else None
    teach = get_teacher_name(uid) if role == "teacher" else None
    df = filter_schedule(day=today, role=role, groups=groups, teacher_name=teach)
    
    # Header info
    if role == "student" and groups:
        header_info = f"(Групи: {', '.join(groups)})"
    elif role == "teacher" and teach:
        header_info = f"(Викладач: {teach})"
    else:
        header_info = ""

    found = []
    for _, row in df.iterrows():
        if is_lesson_active(row["Час"]):
            subj = filter_current_lesson_name(row['Предмет'], w_type)
            if subj:
                info = f"Група: {row['Група']}" if role == "teacher" else f"👨‍🏫 {row['Викладач']}"
                link = str(row['Кабінет/Zoom'])
                link_txt = f"\n🔗 {link}" if link not in ['-', 'nan'] else ""
                found.append(f"🔥 <b>ЗАРАЗ ({week_label(w_type)})</b> {header_info}:\n📚 {subj}\n⏰ {row['Час']}\n{info}{link_txt}")
    
    if found: 
        text = "\n\n➖ ➖ ➖\n\n".join(found) + ERROR_FOOTER
        await msg.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    else: 
        await msg.answer(f"☕ Зараз пар немає ({week_label(w_type)}) {header_info}.")

@router.message(F.text == "📅 Розклад на сьогодні")
async def today(msg: types.Message):
    uid = msg.from_user.id
    day = datetime.now().strftime("%A")
    w_type = get_week_type()
    role = get_role(uid)
    groups = get_groups(uid) if role == "student" else None
    teach = get_teacher_name(uid) if role == "teacher" else None
    
    df = filter_schedule(day=day, role=role, groups=groups, teacher_name=teach).sort_values("Час")
    
    # Header info
    if role == "student" and groups:
        header_info = f"\n👥 Групи: {', '.join(groups)}"
    elif role == "teacher" and teach:
        header_info = f"\n👤 Викладач: {teach}"
    else:
        header_info = ""

    txt = f"📅 <b>СЬОГОДНІ</b> ({week_label(w_type)}){header_info}\n"
    has = False
    for _, row in df.iterrows():
        subj = filter_current_lesson_name(row['Предмет'], w_type)
        if subj:
            has = True
            info = row['Група'] if role == "teacher" else row['Викладач']
            txt += f"\n⏰ {row['Час']} — <b>{subj}</b>\n   <i>{info}</i>"
            
    if not has: txt += "\nПар немає!"
    txt += ERROR_FOOTER
    await msg.answer(txt, parse_mode="HTML")

@router.message(F.text == "🗓 Розклад на тиждень")
async def week(msg: types.Message):
    uid = msg.from_user.id
    role = get_role(uid)
    w_type = get_week_type()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    ua_days = {'Monday': 'ПН', 'Tuesday': 'ВТ', 'Wednesday': 'СР', 'Thursday': 'ЧТ', 'Friday': 'ПТ', 'Saturday': 'СБ'}
    
    groups = get_groups(uid) if role == "student" else None
    teach = get_teacher_name(uid) if role == "teacher" else None
    df = filter_schedule(role=role, groups=groups, teacher_name=teach)
    
    # Header info
    if role == "student" and groups:
        header_info = f"\n👥 Групи: {', '.join(groups)}"
    elif role == "teacher" and teach:
        header_info = f"\n👤 Викладач: {teach}"
    else:
        header_info = ""

    full = f"🗓 <b>РОЗКЛАД НА ТИЖДЕНЬ</b>\n📌 {week_label(w_type)}{header_info}\n"
    for d in days:
        d_df = df[df['День'] == d].sort_values("Час")
        if d_df.empty: continue
        lessons = []
        for _, row in d_df.iterrows():
            entry = format_lesson_week(row['Предмет'], row['Викладач'], row['Кабінет/Zoom'], w_type, row['Група'])
            if entry: lessons.append(f"⏰ <b>{row['Час']}</b>\n{entry}")
        if lessons: full += f"\n🔰 <b>{ua_days[d]}</b>:\n" + "\n".join(lessons) + "\n"
    
    full += ERROR_FOOTER
    
    if len(full) > 4000:
        for x in range(0, len(full), 4000): await msg.answer(full[x:x+4000], parse_mode="HTML")
    else: await msg.answer(full, parse_mode="HTML")
