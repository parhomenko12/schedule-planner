import sqlite3
import os

DB_NAME = 'schedule.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Таблица групп
        conn.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        # Таблица расписания
        conn.execute('''
            CREATE TABLE IF NOT EXISTS timetable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                pair_number INTEGER NOT NULL,
                subject TEXT,
                room TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        ''')
        # Таблица расписания звонков
        conn.execute('''
            CREATE TABLE IF NOT EXISTS calls_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week TEXT NOT NULL,
                pair_number INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                note TEXT
            )
        ''')
        # Таблица обновлений
        conn.execute('''
            CREATE TABLE IF NOT EXISTS updates (
                id INTEGER PRIMARY KEY,
                last_update TEXT,
                message TEXT
            )
        ''')
        # НОВАЯ ТАБЛИЦА: пользователи
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_name TEXT NOT NULL,
                first_name TEXT NOT NULL,
                middle_name TEXT,
                group_id INTEGER,
                phone TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'student',
                status TEXT DEFAULT 'active',
                photo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        ''')
        
        conn.execute("INSERT OR IGNORE INTO updates (id, last_update, message) VALUES (1, '', '')")
        conn.execute("INSERT OR IGNORE INTO groups (name) VALUES ('101')")
        conn.execute("INSERT OR IGNORE INTO groups (name) VALUES ('441, 442')")
        conn.execute("INSERT OR IGNORE INTO groups (name) VALUES ('100/1')")
        conn.commit()
    
    init_calls()

def init_calls():
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM calls_schedule").fetchone()[0]
        if count > 0:
            return
        # Понедельник
        monday = [
            (0, '08:30', '09:15', 'Разговоры о важном'),
            (1, '09:25', '10:55', '1 пара'),
            (2, '11:05', '12:35', '2 пара'),
            (3, '13:00', '14:30', '3 пара'),
            (4, '14:40', '16:10', '4 пара'),
            (5, '16:20', '17:50', '5 пара'),
            (6, '18:00', '19:30', '6 пара')
        ]
        for pair, start, end, note in monday:
            conn.execute('INSERT INTO calls_schedule (day_of_week, pair_number, start_time, end_time, note) VALUES (?, ?, ?, ?, ?)',
                         ('monday', pair, start, end, note))
        # Четверг
        thursday = [
            (0, '08:30', '10:00', 'Час куратора'),
            (1, '10:15', '11:45', '1 пара'),
            (2, '12:15', '13:45', '2 пара'),
            (3, '14:05', '15:35', '3 пара'),
            (4, '15:45', '17:15', '4 пара'),
            (5, '17:25', '18:55', '5 пара')
        ]
        for pair, start, end, note in thursday:
            conn.execute('INSERT INTO calls_schedule (day_of_week, pair_number, start_time, end_time, note) VALUES (?, ?, ?, ?, ?)',
                         ('thursday', pair, start, end, note))
        # Вторник, среда, пятница, суббота
        common = [
            (1, '08:30', '10:00', '1 пара'),
            (2, '10:15', '11:45', '2 пара'),
            (3, '12:15', '13:45', '3 пара'),
            (4, '14:05', '15:35', '4 пара'),
            (5, '15:45', '17:15', '5 пара'),
            (6, '17:25', '18:55', '6 пара')
        ]
        for day in ['tuesday', 'wednesday', 'friday', 'saturday']:
            for pair, start, end, note in common:
                conn.execute('INSERT INTO calls_schedule (day_of_week, pair_number, start_time, end_time, note) VALUES (?, ?, ?, ?, ?)',
                             (day, pair, start, end, note))
        conn.commit()

if __name__ == '__main__':
    init_db()
