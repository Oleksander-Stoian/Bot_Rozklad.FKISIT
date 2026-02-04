from datetime import datetime, timedelta
from config import BELL_SCHEDULE

def is_lesson_active(start_time_str):
    try:
        now = datetime.now()
        end_time_str = None
        for item in BELL_SCHEDULE:
            if item['start'] == start_time_str:
                end_time_str = item['end']
                break
        
        start = datetime.strptime(start_time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        if end_time_str:
            end = datetime.strptime(end_time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        else:
            end = start + timedelta(minutes=80) 
        
        return start <= now <= end
    except: return False
