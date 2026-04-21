from flask import Flask, render_template, request, redirect, url_for, make_response, session, send_from_directory
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
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

# ------------------- Главная страница -------------------
@app.route('/')
def index():
    if not session.get('user_id'):
        return render_template('welcome.html')
    return render_template('home.html', user_name=session.get('user_name'))

# ------------------- Регистрация -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    groups = db.execute("SELECT * FROM groups").fetchall()
    
    if request.method == 'POST':
        last_name = request.form['last_name']
        first_name = request.form['first_name']
        middle_name = request.form.get('middle_name', '')
        group_id = request.form['group_id']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if password != confirm:
            return "Пароли не совпадают"
        
        hashed = generate_password_hash(password)
        
        try:
            db.execute('''
                INSERT INTO users (last_name, first_name, middle_name, group_id, phone, email, password, role, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'student', 'active')
            ''', (last_name, first_name, middle_name, group_id, phone, email, hashed))
            db.commit()
            return redirect('/login')
        except Exception as e:
            return f"Ошибка: {e}. Возможно, такой email или телефон уже зарегистрирован."
    
    return render_template('register.html', groups=groups)

# ------------------- Вход для студентов -------------------
@app.route('/login', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        login_input = request.form['login']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('''
            SELECT * FROM users WHERE email = ? OR phone = ?
        ''', (login_input, login_input)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            session['user_role'] = user['role']
            session['user_group_id'] = user['group_id']
            return redirect('/')
        else:
            return "Неверный логин или пароль. <a href='/login'>Попробовать снова</a>"
    
    return render_template('login.html')

# ------------------- Выход -------------------
@app.route('/logout')
def logout_user():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    session.pop('user_group_id', None)
    return redirect('/')

# ------------------- Расписание для студентов -------------------
@app.route('/schedule')
def schedule_view():
    if not session.get('user_id'):
        return redirect('/login')
    
    group_id = session.get('user_group_id')
    if not group_id:
        return "У вас не выбрана группа. Обратитесь к администратору."
    
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
    group_name = db.execute("SELECT name FROM groups WHERE id = ?", (group_id,)).fetchone()['name']
    
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

# ------------------- Настройки -------------------
@app.route('/settings')
def settings():
    if not session.get('user_id'):
        return redirect('/login')
    return render_template('settings.html')

# ------------------- Админка (преподаватель) -------------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == 'schedule2026':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            return "Неверный пароль. <a href='/admin_login'>Попробовать снова</a>"
    return '''
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>Вход для преподавателя</title></head>
        <body>
            <form method="post">
                <input type="password" name="password" placeholder="Введите пароль" required>
                <button type="submit">Войти</button>
            </form>
        </body>
        </html>
    '''

@app.route('/logout_admin')
def logout_admin():
    session.pop('admin', None)
    return redirect('/')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
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

# ------------------- Запуск -------------------
application = app

if __name__ == '__main__':
    app.run(debug=True)
