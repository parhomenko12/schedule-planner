import pdfplumber
import re
import os
from database import get_db

def parse_schedule(filepath):
    filename = os.path.basename(filepath)
    match = re.match(r'(\d{2})[._](\d{2})[._](\d{4})\.pdf', filename)
    if not match:
        raise ValueError(f"Имя файла {filename} не соответствует формату ДД_ММ_ГГГГ.pdf или ДД.ММ.ГГГГ.pdf")
    day, month, year = match.groups()
    date_str = f"{year}-{month}-{day}"

    with pdfplumber.open(filepath) as pdf:
        all_tables = []
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)

    if not all_tables:
        raise ValueError("Не удалось извлечь таблицы")

    db = get_db()

    for table in all_tables:
        if len(table) < 2:
            continue

        # Первая строка — названия групп (заголовок)
        header = table[0]
        groups = []  # список кортежей (start_index, group_name)
        i = 0
        while i < len(header):
            cell = header[i]
            if cell and re.search(r'\d', cell):
                group_name = re.sub(r'\s+', ' ', str(cell)).strip()
                if group_name == "441,442":  # игнорируем нежелательный дубликат
                    i += 3
                    continue
                groups.append((i, group_name))
                i += 3  # каждая группа занимает 3 колонки
            else:
                i += 1

        if not groups:
            continue

        # Остальные строки — пары
        for row in table[1:]:
            if not row or len(row) < 3:
                continue
            for start_idx, group_name in groups:
                if start_idx + 2 >= len(row):
                    continue
                pair_cell = row[start_idx] if start_idx < len(row) else ''
                subject_cell = row[start_idx+1] if start_idx+1 < len(row) else ''
                room_cell = row[start_idx+2] if start_idx+2 < len(row) else ''

                # Очистка
                pair_num_str = str(pair_cell).strip() if pair_cell else ''
                if not re.match(r'^\d+$', pair_num_str):
                    continue  # нет номера пары – пропускаем
                pair_num = int(pair_num_str)

                subject = re.sub(r'\s+', ' ', str(subject_cell)).strip() if subject_cell else ''
                room = re.sub(r'\s+', ' ', str(room_cell)).strip() if room_cell else ''

                # Если оба пустые – пропускаем
                if not subject and not room:
                    continue

                # Эвристика: если subject пуст, а room не пуст – возможно, предмет попал в room
                if not subject and room:
                    subject, room = room, ''
                # Если subject похож на кабинет (только цифры или спец.слова), а room похож на предмет – меняем
                def is_likely_room(text):
                    if not text:
                        return False
                    text_lower = text.lower()
                    room_keywords = ('с/з', 'к/з', 'max', 'ум', 'спортзал', '4м', '5м', '6м', '18м', '21м', '15м', '14м', '3м', '8м', '1м', '2м', '7м')
                    if text_lower in room_keywords:
                        return True
                    if re.match(r'^\d+$', text):
                        return True
                    if re.match(r'^\d+м$', text_lower):
                        return True
                    return False
                def is_likely_subject(text):
                    if not text:
                        return False
                    return re.search(r'[а-яА-Я]', text) and not is_likely_room(text)

                if is_likely_room(subject) and is_likely_subject(room):
                    subject, room = room, subject
                elif is_likely_room(subject) and not room:
                    room = subject
                    subject = ''

                # Если после всех проверок subject пуст, а room не пуст – переносим в subject
                if not subject and room:
                    subject = room
                    room = ''

                # Находим или создаём группу
                group_row = db.execute("SELECT id FROM groups WHERE name = ?", (group_name,)).fetchone()
                if not group_row:
                    db.execute("INSERT INTO groups (name) VALUES (?)", (group_name,))
                    db.commit()
                    group_row = db.execute("SELECT id FROM groups WHERE name = ?", (group_name,)).fetchone()
                group_id = group_row[0]

                # Удаляем старую запись за эту дату и пару
                db.execute("DELETE FROM timetable WHERE group_id=? AND date=? AND pair_number=?", 
                           (group_id, date_str, pair_num))
                # Вставляем новую
                db.execute('''
                    INSERT INTO timetable (group_id, date, pair_number, subject, room)
                    VALUES (?, ?, ?, ?, ?)
                ''', (group_id, date_str, pair_num, subject, room))
        db.commit()
    db.close()
    return True