import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
FILE_NAME = "rozklad_pro.xlsx"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Load Admin IDs from env, splitting by comma
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]

INVERT_WEEK_LOGIC = True 

BELL_SCHEDULE = [
    {"num": 1, "start": "08:30", "end": "09:50", "break": "10 хв"},
    {"num": 2, "start": "10:00", "end": "11:20", "break": "25 хв (Велика)"},
    {"num": 3, "start": "11:45", "end": "13:05", "break": "10 хв"},
    {"num": 4, "start": "13:15", "end": "14:35", "break": "10 хв"},
    {"num": 5, "start": "14:45", "end": "16:05", "break": "10 хв"},
    {"num": 6, "start": "16:15", "end": "17:35", "break": "10 хв"},
    {"num": 7, "start": "17:45", "end": "19:05", "break": "-"},
]
