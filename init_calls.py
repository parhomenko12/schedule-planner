import sqlite3
import os

DB_NAME = 'schedule.db'

def init_calls():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM calls_schedule")
    
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
        cursor.execute('INSERT INTO calls_schedule (day_of_week, pair_number, start_time, end_time, note) VALUES (?, ?, ?, ?, ?)',
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
        cursor.execute('INSERT INTO calls_schedule (day_of_week, pair_number, start_time, end_time, note) VALUES (?, ?, ?, ?, ?)',
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
            cursor.execute('INSERT INTO calls_schedule (day_of_week, pair_number, start_time, end_time, note) VALUES (?, ?, ?, ?, ?)',
                           (day, pair, start, end, note))
    
    conn.commit()
    conn.close()
    print("Расписание звонков успешно добавлено.")

if __name__ == '__main__':
    init_calls()
