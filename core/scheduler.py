import asyncio
from datetime import datetime, timedelta
from core.bot import bot
from services.week_service import get_week_type
from services.excel_service import filter_schedule, clear_cache
from services.redis_service import get_role, get_all_users_keys, get_groups, get_teacher_name, get_notification_status
from utils.formatters import filter_current_lesson_name

async def scheduler():
    # Initial alignment to the next minute
    now = datetime.now()
    delay = 60 - now.second
    await asyncio.sleep(delay)

    while True:
        # Start of the minute logic
        # clear_cache()  <-- REMOVED: Cache is now cleared manually via /reload_schedule
        now = datetime.now()
        w_type = get_week_type(now)
        day = now.strftime("%A")
        
        next_min_stud = (now + timedelta(minutes=2)).strftime("%H:%M")
        next_min_teach = (now + timedelta(minutes=5)).strftime("%H:%M")
        
        alerts_queue = {}
        try:
            keys = get_all_users_keys()
            
            for key in keys:
                uid = key.split(":")[1]
                
                # Check notification subscription
                if not get_notification_status(uid): continue
                
                role = get_role(uid)
                check_time = next_min_teach if role == "teacher" else next_min_stud
                groups = get_groups(uid) if role == "student" else None
                teacher = get_teacher_name(uid) if role == "teacher" else None
                
                df = filter_schedule(day=day, specific_time=check_time, role=role, groups=groups, teacher_name=teacher)
                
                for _, row in df.iterrows():
                    subj = filter_current_lesson_name(row['Предмет'], w_type)
                    if subj:
                        warn = "5 хвилин" if role == "teacher" else "1 хвилину"
                        link = str(row['Кабінет/Zoom'])
                        link_html = f"\n🔗 <a href='{link}'>ВХІД</a>" if link.lower() not in ['-', 'nan'] else f"\n🚪 {link}"
                        info_line = f"Група: {row['Група']}" if role == "teacher" else f"👨‍🏫 {row['Викладач']}"

                        msg_text = (f"🔔 <b>Через {warn}!</b>\n📚 {subj}\n<i>{info_line}</i>{link_html}")
                        if uid not in alerts_queue: alerts_queue[uid] = []
                        alerts_queue[uid].append(msg_text)
            
            for uid, messages in alerts_queue.items():
                try:
                    final_text = "\n\n➖➖➖➖➖➖\n\n".join(messages)
                    await bot.send_message(uid, final_text, parse_mode="HTML", disable_web_page_preview=True)
                except Exception as e:
                    print(f"Failed to send to {uid}: {e}")

        except Exception as e:
            print(f"Scheduler error: {e}")

        # Wait for the next minute
        now = datetime.now()
        delay = 60 - now.second
        await asyncio.sleep(delay)
        



#изменение 27.02 дима (ПОЛНОСТЬЮ заменяешь логику обхода пользователей
#Оставляешь только проверку очереди событий

import asyncio
import json
from services.redis_service import get_due_events, remove_event
from config import redis  # если у тебя клиент там


async def process_event(event_raw):
    event = json.loads(event_raw)
    user_id = event["user_id"]

    # тут вставляешь отправку уведомления
    print(f"Отправка уведомления {user_id}")


async def check_schedule():
    events = await get_due_events(redis)

    for event in events:
        await process_event(event)
        await remove_event(redis, event)


async def scheduler_loop():
    while True:
        await check_schedule()
        await asyncio.sleep(30)