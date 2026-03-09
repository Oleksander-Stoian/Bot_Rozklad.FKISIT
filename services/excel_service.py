import logging
import pandas as pd
from functools import lru_cache
from config import FILE_NAME

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def load_schedule():
    try: 
        # Зчитуємо файл як текст (dtype=str)
        df = pd.read_excel(FILE_NAME, dtype=str)
        
        # --- ФІКС ЧАСУ ---
        # Якщо в колонці "Час" є щось типу "11:45:00", ми беремо тільки перші 5 символів ("11:45")
        if 'Час' in df.columns:
            df['Час'] = df['Час'].astype(str).apply(lambda x: x[:5] if len(x) >= 5 else x)
        # -----------------
        
        return df
    except Exception as e:
        logger.error(f"Помилка при завантаженні розкладу: {e}")
        return pd.DataFrame()

def clear_cache(): load_schedule.cache_clear()

def get_all_teachers():
    df = load_schedule()
    teachers = set()
    if 'Викладач' not in df.columns: return []
    for item in df['Викладач'].dropna().unique():
        if str(item).strip() in ["-", "nan", ""]: continue
        for p in str(item).split("//"):
            if len(p.strip()) > 2: teachers.add(p.strip())
    return sorted(list(teachers))

def get_all_courses():
    df = load_schedule()
    if 'Курс' not in df.columns: return []
    return sorted(df['Курс'].dropna().unique(), key=lambda x: int(x) if str(x).isdigit() else 0)

def get_groups_by_course(course):
    df = load_schedule()
    if 'Курс' not in df.columns or 'Група' not in df.columns: return []
    return sorted(df[df['Курс'] == str(course)]['Група'].dropna().unique())

def filter_schedule(day=None, specific_time=None, role=None, groups=None, teacher_name=None):
    df = load_schedule()
    if df.empty: return pd.DataFrame()
    
    # Фільтрація за днем та часом
    if day and 'День' in df.columns: 
        df = df[df['День'] == day]
    if specific_time and 'Час' in df.columns: 
        df = df[df['Час'] == specific_time]
    
    # Якщо роль не вказана — повертаємо весь відфільтрований DataFrame
    # (використовується планувальником для пошуку всіх пар у хвилину X)
    if role is None:
        return df

    if role == "student" and groups and 'Група' in df.columns: 
        return df[df['Група'].isin(groups)]
    elif role == "teacher" and teacher_name and 'Викладач' in df.columns: 
        return df[df['Викладач'].str.contains(teacher_name, na=False, regex=False)]
    
    return pd.DataFrame()