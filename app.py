from flask import Flask, render_template, request, redirect, url_for, make_response, session, send_from_directory
import os
from werkzeug.utils import secure_filename
from database import get_db, init_db
from pdf_parser import parse_schedule
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey2026'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

with app.app_context():
    init_db()

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------- Студенческая часть -------------------
@app.route('/')
def index():
    group_id = request.cookies.get('selected_group')
    if group_id:
        db = get_db()
        group = db.execute("SELECT id FROM groups WHERE id = ?", (group_id,)).fetchone()
        if group:
            return redirect(url_for('week_schedule', group_id=group_id))
        else:
            resp = make_response(redirect(url_for('index')))
            resp.delete_cookie('selected_group')
            return resp
    db = get_db()
    groups = db.execute("SELECT * FROM groups").fetchall()
    return render_template('select_group.html', groups=groups)

@app.route('/select_group', methods=['POST'])
def select_group():
    group_id = request.form['group_id']
    resp = redirect(url_for('week_schedule', group_id=group_id))
    resp.set_cookie('selected_group', group_id, max_age=60*60*24*30)
    return resp

@app.route('/change_group')
def change_group():
    resp = redirect(url_for('index'))
    resp.delete_cookie('selected_group')
    return resp

@app.route('/schedule/<int:group_id>')
def week_schedule(group_id):
    week_offset = request.args.get('week_offset', 0, type=int)
    
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    monday = start_of_week + timedelta(days=7*week_offset)
    week_dates = []
    week_day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
    for i in range(6):
        current_date = monday + timedelta(days=i)
        week_dates.append({
            'date_str': current_date.strftime('%Y-%m-%d'),
            'display_date': current_date.strftime('%d.%m.%Y'),
            'weekday': week_day_names[i]
        })
    
    db = get_db()
    group_row = db.execute("SELECT name FROM groups WHERE id = ?", (group_id,)).fetchone()
    if not group_row:
        return redirect(url_for('index'))
    group_name = group_row['name']
    
    schedule_by_day = []
    for day_info in week_dates:
        date_str = day_info['date_str']
        rows = db.execute('''
            SELECT t.pair_number, t.subject, t.room, c.start_time, c.end_time
            FROM timetable t
            LEFT JOIN calls_schedule c ON c.day_of_week = ? AND c.pair_number = t.pair_number
            WHERE t.group_id = ? AND t.date = ?
            ORDER BY t.pair_number
        ''', (get_weekday_name(date_str), group_id, date_str)).fetchall()
        schedule_by_day.append({
            'weekday': day_info['weekday'],
            'date': day_info['display_date'],
            'pairs': rows
        })
    
    update = db.execute("SELECT last_update, message FROM updates WHERE id = 1").fetchone()
    show_notification = False
    notification_message = ''
    if update and update['last_update']:
        last_update = datetime.strptime(update['last_update'], '%Y-%m-%d %H:%M')
        if last_update.date() == datetime.now().date():
            show_notification = True
            notification_message = update['message']
    
    week_num = monday.isocalendar()[1]
    even_week = (week_num % 2 == 0)
    
    return render_template('week_schedule.html', 
                           group_id=group_id,
                           group_name=group_name,
                           schedule_by_day=schedule_by_day,
                           week_offset=week_offset,
                           even_week=even_week,
                           show_notification=show_notification,
                           notification_message=notification_message)

def get_weekday_name(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return weekdays[dt.weekday()]

# ------------------- Админка с паролем -------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == 'schedule2026':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            return "Неверный пароль. <a href='/login'>Попробовать снова</a>"
    return '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Вход для преподавателя</title>
            <link rel="stylesheet" href="/static/style.css">
            <style>
                .theme-toggle {
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    background: #7b2cbf;
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 44px;
                    height: 44px;
                    font-size: 22px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    max-width: 500px;
                    margin: 50px auto;
                    text-align: center;
                }
                input[type="password"] {
                    width: 100%;
                    padding: 12px;
                    margin: 10px 0;
                    border-radius: 12px;
                    border: 1px solid #cbb2fe;
                    font-size: 1rem;
                }
                button {
                    width: 100%;
                    padding: 12px;
                    background: #7b2cbf;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 1rem;
                    cursor: pointer;
                }
                button:hover {
                    background: #9b4dff;
                }
                body.dark .container {
                    background: #2a1a3e;
                    color: #e9d9ff;
                }
                body.dark input[type="password"] {
                    background: #2a1a3e;
                    color: #e9d9ff;
                    border-color: #5a3a8a;
                }
            </style>
            <script>
                function applyTheme() {
                    const savedTheme = localStorage.getItem('theme');
                    if (savedTheme === 'dark') document.body.classList.add('dark');
                    else document.body.classList.remove('dark');
                }
                function toggleTheme() {
                    if (document.body.classList.contains('dark')) {
                        document.body.classList.remove('dark');
                        localStorage.setItem('theme', 'light');
                    } else {
                        document.body.classList.add('dark');
                        localStorage.setItem('theme', 'dark');
                    }
                }
                window.onload = applyTheme;
            </script>
        </head>
        <body>
            <button class="theme-toggle" onclick="toggleTheme()">🌓</button>
            <div class="container">
                <h1>🔐 Вход для преподавателя</h1>
                <form method="post">
                    <input type="password" name="password" placeholder="Введите пароль" required>
                    <button type="submit">Войти</button>
                </form>
                <p style="margin-top: 20px;"><a href="/">На главную</a></p>
            </div>
        </body>
        </html>
    '''

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        files = request.files.getlist('pdf_files')
        if not files or files[0].filename == '':
            return "Файлы не выбраны"
        results = []
        db = get_db()
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                try:
                    parse_schedule(filepath)
                    results.append(f"✅ {filename} – успешно")
                except Exception as e:
                    results.append(f"❌ {filename} – ошибка: {e}")
            else:
                results.append(f"⚠️ {file.filename} – недопустимый формат (только PDF)")
        db.execute("UPDATE updates SET last_update = ?, message = ? WHERE id = 1",
                   (datetime.now().strftime('%Y-%m-%d %H:%M'), "Новое расписание загружено!"))
        db.commit()
        return render_template('admin_result.html', results=results)
    
    return render_template('admin.html')

# ------------------- PWA -------------------
@app.route('/static/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/static/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# ------------------- Это важно для Railway! -------------------
application = app

if __name__ == '__main__':
    app.run(debug=True)
