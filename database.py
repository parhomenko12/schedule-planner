import sqlite3
import os

DB_NAME = 'schedule.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS updates (
                id INTEGER PRIMARY KEY,
                last_update TEXT,
                message TEXT
            )
        ''')
        # Добавляем запись об обновлении, если её нет
        conn.execute("INSERT OR IGNORE INTO updates (id, last_update, message) VALUES (1, '', '')")
        # Тестовые группы (если нужно)
        conn.execute("INSERT OR IGNORE INTO groups (name) VALUES ('101')")
        conn.execute("INSERT OR IGNORE INTO groups (name) VALUES ('441, 442')")
        conn.execute("INSERT OR IGNORE INTO groups (name) VALUES ('100/1')")
        conn.commit()

if __name__ == '__main__':
    init_db()
    print("База данных и таблицы созданы.")