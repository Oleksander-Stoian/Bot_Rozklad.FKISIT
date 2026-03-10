from aiogram import types, F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from zoneinfo import ZoneInfo
from services.week_service import get_week_type, week_label
from services.redis_service import get_role, get_groups, get_teacher_name
from services.excel_service import filter_schedule
from services.bell_service import is_lesson_active
from utils.formatters import format_lesson_week, get_current_lesson_info
from config import ADMIN_USERNAME, BELL_SCHEDULE

router = Router()

KYIV_TZ = ZoneInfo("Europe/Kyiv")
ERROR_FOOTER = f"\n\n💬 <i>Знайшли помилку? Пишіть: @{ADMIN_USERNAME}</i>"


def _room_display(row):
    """Повертає (remote_icon, display_str) для рядка розкладу."""
    is_remote = str(row.get('Формат', '')).lower().strip() == 'дистанційно'
    room_val = str(row.get('Кабінет/Zoom', '')).strip()
    if is_remote:
        disp = f"{room_val} 💻" if room_val not in ['-', 'nan', ''] else 'Дистанційно 💻'
        return '', disp
    disp = f"ауд. {room_val}" if room_val not in ['-', 'nan', ''] else ''
    return '', disp


def _get_end_time(start_str):
    for item in BELL_SCHEDULE:
        if item['start'] == start_str:
            return item['end']
    return None


# ==========================================
# ⚡ Зараз
# ==========================================

@router.message(F.text == "⚡ Зараз")
async def current(msg: types.Message):
    uid = msg.from_user.id
    role = await get_role(uid)
    if not role:
        await msg.answer("⚠️ Спочатку оберіть Вашу роль. Натисніть /start")
        return

    w_type = get_week_type()
    now = datetime.now(KYIV_TZ)
    today = now.strftime("%A")
    groups = await get_groups(uid) if role == "student" else None
    teach = await get_teacher_name(uid) if role == "teacher" else None
    df = filter_schedule(day=today, role=role, groups=groups, teacher_name=teach)

    found = []
    for _, row in df.iterrows():
        if is_lesson_active(row["Час"]):
            subj, curr_teach = get_current_lesson_info(row['Предмет'], row['Викладач'], w_type)
            if not subj:
                continue
            if role == "teacher" and teach and teach not in curr_teach:
                continue

            info = f"Гр. {row['Група']}" if role == "teacher" else curr_teach
            remote_icon, room_disp = _room_display(row)
            end_time = _get_end_time(row['Час'])
            time_range = f"{row['Час']}–{end_time}" if end_time else row['Час']
            parts = [p for p in [info, room_disp] if p]
            sec = '  ·  '.join(parts)

            block = (
                f"⚡ <b>Зараз іде пара</b>  ·  {week_label(w_type)}\n\n"
                f"<b>{subj}</b>{remote_icon}\n"
                f"⏰ {time_range}"
                + (f"\n<i>{sec}</i>" if sec else "")
            )
            found.append(block)

    if found:
        await msg.answer("\n\n➖➖➖\n\n".join(found) + ERROR_FOOTER, parse_mode="HTML", disable_web_page_preview=True)
        return

    # Шукаємо наступну пару
    df_sorted = df.sort_values("Час")
    next_lesson = next_subj = next_curr_teach = next_lesson_start = None

    for _, row in df_sorted.iterrows():
        try:
            ls = datetime.strptime(str(row['Час']), "%H:%M").replace(
                year=now.year, month=now.month, day=now.day, tzinfo=KYIV_TZ
            )
            if ls > now:
                subj, curr_teach = get_current_lesson_info(row['Предмет'], row['Викладач'], w_type)
                if subj:
                    if role == "teacher" and teach and teach not in curr_teach:
                        continue
                    next_lesson, next_subj, next_curr_teach, next_lesson_start = row, subj, curr_teach, ls
                    break
        except Exception:
            continue

    if next_lesson is not None and next_lesson_start is not None:
        delta = int((next_lesson_start - now).total_seconds() / 60)
        info = f"Гр. {next_lesson['Група']}" if role == "teacher" else next_curr_teach
        remote_icon, room_disp = _room_display(next_lesson)
        parts = [p for p in [info, room_disp] if p]
        sec = '  ·  '.join(parts)
        txt = (
            f"☕ <b>Зараз перерва</b>  ·  {week_label(w_type)}\n\n"
            f"<b>{next_subj}</b>{remote_icon}\n"
            f"⏰ {next_lesson['Час']} (через {delta} хв)"
            + (f"\n<i>{sec}</i>" if sec else "")
            + ERROR_FOOTER
        )
        await msg.answer(txt, parse_mode="HTML")
    else:
        await msg.answer(
            f"🎉 <b>Пари закінчились!</b>\nГарного відпочинку 😊{ERROR_FOOTER}",
            parse_mode="HTML"
        )


# ==========================================
# 📅 Сьогодні
# ==========================================

@router.message(F.text == "📅 Сьогодні")
async def today(msg: types.Message):
    uid = msg.from_user.id
    role = await get_role(uid)
    if not role:
        await msg.answer("⚠️ Спочатку оберіть Вашу роль. Натисніть /start")
        return

    day = datetime.now(KYIV_TZ).strftime("%A")
    w_type = get_week_type()
    groups = await get_groups(uid) if role == "student" else None
    teach = await get_teacher_name(uid) if role == "teacher" else None
    df = filter_schedule(day=day, role=role, groups=groups, teacher_name=teach).sort_values("Час")

    who = (f"  ·  {', '.join(groups)}" if (role == "student" and groups)
           else (f"  ·  {teach}" if (role == "teacher" and teach) else ""))
    txt = f"📅 <b>Сьогодні</b>  ·  {week_label(w_type)}{who}\n"

    has = False
    for _, row in df.iterrows():
        subj, curr_teach = get_current_lesson_info(row['Предмет'], row['Викладач'], w_type)
        if not subj:
            continue
        if role == "teacher" and teach and teach not in curr_teach:
            continue
        has = True
        info = row['Група'] if role == "teacher" else curr_teach
        remote_icon, room_disp = _room_display(row)
        parts = [p for p in [info, room_disp] if p]
        sec = '  ·  '.join(parts)
        txt += f"\n<b>{row['Час']}</b>  {subj}{remote_icon}"
        if sec:
            txt += f"\n<i>{sec}</i>"

    if not has:
        txt += "\n✦ Пар немає"
    txt += ERROR_FOOTER
    await msg.answer(txt, parse_mode="HTML")


# ==========================================
# 🗓 На тиждень
# ==========================================

async def generate_day_schedule_text(day_en, role, groups, teach, w_type):
    df = filter_schedule(day=day_en, role=role, groups=groups, teacher_name=teach)

    ua_days_full = {
        'Monday': 'Понеділок', 'Tuesday': 'Вівторок', 'Wednesday': 'Середа',
        'Thursday': 'Четвер', 'Friday': 'П\'ятниця', 'Saturday': 'Субота'
    }

    who = (f"  ·  {', '.join(groups)}" if (role == "student" and groups)
           else (f"  ·  {teach}" if (role == "teacher" and teach) else ""))
    txt = f"🗓 <b>На тиждень</b>  ·  {week_label(w_type)}{who}\n\n📆 <b>{ua_days_full.get(day_en, day_en)}</b>\n"

    d_df = df.sort_values("Час")
    if d_df.empty:
        txt += "\n✦ Пар немає\n"
    else:
        lessons = []
        for _, row in d_df.iterrows():
            lesson_fmt = row.get('Формат', 'Аудиторія')
            entry = format_lesson_week(
                row['Предмет'], row['Викладач'], row['Кабінет/Zoom'],
                w_type, row['Група'], lesson_fmt, role=role
            )
            if entry:
                lessons.append(f"<b>{row['Час']}</b>  {entry}")

        if lessons:
            txt += "\n" + "\n\n".join(lessons) + "\n"
        else:
            txt += "\n✦ Пар немає\n"

    txt += ERROR_FOOTER
    return txt


def get_week_kb(current_day=None):
    days = {
        'Monday': 'ПН', 'Tuesday': 'ВТ', 'Wednesday': 'СР',
        'Thursday': 'ЧТ', 'Friday': 'ПТ', 'Saturday': 'СБ'
    }
    buttons = [
        InlineKeyboardButton(
            text=f"🔹 {ua}" if en == current_day else ua,
            callback_data=f"wd_{en}"
        )
        for en, ua in days.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[0:3], buttons[3:6]])


@router.message(F.text == "🗓 На тиждень")
async def week_cmd(msg: types.Message):
    uid = msg.from_user.id
    role = await get_role(uid)
    if not role:
        await msg.answer("⚠️ Спочатку оберіть Вашу роль. Натисніть /start")
        return

    w_type = get_week_type()
    groups = await get_groups(uid) if role == "student" else None
    teach = await get_teacher_name(uid) if role == "teacher" else None

    today = datetime.now(KYIV_TZ).strftime("%A")
    if today not in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
        today = 'Monday'

    text = await generate_day_schedule_text(today, role, groups, teach, w_type)
    await msg.answer(text, reply_markup=get_week_kb(today), parse_mode="HTML")


@router.callback_query(F.data.startswith("wd_"))
async def process_wkday(cb: types.CallbackQuery):
    day_en = cb.data.split("_")[1]
    uid = cb.from_user.id
    role = await get_role(uid)
    w_type = get_week_type()
    groups = await get_groups(uid) if role == "student" else None
    teach = await get_teacher_name(uid) if role == "teacher" else None

    text = await generate_day_schedule_text(day_en, role, groups, teach, w_type)
    try:
        await cb.message.edit_text(text, reply_markup=get_week_kb(day_en), parse_mode="HTML")
    except Exception:
        pass
    await cb.answer()