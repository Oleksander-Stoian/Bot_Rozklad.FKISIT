import pandas as pd
import re

def parse_college_schedule(input_file="raw_rozklad.xlsx", output_file="rozklad_pro.xlsx"):
    print(f"🔄 Читаємо файл {input_file}...")
    try:
        xls = pd.ExcelFile(input_file)
    except FileNotFoundError:
        print(f"❌ ПОМИЛКА: Файл {input_file} не знайдено! Покладіть його поруч зі скриптом.")
        return

    days_map = {
        "ПОНЕДІЛОК": "Monday", "ВІВТОРОК": "Tuesday", "СЕРЕДА": "Wednesday",
        "ЧЕТВЕР": "Thursday", "П'ЯТНИЦЯ": "Friday", "СУБОТА": "Saturday"
    }

    schedule_dict = {}

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        current_day = "Monday"
        for ua_day, en_day in days_map.items():
            if ua_day in sheet_name.upper():
                current_day = en_day
                break
        for r in range(min(20, len(df))):
            for c in range(min(5, len(df.columns))):
                val = str(df.iloc[r, c]).upper().strip()
                for ua_day, en_day in days_map.items():
                    if ua_day in val:
                        current_day = en_day
                        break

        table_start_rows = []
        for r in range(len(df)):
            for c in range(min(5, len(df.columns))):
                if "години" in str(df.iloc[r, c]).lower():
                    table_start_rows.append(r)
                    break
        
        for i, time_row_idx in enumerate(table_start_rows):
            end_row = table_start_rows[i+1] if i + 1 < len(table_start_rows) else len(df)
            
            group_row_idx = -1
            group_col_idx = -1
            for r in range(time_row_idx, min(time_row_idx + 5, end_row)):
                for c in range(min(5, len(df.columns))):
                    if "група" in str(df.iloc[r, c]).lower():
                        group_row_idx = r
                        group_col_idx = c
                        break
                if group_row_idx != -1: break
            
            if group_row_idx == -1: continue
            
            pair_cols = {}
            for c in range(group_col_idx + 1, len(df.columns)):
                time_val = str(df.iloc[time_row_idx, c]).strip()
                m = re.search(r'(\d{1,2}:\d{2})', time_val)
                if m: pair_cols[c] = m.group(1)
            
            if not pair_cols: continue

            current_group_str = ""
            rows_since_group = 0

            for r in range(group_row_idx + 1, end_row):
                cell_g = str(df.iloc[r, group_col_idx]).strip()
                if cell_g.endswith('.0'): cell_g = cell_g[:-2]
                
                is_new_group = False
                
                if cell_g and cell_g.lower() != 'nan':
                    # СУВОРА ПЕРЕВІРКА ГРУПИ (щоб відсіяти дати "12 грудня", "ІІ семестр" і т.д.)
                    if len(cell_g) <= 15 and "2025" not in cell_g and "2026" not in cell_g and bool(re.match(r'^[\d\s/\-,]+[А-ЯІЇЄa-zA-Z]*$', cell_g)):
                        current_group_str = cell_g
                        is_new_group = True
                        rows_since_group = 0 
                    else:
                        current_group_str = "" 
                        continue
                else:
                    rows_since_group += 1
                    if rows_since_group == 1 and current_group_str:
                        is_new_group = False 
                    else:
                        current_group_str = "" 
                        continue

                # Розділяємо можливі об'єднані групи (напр. 141/181)
                groups = [g.strip() for g in current_group_str.replace(',', '/').split('/') if g.strip()]
                
                for group in groups:
                    current_course = group[0] if group and group[0].isdigit() else "1"
                    
                    for col_idx, time_str in pair_cols.items():
                        cell_val = str(df.iloc[r, col_idx]).strip()
                        if cell_val in ['nan', '', '-', 'None']: continue
                        
                        # Розширений фільтр сміття
                        if any(trash in cell_val.upper() for trash in ["ЦИБЕНКО", "ЛЕСНЯК", "МАШИНА", "_____", "ЗАТВЕРДЖУЮ", "ПОГОДЖЕНО", "АУДИТОРНОЮ ФОРМОЮ", "ДИСТАНЦІЙНОЮ ФОРМОЮ", "ДЕНЬ САМОРОЗВИТКУ"]):
                            continue

                        cell_val = re.sub(r'^\d{1,2}:\d{2}\s*', '', cell_val).strip()
                        cell_val = re.sub(r'\s+', ' ', cell_val).strip()
                        
                        format_type = "Дистанційно"
                        room = "-"
                        
                        room_match = re.search(r'\((?:ауд\.?|каб\.?|а\.)\s*([^)]+)\)', cell_val, re.IGNORECASE)
                        if room_match:
                            format_type = "Аудиторія"
                            room = room_match.group(1).strip()
                            room = re.sub(r'\s+', ' ', room) 
                            cell_val = cell_val[:room_match.start()] + cell_val[room_match.end():]
                            cell_val = cell_val.strip()
                        
                        parts = [p.strip() for p in cell_val.split(',') if p.strip()]
                        if len(parts) >= 2:
                            teacher = parts[-1]
                            subject = ", ".join(parts[:-1])
                        else:
                            subject = cell_val
                            teacher = "-"
                        
                        subject = re.sub(r'\s+', ' ', subject).strip()
                        teacher = re.sub(r'\s+', ' ', teacher).strip()
                            
                        key = (current_course, group, current_day, time_str)
                        
                        if is_new_group:
                            schedule_dict[key] = {
                                "Курс": current_course, "Група": group, "День": current_day,
                                "Час": time_str, "Предмет": subject, 
                                "Викладач": teacher, "Кабінет/Zoom": room, "Формат": format_type
                            }
                        else:
                            if key in schedule_dict:
                                prev = schedule_dict[key]
                                if prev["Предмет"] != subject or prev["Викладач"] != teacher:
                                    prev["Предмет"] = f"{prev['Предмет']} // {subject}"
                                    prev["Викладач"] = f"{prev['Викладач']} // {teacher}"
                                    if prev["Формат"] != format_type or prev["Кабінет/Zoom"] != room:
                                        prev["Кабінет/Zoom"] = f"{prev['Кабінет/Zoom']} // {room}"
                            else:
                                schedule_dict[key] = {
                                    "Курс": current_course, "Група": group, "День": current_day,
                                    "Час": time_str, "Предмет": f"- // {subject}", 
                                    "Викладач": f"- // {teacher}", "Кабінет/Zoom": room, "Формат": format_type
                                }

    parsed_data = list(schedule_dict.values())
    
    if not parsed_data:
        print("❌ Не вдалося знайти жодної пари. Перевірте формат файлу.")
        return

    res_df = pd.DataFrame(parsed_data)
    res_df.to_excel(output_file, index=False)
    print(f"✅ МАГІЯ ВІДБУЛАСЯ! Збережено у {output_file}.")
    print(f"📊 Знайдено {len(parsed_data)} унікальних пар.")

if __name__ == "__main__":
    parse_college_schedule("raw_rozklad.xlsx", "rozklad_pro.xlsx")