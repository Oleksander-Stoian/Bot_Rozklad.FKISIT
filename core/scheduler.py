import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from core.bot import bot
from services.week_service import get_week_type
from services.excel_service import filter_schedule
from services.redis_service import get_users_in_group, get_users_for_teacher, get_notification_status
from utils.formatters import filter_current_lesson_name

logger = logging.getLogger(__name__)

KYIV_TZ = ZoneInfo("Europe/Kyiv")

def _build_link_html(raw_value: str) -> str:
    """
    Формує рядок з посиланням або кабінетом.
    Посилання створюється лише якщо значення є URL (починається з http:// або https://).
    """
    val = str(raw_value).strip()
    if val.lower() in ['-', 'nan', '']:
        return ""
    if val.startswith("http://") or val.startswith("https://"):
        return f"\n🔗 <a href='{val}'>ВХІД</a>"
    return f"\n🚪 Кабінет: {val}"

async def scheduler():
    # Initial alignment to the next minute
    now = datetime.now(KYIV_TZ)
    delay = 60 - now.second
    await asyncio.sleep(delay)

    while True:
        now = datetime.now(KYIV_TZ)
        w_type = get_week_type(now)
        day = now.strftime("%A")
        
        # Студентам — попередження за 2 хвилини
        next_min_stud = (now + timedelta(minutes=2)).strftime("%H:%M")
        # Викладачам — попередження за 5 хвилин
        next_min_teach = (now + timedelta(minutes=5)).strftime("%H:%M")
        
        alerts_queue = {}
        try:
            # 1. Fetch schedule ONLY ONCE per minute (role=None → повертає всі рядки дня)
            df = filter_schedule(day=day)
            
            if not df.empty:
                # 2. Process STUDENT notifications (2 min warning)
                df_stud = df[df['Час'] == next_min_stud]
                for _, row in df_stud.iterrows():
                    group = row.get('Група')
                    if not group or str(group) in ['nan', '-']: continue
                    
                    subj = filter_current_lesson_name(row['Предмет'], w_type)
                    if not subj: continue
                    
                    users = await get_users_in_group(group)
                    
                    link_html = _build_link_html(row.get('Кабінет/Zoom', '-'))
                    info_line = f"👨‍🏫 {row.get('Викладач', '-')}"
                    msg_text = f"🔔 <b>Через 2 хвилини!</b>\n📚 {subj}\n<i>{info_line}</i>{link_html}"
                    
                    for uid in users:
                        if not await get_notification_status(uid): continue
                        if uid not in alerts_queue: alerts_queue[uid] = []
                        alerts_queue[uid].append(msg_text)
                
                # 3. Process TEACHER notifications (5 min warning)
                df_teach = df[df['Час'] == next_min_teach]
                for _, row in df_teach.iterrows():
                    teacher_raw = row.get('Викладач')
                    if not teacher_raw or str(teacher_raw) in ['nan', '-']: continue
                    
                    subj = filter_current_lesson_name(row['Предмет'], w_type)
                    if not subj: continue
                    
                    # Handle multiple teachers (e.g. Teacher1 // Teacher2)
                    teachers = [t.strip() for t in str(teacher_raw).split("//") if len(t.strip()) > 2]
                    
                    link_html = _build_link_html(row.get('Кабінет/Zoom', '-'))
                    info_line = f"Група: {row.get('Група', '-')}"
                    msg_text = f"🔔 <b>Через 5 хвилин!</b>\n📚 {subj}\n<i>{info_line}</i>{link_html}"
                    
                    for t_name in teachers:
                        users = await get_users_for_teacher(t_name)
                        for uid in users:
                            if not await get_notification_status(uid): continue
                            if uid not in alerts_queue: alerts_queue[uid] = []
                            alerts_queue[uid].append(msg_text)

            # 4. Dispatch messages
            for uid, messages in alerts_queue.items():
                try:
                    final_text = "\n\n➖➖➖➖➖➖\n\n".join(messages)
                    await bot.send_message(uid, final_text, parse_mode="HTML", disable_web_page_preview=True)
                except Exception as e:
                    logger.warning(f"Не вдалося надіслати повідомлення {uid}: {e}")

        except Exception as e:
            logger.error(f"Помилка планувальника: {e}")

        # Wait for the next minute
        now = datetime.now(KYIV_TZ)
        delay = 60 - now.second
        await asyncio.sleep(delay)
