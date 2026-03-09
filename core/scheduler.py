import asyncio
from datetime import datetime, timedelta
from core.bot import bot
from services.week_service import get_week_type
from services.excel_service import filter_schedule
from services.redis_service import get_users_in_group, get_users_for_teacher, get_notification_status
from utils.formatters import filter_current_lesson_name

async def scheduler():
    # Initial alignment to the next minute
    now = datetime.now()
    delay = 60 - now.second
    await asyncio.sleep(delay)

    while True:
        now = datetime.now()
        w_type = get_week_type(now)
        day = now.strftime("%A")
        
        next_min_stud = (now + timedelta(minutes=2)).strftime("%H:%M")
        next_min_teach = (now + timedelta(minutes=5)).strftime("%H:%M")
        
        alerts_queue = {}
        try:
            # 1. Fetch schedule ONLY ONCE per minute
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
                    
                    # Generate message
                    link = str(row.get('Кабінет/Zoom', '-'))
                    link_html = f"\n🔗 <a href='{link}'>ВХІД</a>" if link.lower() not in ['-', 'nan', ''] else f"\n🚪 {link}"
                    info_line = f"👨‍🏫 {row.get('Викладач', '-')}"
                    msg_text = f"🔔 <b>Через 1 хвилину!</b>\n📚 {subj}\n<i>{info_line}</i>{link_html}"
                    
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
                    
                    link = str(row.get('Кабінет/Zoom', '-'))
                    link_html = f"\n🔗 <a href='{link}'>ВХІД</a>" if link.lower() not in ['-', 'nan', ''] else f"\n🚪 {link}"
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
                    print(f"Failed to send to {uid}: {e}")

        except Exception as e:
            print(f"Scheduler error: {e}")

        # Wait for the next minute
        now = datetime.now()
        delay = 60 - now.second
        await asyncio.sleep(delay)
        



