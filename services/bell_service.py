import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import BELL_SCHEDULE

logger = logging.getLogger(__name__)

KYIV_TZ = ZoneInfo("Europe/Kyiv")

def is_lesson_active(start_time_str):
    try:
        now = datetime.now(KYIV_TZ)
        end_time_str = None
        for item in BELL_SCHEDULE:
            if item['start'] == start_time_str:
                end_time_str = item['end']
                break
        
        start = datetime.strptime(start_time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=KYIV_TZ
        )
        if end_time_str:
            end = datetime.strptime(end_time_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day, tzinfo=KYIV_TZ
            )
        else:
            end = start + timedelta(minutes=80) 
        
        return start <= now <= end
    except Exception as e:
        logger.error(f"Помилка у is_lesson_active({start_time_str!r}): {e}")
        return False
