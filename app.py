import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import pandas as pd
from io import BytesIO
import qrcode
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# --- НАСТРОЙКА ПОЧТЫ (ВАШИ ДАННЫЕ) ---
EMAIL_SENDER = "Yvedomlenie-scald.sad@yandex.ru"
EMAIL_PASSWORD = "bpzhkwtwimhurhkt"  # Ваш пароль приложения
EMAIL_RECIPIENT = "Yvedomlenie-scald.sad@yandex.ru"
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 587

# --- ФУНКЦИЯ ОТПРАВКИ EMAIL ---
def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = Header(subject, 'utf-8').encode()
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "✅ Email отправлен"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

# --- ПАРОЛИ ДЛЯ ВХОДА ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ ---
if "user" not in st.session_state:
    st.session_state.user = None
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = {}
if "cons_mode" not in st.session_state:
    st.session_state.cons_mode = {}
if "move_mode" not in st.session_state:
    st.session_state.move_mode = {}
if "qr_mode" not in st.session_state:
    st.session_state.qr_mode = {}
if "show_details" not in st.session_state:
    st.session_state.show_details = {}

# --- ФУНКЦИЯ ВХОДА НА ГЛАВНОЙ СТРАНИЦЕ ---
def show_login():
    st.markdown("""
        <style>
            .login-container {
                max-width: 400px;
                margin: 80px auto;
                padding: 40px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                text-align: center;
            }
            .login-container h1 {
                color: #2E7D32;
                font-size: 2rem;
                margin-bottom: 10px;
            }
            .login-container .subtitle {
                color: #666;
                margin-bottom: 30px;
            }
            .login-container .hint {
                color: #888;
                font-size: 0.85rem;
                margin-top: 15px;
                padding: 10px;
                background: #f5f5f5;
                border-radius: 8px;
            }
            .login-container .hint code {
                background: #e0e0e0;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            .stButton button {
                width: 100%;
                background-color: #4CAF50 !important;
                color: white !important;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
            }
            .stButton button:hover {
                background-color: #2E7D32 !important;
            }
            .stTextInput input {
                border-radius: 8px;
                border: 2px solid #e0e0e0;
                padding: 12px;
                font-size: 1.1rem;
                text-align: center;
                letter-spacing: 2px;
            }
            .stTextInput input:focus {
                border-color: #4CAF50;
            }
            .stAlert {
                border-radius: 8px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Контейнер входа
    with st.container():
        st.markdown("""
            <div class="login-container">
                <h1>🌿 Мой Склад</h1>
                <p class="subtitle">Введите пароль для входа</p>
        """, unsafe_allow_html=True)
        
        # Поле ввода пароля
        password = st.text_input(
            "🔑 Пароль",
            type="password",
            placeholder="Введите пароль...",
            key="login_password_main"
        )
        
        # Кнопка входа
        if st.button("🔓 Войти", use_container_width=True):
            if password in USERS:
                st.session_state.user = USERS[password]
                st.rerun()
            else:
                st.error("❌ Неверный пароль! Попробуйте еще раз.")
        
        # Подсказка
        st.markdown("""
            <div class="hint">
                💡 <strong>Для сотрудника:</strong> введите пароль <code>1111</code><br>
                🔑 <strong>Для администратора:</strong> введите пароль <code>12345</code>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# --- ПРОВЕРКА АВТОРИЗАЦИИ ---
if st.session_state.user is None:
    st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")
    show_login()
    st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

st.title("🌿 Мой Склад")
st.caption(f"👋 Добро пожаловать, {user_name}! {('🔑 Администратор' if role == 'admin' else '🔧 Сотрудник')}")

if st.sidebar.button("🚪 Выйти"):
    st.session_state.user = None
    st.rerun()

# --- PWA НАСТРОЙКИ ---
st.markdown("""
    <link rel="manifest" href="manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Мой Склад">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="apple-touch-icon" href="icon-192.png">
    <meta name="theme-color" content="#2E7D32">
""", unsafe_allow_html=True)

# --- ТЁМНАЯ ТЕМА ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "selected_room" not in st.session_state:
    st.session_state.selected_room = None
if "selected_equipment" not in st.session_state:
    st.session_state.selected_equipment = None

with st.sidebar:
    dark_mode_toggle = st.toggle("🌙 Тёмная тема", value=st.session_state.dark_mode)
    if dark_mode_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode_toggle
        st.rerun()

if st.session_state.dark_mode:
    st.markdown("""
        <style>
            .stApp { background-color: #0d1a0d; color: #d4e8d4; }
            .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
                color: #d4e8d4 !important;
            }
            .stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label {
                color: #b8d9b8 !important;
            }
            .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
                background-color: #1a2a1a !important;
                color: #d4e8d4 !important;
                border-color: #2e5a2e !important;
                border-radius: 8px;
            }
            .stButton button {
                background-color: #4CAF50 !important;
                color: #ffffff !important;
                border-radius: 8px;
                font-weight: bold;
            }
            .stButton button:hover {
                background-color: #2E7D32 !important;
                color: #ffffff !important;
            }
            .stCaption, .stCaption p { color: #9acd9a !important; }
            .stInfo, .stWarning, .stError, .stSuccess {
                background-color: #1a2a1a !important;
                color: #d4e8d4 !important;
            }
            .stAlert { background-color: #1a2a1a !important; }
            div[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0d1a0d, #1a2a1a) !important;
                border-right: 2px solid #2e5a2e !important;
            }
            div[data-testid="stSidebar"] * { color: #d4e8d4 !important; }
        </style>
    """, unsafe_allow_html=True)

# --- СОЗДАНИЕ ПАПКИ ДЛЯ ФОТО ---
if not os.path.exists("images"):
    os.makedirs("images")

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY,
                  name TEXT,
                  category TEXT,
                  location TEXT,
                  room TEXT,
                  description TEXT,
                  item_photo TEXT,
                  location_photo TEXT,
                  date_added TEXT,
                  quantity REAL,
                  unit TEXT,
                  threshold INTEGER DEFAULT 1,
                  application TEXT,
                  installed_photo TEXT,
                  equipment_id INTEGER,
                  unit_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  number TEXT,
                  date_added TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS units
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  equipment_id INTEGER,
                  date_added TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  item_id TEXT,
                  quantity REAL,
                  unit TEXT,
                  object_name TEXT,
                  user TEXT,
                  date TEXT,
                  status TEXT DEFAULT 'pending',
                  photo TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  date_added TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  item_name TEXT,
                  quantity REAL,
                  unit TEXT,
                  description TEXT,
                  photo TEXT,
                  location TEXT,
                  user TEXT,
                  date TEXT,
                  status TEXT DEFAULT 'pending',
                  admin_comment TEXT)''')
    
    c.execute("PRAGMA table_info(items)")
    columns = [col[1] for col in c.fetchall()]
    if 'application' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN application TEXT")
    if 'installed_photo' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN installed_photo TEXT")
    if 'equipment_id' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN equipment_id INTEGER")
    if 'unit_id' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN unit_id INTEGER")
    
    c.execute("PRAGMA table_info(consumption)")
    cons_columns = [col[1] for col in c.fetchall()]
    if 'status' not in cons_columns:
        c.execute("ALTER TABLE consumption ADD COLUMN status TEXT DEFAULT 'pending'")
    if 'photo' not in cons_columns:
        c.execute("ALTER TABLE consumption ADD COLUMN photo TEXT")
    
    c.execute("PRAGMA table_info(equipment)")
    eq_columns = [col[1] for col in c.fetchall()]
    if 'number' not in eq_columns:
        c.execute("ALTER TABLE equipment ADD COLUMN number TEXT")
    
    conn.commit()
    conn.close()

# --- ФУНКЦИИ ДЛЯ ЗАЯВОК НА ЗАКУПКУ ---
def add_purchase_request(item_name, quantity, unit, description, photo_path, location, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""INSERT INTO purchase_requests 
                 (item_name, quantity, unit, description, photo, location, user, date, status) 
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (item_name, quantity, unit, description, photo_path, location, user, 
               datetime.now().strftime("%Y-%m-%d %H:%M"), "pending"))
    conn.commit()
    conn.close()
    return True, "✅ Заявка отправлена!"

def get_purchase_requests(status=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM purchase_requests WHERE status = ? ORDER BY date DESC", (status,))
    else:
        c.execute("SELECT * FROM purchase_requests ORDER BY date DESC")
    results = c.fetchall()
    conn.close()
    return results

def update_purchase_request(request_id, status, admin_comment=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE purchase_requests SET status = ?, admin_comment = ? WHERE id = ?", 
              (status, admin_comment, request_id))
    conn.commit()
    conn.close()
    return True, f"✅ Заявка {status}"

def delete_purchase_request(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT photo FROM purchase_requests WHERE id = ?", (request_id,))
    result = c.fetchone()
    if result and result[0] and os.path.exists(result[0]):
        os.remove(result[0])
    c.execute("DELETE FROM purchase_requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    return True, "✅ Заявка удалена"

# --- ФУНКЦИИ РАБОТЫ С БД ---
def add_room(name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?,?)",
                  (name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True, f"Помещение '{name}' добавлено"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Помещение '{name}' уже существует"

def delete_room(room_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()

def get_rooms():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rooms ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def get_room_names():
    return [room[1] for room in get_rooms()]

def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("""INSERT INTO items 
                 (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo, equipment_id, unit_id) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path, 
               datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id))
    conn.commit()
    conn.close()
    return item_id

def update_item(item_id, name, category, location, room, description, application, equipment_id, unit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""
        UPDATE items
        SET name = ?, category = ?, location = ?, room = ?, description = ?, application = ?, equipment_id = ?, unit_id = ?
        WHERE id = ?
    """, (name, category, location, room, description, application, equipment_id, unit_id, item_id))
    conn.commit()
    conn.close()

def update_item_room(item_id, new_room):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET room = ? WHERE id = ?", (new_room, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_photo, location_photo, installed_photo FROM items WHERE id = ?", (item_id,))
    row = c.fetchone()
    if row:
        for path in row:
            if path and os.path.exists(path):
                os.remove(path)
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    c.execute("DELETE FROM consumption WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM items ORDER BY date_added DESC")
    results = c.fetchall()
    conn.close()
    return results

def get_items_by_room(room_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM items WHERE room = ? ORDER BY date_added DESC", (room_name,))
    results = c.fetchall()
    conn.close()
    return results

def get_low_stock_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM items WHERE quantity <= threshold ORDER BY quantity ASC")
    results = c.fetchall()
    conn.close()
    return results

def search_items(query, room_filter=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    query_like = f"%{query}%"
    if room_filter and room_filter != "Все помещения":
        c.execute("""
            SELECT * FROM items
            WHERE (name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ?)
            AND room = ?
        """, (query_like, query_like, query_like, query_like, room_filter))
    else:
        c.execute("""
            SELECT * FROM items
            WHERE name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ?
        """, (query_like, query_like, query_like, query_like))
    results = c.fetchall()
    conn.close()
    return results

def get_statistics():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM items")
    total_items = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM items WHERE quantity <= threshold")
    low_stock_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM equipment")
    total_equipment = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM consumption")
    total_consumption = c.fetchone()[0]
    c.execute("SELECT category, COUNT(*) FROM items GROUP BY category ORDER BY COUNT(*) DESC LIMIT 3")
    top_categories = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM purchase_requests WHERE status = 'pending'")
    pending_requests = c.fetchone()[0]
    
    conn.close()
    return total_items, low_stock_count, total_rooms, total_equipment, total_consumption, top_categories, pending_requests

def add_equipment(name, number=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment (name, number, date_added) VALUES (?,?,?)",
                  (name, number, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True, f"Техника '{name}' добавлена"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Техника '{name}' уже существует"

def delete_equipment(equipment_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
    c.execute("DELETE FROM units WHERE equipment_id = ?", (equipment_id,))
    conn.commit()
    conn.close()

def get_equipment():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def get_equipment_by_id(eq_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,))
    result = c.fetchone()
    conn.close()
    return result

def add_unit(name, equipment_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO units (name, equipment_id, date_added) VALUES (?,?,?)",
                  (name, equipment_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True, f"Агрегат '{name}' добавлен"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Агрегат '{name}' уже существует"

def delete_unit(unit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM units WHERE id = ?", (unit_id,))
    conn.commit()
    conn.close()

def get_units(equipment_id=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if equipment_id:
        c.execute("SELECT * FROM units WHERE equipment_id = ? ORDER BY name", (equipment_id,))
    else:
        c.execute("SELECT * FROM units ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def consume_item(item_id, quantity, object_name, user="Пользователь", note="", photo_path="", status="pending"):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id = ?", (item_id,))
    result = c.fetchone()
    if result is None:
        conn.close()
        return False, "Вещь не найдена"
    current_q, unit = result
    if quantity > current_q:
        conn.close()
        return False, f"Недостаточно! Есть {current_q} {unit}"
    new_q = current_q - quantity
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_q, item_id))
    c.execute("INSERT INTO consumption (item_id, quantity, unit, object_name, user, date, status, photo) VALUES (?,?,?,?,?,?,?,?)",
              (item_id, quantity, unit, object_name, user, datetime.now().strftime("%Y-%m-%d %H:%M"), status, photo_path))
    conn.commit()
    conn.close()
    return True, f"Списано {quantity} {unit} на '{object_name}'"

def approve_consumption(record_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE consumption SET status = 'confirmed' WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return True

def delete_consumption_record(record_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_id, quantity, status, photo FROM consumption WHERE id = ?", (record_id,))
    result = c.fetchone()
    if result:
        item_id, quantity, status, photo = result
        if status == "confirmed":
            c.execute("UPDATE items SET quantity = quantity + ? WHERE id = ?", (quantity, item_id))
        if photo and os.path.exists(photo):
            os.remove(photo)
    c.execute("DELETE FROM consumption WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return True

def get_all_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c
                 JOIN items i ON c.item_id = i.id
                 ORDER BY c.date DESC LIMIT 200""")
    results = c.fetchall()
    conn.close()
    return results

def get_consumption_by_equipment(eq_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c
                 JOIN items i ON c.item_id = i.id
                 WHERE c.object_name LIKE ?
                 ORDER BY c.date DESC""", (f'%{eq_name}%',))
    results = c.fetchall()
    conn.close()
    return results

def export_to_excel():
    conn = sqlite3.connect('storage.db')
    df = pd.read_sql_query("SELECT name as 'Название', category as 'Категория', location as 'Место', room as 'Помещение', description as 'Описание', application as 'Область применения', quantity as 'Количество', unit as 'Ед. изм.', threshold as 'Порог', date_added as 'Дата добавления' FROM items", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Инвентарь')
        for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            writer.sheets['Инвентарь'].column_dimensions[chr(65 + col_idx)].width = column_width + 2
    return output.getvalue()

# --- ИНИЦИАЛИЗАЦИЯ ---
init_db()

# --- ИНТЕРФЕЙС ---
total_items, low_stock_count, total_rooms, total_equipment, total_consumption, top_categories, pending_requests = get_statistics()

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("📦 Вещи", total_items)
with col2:
    st.metric("🏠 Помещения", total_rooms)
with col3:
    st.metric("⚠️ Пополнить", low_stock_count)
with col4:
    st.metric("🚜 Техника", total_equipment)
with col5:
    st.metric("📤 Списано", total_consumption)
with col6:
    if role == "admin":
        st.metric("🛒 Заявки", pending_requests, delta="Новые" if pending_requests > 0 else None)

if role == "admin":
    low_items = get_low_stock_items()
    if low_items:
        st.warning(f"⚠️ {len(low_items)} вещей требуют пополнения!")
        for item in low_items:
            st.write(f"• {item[1]} — {item[9]} {item[10]} (порог: {item[11]}) в {item[4]}")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    st.divider()
    
    st.subheader("📧 Тест Email")
    if st.button("📧 Отправить тестовое письмо", use_container_width=True):
        success, msg = send_email(
            "✅ Тестовое письмо!",
            f"Уведомления работают!\n\nПроверено: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        if success:
            st.success(msg)
        else:
            st.error(msg)
    st.divider()
    
    if role == "admin":
        st.header("➕ Добавить вещь")
        room_names = get_room_names()
        if not room_names:
            st.warning("⚠️ Сначала добавьте помещения!")
        
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Название вещи*")
            category = st.text_input("Категория")
            if room_names:
                room = st.selectbox("Помещение*", room_names)
            else:
                room = st.selectbox("Помещение*", ["— Добавьте помещение —"])
            location = st.text_input("Место*")
            description = st.text_area("Описание")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                quantity = st.number_input("Количество", min_value=0.0, step=0.5, value=1.0)
            with col2:
                unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект"])
            with col3:
                threshold = st.number_input("Порог", min_value=0, step=1, value=1)
            
            if st.form_submit_button("💾 Сохранить"):
                if name and location and room != "— Добавьте помещение —":
                    add_item(name, category, location, room, description, "", "", quantity, unit, threshold, "", "", None, None)
                    st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
                    st.rerun()
                else:
                    st.error("⚠️ Название, Помещение и Место обязательны!")
        st.divider()
    
    st.header("📤 Экспорт Excel")
    if st.button("📥 Скачать Excel", use_container_width=True):
        excel_data = export_to_excel()
        st.download_button(
            label="⬇️ Скачать",
            data=excel_data,
            file_name=f"инвентарь_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# --- ВКЛАДКИ ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔍 Поиск", 
    "📋 Все вещи", 
    "🚜 Парк", 
    "📤 Списания", 
    "📦 Остатки", 
    "🛒 Заявки", 
    "📊 Уведомления"
])

# --- ВКЛАДКА 1: ПОИСК ---
with tab1:
    st.subheader("🔍 Поиск вещей")
    
    rooms = ["Все помещения"] + get_room_names()
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("🔍 Что ищем?", placeholder="Введите название, категорию, место...", key="search_query_tab1")
    with col2:
        room_filter = st.selectbox("🏠 Помещение", rooms, key="room_filter_tab1")
    
    if search_query:
        items = search_items(search_query, room_filter)
        if items:
            st.subheader(f"📌 Найдено: {len(items)}")
            for idx, item in enumerate(items):
                unique_id = f"search_{item[0]}_{idx}"
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{item[1]}**")
                        st.caption(f"📍 {item[3]} | 🏠 {item[4]}")
                        st.caption(f"📦 {item[9]} {item[10]}")
                    with col2:
                        if role == "admin":
                            if st.button("🗑️ Удалить", key=f"del_search_{unique_id}"):
                                delete_item(item[0])
                                st.rerun()
        else:
            st.info("🌱 Ничего не найдено")

# --- ВКЛАДКА 2: ВСЕ ВЕЩИ (С РЕДАКТИРОВАНИЕМ ВНИЗУ КАРТОЧКИ) ---
with tab2:
    st.subheader("📋 Все вещи в базе данных")
    items = get_all_items()
    if not items:
        st.info("🌱 В базе пока нет вещей")
    else:
        rooms = ["Все помещения"] + get_room_names()
        room_filter = st.selectbox("🏠 Фильтр по помещению", rooms, key="filter_room_all")
        
        filtered_items = items
        if room_filter != "Все помещения":
            filtered_items = [item for item in items if item[4] == room_filter]
        
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_term = st.text_input("🔍 Поиск по названию", placeholder="Введите название...", key="search_term_all")
        with search_col2:
            st.write("")
            st.write("")
            if st.button("🔄 Обновить", use_container_width=True, key="refresh_all"):
                st.rerun()
        
        if search_term:
            filtered_items = [item for item in filtered_items if search_term.lower() in item[1].lower()]
        
        st.caption(f"📌 Найдено позиций: {len(filtered_items)}")
        
        for idx, item in enumerate(filtered_items):
            unique_id = f"{item[0]}_{idx}"
            
            item_id = item[0]
            name = item[1]
            category = item[2] or ""
            location = item[3]
            room = item[4]
            description = item[5] or ""
            item_photo = item[6]
            location_photo = item[7]
            date_added = item[8]
            quantity = item[9]
            unit = item[10]
            threshold = item[11]
            application = item[12] if len(item) > 12 else ""
            installed_photo = item[13] if len(item) > 13 else ""
            equipment_id = item[14] if len(item) > 14 else None
            unit_id = item[15] if len(item) > 15 else None
            
            if quantity <= 0:
                status_emoji = "🔴"
                status_text = "КРИТИЧНО!"
                status_color = "#EF5350"
            elif quantity <= threshold:
                status_emoji = "🟡"
                status_text = f"Скоро (≤ {threshold})"
                status_color = "#FFA726"
            else:
                status_emoji = "🟢"
                status_text = "В норме"
                status_color = "#66BB6A"
            
            with st.container(border=True):
                # Верхняя часть карточки - информация
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"### {status_emoji} {name}")
                    st.caption(f"🆔 ID: {item_id}")
                with col2:
                    st.markdown(f"""
                        <div style="
                            background-color: {status_color}20;
                            padding: 5px 12px;
                            border-radius: 20px;
                            display: inline-block;
                            border: 1px solid {status_color};
                            color: {status_color};
                            font-weight: bold;
                            text-align: center;
                        ">
                            {status_emoji} {status_text}
                        </div>
                    """, unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Количество", f"{quantity} {unit}")
                with col2:
                    st.metric("🔴 Порог", f"{threshold} {unit}")
                with col3:
                    st.metric("🏠 Помещение", room)
                with col4:
                    st.metric("📍 Место", location)
                
                if category:
                    st.caption(f"📂 Категория: {category}")
                if description:
                    st.caption(f"📝 {description}")
                if application:
                    st.caption(f"🔧 Область применения: {application}")
                st.caption(f"🕒 Добавлено: {date_added}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if item_photo and os.path.exists(item_photo):
                        st.image(item_photo, caption="Фото вещи", use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                with col2:
                    if location_photo and os.path.exists(location_photo):
                        st.image(location_photo, caption="Фото места", use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                with col3:
                    if installed_photo and os.path.exists(installed_photo):
                        st.image(installed_photo, caption="Фото установки", use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                
                st.divider()
                
                # --- ДЕЙСТВИЯ ДЛЯ АДМИНИСТРАТОРА (ВСЕ КНОПКИ) ---
                if role == "admin":
                    st.write("**📋 Управление вещью:**")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        if st.button("✏️ Редактировать", key=f"edit_{unique_id}", use_container_width=True):
                            st.session_state.edit_mode[item_id] = True
                            st.rerun()
                    
                    with col2:
                        if st.button("📤 Списать", key=f"cons_{unique_id}", use_container_width=True):
                            st.session_state.cons_mode[item_id] = True
                            st.rerun()
                    
                    with col3:
                        if st.button("🚚 Переместить", key=f"move_{unique_id}", use_container_width=True):
                            st.session_state.move_mode[item_id] = True
                            st.rerun()
                    
                    with col4:
                        if st.button("📷 QR", key=f"qr_{unique_id}", use_container_width=True):
                            st.session_state.qr_mode[item_id] = True
                            st.rerun()
                    
                    with col5:
                        if st.button("🗑️ Удалить", key=f"del_{unique_id}", use_container_width=True):
                            delete_item(item_id)
                            st.success(f"✅ '{name}' удалена!")
                            st.rerun()
                
                # --- КНОПКА ДЛЯ СОТРУДНИКА: СПИСАТЬ ---
                if role == "employee":
                    if st.button("📤 Списать", key=f"employee_cons_{unique_id}", use_container_width=True):
                        st.session_state.cons_mode[item_id] = True
                        st.rerun()
                
                # --- ДИАЛОГ РЕДАКТИРОВАНИЯ (ТОЛЬКО ДЛЯ АДМИНА) ---
                if role == "admin" and st.session_state.edit_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**✏️ Редактирование: {name}**")
                        
                        with st.form(key=f"edit_form_{unique_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                new_name = st.text_input("Название*", value=name, key=f"edit_name_{unique_id}")
                                new_category = st.text_input("Категория", value=category, key=f"edit_cat_{unique_id}")
                                room_names = get_room_names()
                                new_room = st.selectbox("Помещение*", room_names, 
                                                       index=room_names.index(room) if room in room_names else 0,
                                                       key=f"edit_room_{unique_id}")
                                new_location = st.text_input("Место*", value=location, key=f"edit_loc_{unique_id}")
                            with col2:
                                new_quantity = st.number_input("Количество", min_value=0.0, step=0.5, value=float(quantity), key=f"edit_qty_{unique_id}")
                                new_unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект", "упаковка", "м²"], 
                                                       index=["шт", "л", "кг", "м", "комплект", "упаковка", "м²"].index(unit) if unit in ["шт", "л", "кг", "м", "комплект", "упаковка", "м²"] else 0,
                                                       key=f"edit_unit_{unique_id}")
                                new_threshold = st.number_input("Порог", min_value=0, step=1, value=int(threshold), key=f"edit_threshold_{unique_id}")
                                new_description = st.text_area("Описание", value=description, key=f"edit_desc_{unique_id}")
                                new_application = st.text_area("Область применения", value=application, key=f"edit_app_{unique_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Сохранить изменения", use_container_width=True):
                                    if new_name and new_room and new_location:
                                        update_item(item_id, new_name, new_category, new_location, new_room, 
                                                   new_description, new_application, None, None)
                                        conn = sqlite3.connect('storage.db')
                                        c = conn.cursor()
                                        c.execute("UPDATE items SET quantity = ?, unit = ?, threshold = ? WHERE id = ?", 
                                                 (new_quantity, new_unit, new_threshold, item_id))
                                        conn.commit()
                                        conn.close()
                                        
                                        st.session_state.edit_mode[item_id] = False
                                        st.success("✅ Изменения сохранены!")
                                        st.rerun()
                                    else:
                                        st.error("⚠️ Заполните обязательные поля!")
                            with col2:
                                if st.form_submit_button("❌ Отмена", use_container_width=True):
                                    st.session_state.edit_mode[item_id] = False
                                    st.rerun()
                
                # --- ДИАЛОГ СПИСАНИЯ (ДЛЯ ВСЕХ) ---
                if st.session_state.cons_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**📤 Списание: {name}**")
                        st.caption(f"Доступно: {quantity} {unit}")
                        
                        with st.form(key=f"cons_form_{unique_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                cons_qty = st.number_input("Количество для списания", min_value=0.0, step=0.5, 
                                                          max_value=float(quantity), value=min(1.0, float(quantity)),
                                                          key=f"cons_qty_{unique_id}")
                                cons_user = st.text_input("Кто списывает", value=user_name, key=f"cons_user_{unique_id}")
                            with col2:
                                cons_object = st.text_input("Куда списывается*", placeholder="Объект, техника...", key=f"cons_obj_{unique_id}")
                                cons_note = st.text_area("Примечание", key=f"cons_note_{unique_id}")
                                cons_photo = st.file_uploader("📷 Фото причины", type=["jpg", "jpeg", "png"], key=f"cons_photo_{unique_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("✅ Списать", use_container_width=True):
                                    if cons_qty > 0 and cons_object:
                                        photo_path = ""
                                        if cons_photo:
                                            ext = cons_photo.name.split('.')[-1]
                                            photo_path = f"images/cons_{uuid.uuid4()}.{ext}"
                                            with open(photo_path, "wb") as f:
                                                f.write(cons_photo.getbuffer())
                                        
                                        if role == "admin":
                                            status = "confirmed"
                                        else:
                                            status = "pending"
                                        
                                        success, msg = consume_item(item_id, cons_qty, cons_object, cons_user, cons_note, photo_path, status)
                                        if success:
                                            st.session_state.cons_mode[item_id] = False
                                            st.success(msg)
                                            if role == "employee":
                                                send_email(
                                                    "📤 Новая заявка на списание!",
                                                    f"Сотрудник {user_name} создал заявку на списание:\n\n"
                                                    f"📦 Вещь: {name}\n"
                                                    f"📦 Количество: {cons_qty} {unit}\n"
                                                    f"🚗 Объект: {cons_object}\n"
                                                    f"📝 Примечание: {cons_note or '—'}\n\n"
                                                    f"Зайдите в приложение для подтверждения."
                                                )
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                    else:
                                        st.error("⚠️ Укажите количество и объект!")
                            with col2:
                                if st.form_submit_button("❌ Отмена", use_container_width=True):
                                    st.session_state.cons_mode[item_id] = False
                                    st.rerun()
                
                # --- ДИАЛОГ ПЕРЕМЕЩЕНИЯ (ТОЛЬКО ДЛЯ АДМИНА) ---
                if role == "admin" and st.session_state.move_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**🚚 Перемещение: {name}**")
                        st.caption(f"Текущее помещение: **{room}**")
                        
                        available_rooms = [r for r in get_room_names() if r != room]
                        if available_rooms:
                            with st.form(key=f"move_form_{unique_id}"):
                                new_room = st.selectbox("Новое помещение", available_rooms, key=f"move_room_{unique_id}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("✅ Переместить", use_container_width=True):
                                        update_item_room(item_id, new_room)
                                        st.session_state.move_mode[item_id] = False
                                        st.success(f"✅ Перемещено в '{new_room}'")
                                        st.rerun()
                                with col2:
                                    if st.form_submit_button("❌ Отмена", use_container_width=True):
                                        st.session_state.move_mode[item_id] = False
                                        st.rerun()
                        else:
                            st.warning("Нет доступных помещений")
                            if st.button("❌ Закрыть", key=f"close_move_{unique_id}", use_container_width=True):
                                st.session_state.move_mode[item_id] = False
                                st.rerun()
                
                # --- ДИАЛОГ QR (ТОЛЬКО ДЛЯ АДМИНА) ---
                if role == "admin" and st.session_state.qr_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**📷 QR-код для: {name}**")
                        app_url = "https://garage-app-2-fcfztptpvqdfqmrh3vczif.streamlit.app"
                        qr_data = f"{app_url}?search={item_id}"
                        qr = qrcode.make(qr_data)
                        buf = BytesIO()
                        qr.save(buf, format="PNG")
                        st.image(buf, caption=f"QR для {name}", use_container_width=True)
                        st.download_button(
                            label="⬇️ Скачать QR",
                            data=buf.getvalue(),
                            file_name=f"qr_{name}_{item_id}.png",
                            mime="image/png",
                            key=f"download_qr_{unique_id}"
                        )
                        if st.button("❌ Закрыть QR", key=f"close_qr_{unique_id}", use_container_width=True):
                            st.session_state.qr_mode[item_id] = False
                            st.rerun()
        
        # Экспорт CSV
        st.divider()
        if filtered_items:
            data = []
            for item in filtered_items:
                data.append({
                    "Название": item[1],
                    "Категория": item[2] or "",
                    "Помещение": item[4],
                    "Место": item[3],
                    "Количество": f"{item[9]} {item[10]}",
                    "Порог": item[11],
                    "Статус": "Критично" if item[9] <= 0 else "Скоро" if item[9] <= item[11] else "Норма",
                    "Дата": item[8][:10] if len(item[8]) > 10 else item[8]
                })
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Скачать таблицу (CSV)",
                data=csv,
                file_name=f"все_вещи_{datetime.now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
                key="download_csv_all"
            )

# --- ВКЛАДКА 3: ПАРК ---
with tab3:
    st.subheader("🚜 Управление техникой")
    
    if st.session_state.get("selected_equipment"):
        eq_name = st.session_state.selected_equipment
        st.markdown(f"### 🔧 История списаний на **{eq_name}**")
        consumptions = get_consumption_by_equipment(eq_name)
        if consumptions:
            for c in consumptions:
                record_id, item_id, qty, unit, obj_name, user, date, status, photo, item_name = c
                status_text = "✅" if status == "confirmed" else "⏳"
                st.write(f"{status_text} **{item_name}** → {qty} {unit} (списал {user}, {date})")
                if photo and os.path.exists(photo):
                    st.image(photo, caption="Фото", use_container_width=True)
        else:
            st.info(f"🌱 Нет списаний на '{eq_name}'")
        if st.button("⬅️ Назад", key="back_from_equipment"):
            st.session_state.selected_equipment = None
            st.rerun()
        st.divider()
    
    if role == "admin":
        with st.expander("➕ Добавить технику", expanded=False):
            with st.form("add_equipment_form", clear_on_submit=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    eq_name = st.text_input("Название техники*", placeholder="МТЗ-82, К-700", key="eq_name_input")
                with col2:
                    st.write("")
                    st.write("")
                    if st.form_submit_button("➕ Добавить"):
                        if eq_name:
                            success, msg = add_equipment(eq_name)
                            st.success(msg) if success else st.error(msg)
                            st.rerun()
    
    equipment = get_equipment()
    if not equipment:
        st.info("🌱 Пока нет техники")
    else:
        st.caption(f"Всего техники: {len(equipment)}")
        for eq in equipment:
            eq_id, eq_name, eq_number, eq_date = eq
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                display = f"🚜 {eq_name}" + (f" ({eq_number})" if eq_number else "")
                st.markdown(f"**{display}**")
                st.caption(f"Добавлено: {eq_date[:10]}")
            with col2:
                if st.button("📊 История", key=f"eq_history_{eq_id}"):
                    st.session_state.selected_equipment = eq_name
                    st.rerun()
            with col3:
                if role == "admin" and st.button("🗑️", key=f"del_eq_{eq_id}"):
                    delete_equipment(eq_id)
                    st.rerun()

# --- ВКЛАДКА 4: СПИСАНИЯ ---
with tab4:
    st.subheader("📤 История списаний")
    
    all_cons = get_all_consumption()
    
    if not all_cons:
        st.info("🌱 Пока нет списаний")
    else:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            status_filter = st.selectbox(
                "📊 Статус",
                ["Все", "pending", "confirmed"],
                format_func=lambda x: {
                    "Все": "Все записи",
                    "pending": "⏳ Ожидают подтверждения",
                    "confirmed": "✅ Подтвержденные"
                }.get(x, x),
                key="status_filter_cons"
            )
        with col2:
            users = list(set([c[5] for c in all_cons]))
            user_filter = st.selectbox("👤 Пользователь", ["Все"] + users, key="user_filter_cons")
        with col3:
            st.write("")
            st.write("")
            if st.button("🔄 Обновить", use_container_width=True, key="refresh_cons"):
                st.rerun()
        
        filtered = all_cons
        if status_filter != "Все":
            filtered = [c for c in filtered if c[7] == status_filter]
        if user_filter != "Все":
            filtered = [c for c in filtered if c[5] == user_filter]
        
        st.caption(f"📌 Найдено записей: {len(filtered)}")
        
        for idx, c in enumerate(filtered):
            unique_id = f"cons_{c[0]}_{idx}"
            record_id = c[0]
            item_id = c[1]
            quantity = c[2]
            unit = c[3]
            object_name = c[4]
            user = c[5]
            date = c[6]
            status = c[7]
            photo = c[8] if len(c) > 8 else None
            item_name = c[9] if len(c) > 9 else "Неизвестно"
            
            if status == "pending":
                status_emoji = "⏳"
                status_text = "Ожидает подтверждения"
                status_color = "#FFA726"
            else:
                status_emoji = "✅"
                status_text = "Подтверждено"
                status_color = "#66BB6A"
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 2, 1])
                with col1:
                    st.markdown(f"### 📦 {item_name}")
                    st.caption(f"🆔 ID: {item_id}")
                with col2:
                    st.markdown(f"""
                        <div style="
                            background-color: {status_color}20;
                            padding: 5px 12px;
                            border-radius: 20px;
                            display: inline-block;
                            border: 1px solid {status_color};
                            color: {status_color};
                            font-weight: bold;
                        ">
                            {status_emoji} {status_text}
                        </div>
                    """, unsafe_allow_html=True)
                with col3:
                    if role == "admin" and status == "pending":
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✅", key=f"approve_{unique_id}", help="Подтвердить"):
                                approve_consumption(record_id)
                                st.success("✅ Заявка подтверждена!")
                                st.rerun()
                        with col_btn2:
                            if st.button("❌", key=f"reject_{unique_id}", help="Отклонить"):
                                delete_consumption_record(record_id)
                                st.success("❌ Заявка отклонена!")
                                st.rerun()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Количество", f"{quantity} {unit}")
                with col2:
                    st.metric("🚗 Объект", object_name)
                with col3:
                    st.metric("👤 Сотрудник", user)
                with col4:
                    st.metric("🕒 Дата", date[:16] if len(date) > 16 else date)
                
                if st.button(f"📋 Подробнее", key=f"details_btn_{unique_id}", use_container_width=True):
                    show_key = f"show_details_{unique_id}"
                    st.session_state.show_details[show_key] = not st.session_state.show_details.get(show_key, False)
                    st.rerun()
                
                if st.session_state.show_details.get(f"show_details_{unique_id}", False):
                    with st.container(border=True):
                        st.markdown("### 📋 Детали списания")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**📦 Информация о вещи:**")
                            st.write(f"• Название: {item_name}")
                            st.write(f"• ID: {item_id}")
                            st.write(f"• Количество: {quantity} {unit}")
                            st.write(f"• Объект: {object_name}")
                        with col2:
                            st.write("**👤 Информация о списании:**")
                            st.write(f"• Сотрудник: {user}")
                            st.write(f"• Дата: {date}")
                            st.write(f"• Статус: {status_text}")
                            if photo and os.path.exists(photo):
                                st.image(photo, caption="📷 Фото", use_container_width=True)
                            else:
                                st.info("📷 Фото не приложено")
                        
                        if role == "admin":
                            st.divider()
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("🗑️ Удалить запись", key=f"del_{unique_id}", use_container_width=True):
                                    delete_consumption_record(record_id)
                                    st.success("✅ Запись удалена!")
                                    st.rerun()
                            with col2:
                                if status == "pending":
                                    if st.button("✅ Подтвердить", key=f"approve2_{unique_id}", use_container_width=True):
                                        approve_consumption(record_id)
                                        st.success("✅ Заявка подтверждена!")
                                        st.rerun()
                            with col3:
                                if st.button("📧 Отправить отчет", key=f"report_{unique_id}", use_container_width=True):
                                    subject = f"📊 Отчет по списанию: {item_name}"
                                    body = f"""
                                    📊 Отчет по списанию
            
                                    📦 Вещь: {item_name}
                                    📦 Количество: {quantity} {unit}
                                    🚗 Объект: {object_name}
                                    👤 Сотрудник: {user}
                                    📅 Дата: {date}
                                    📊 Статус: {status_text}
            
                                    Это автоматическое уведомление из приложения "Мой Склад".
                                    """
                                    success, msg = send_email(subject, body)
                                    if success:
                                        st.success(msg)
                                    else:
                                        st.error(msg)
                        
                        if st.button("✖️ Закрыть", key=f"close_{unique_id}", use_container_width=True):
                            st.session_state.show_details[f"show_details_{unique_id}"] = False
                            st.rerun()
                
                st.divider()

# --- ВКЛАДКА 5: ОСТАТКИ ---
with tab5:
    st.subheader("📦 Управление остатками")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        search_stock = st.text_input("🔍 Поиск по названию", placeholder="Введите название...", key="search_stock")
    with col2:
        sort_by = st.selectbox("📊 Сортировка", ["По убыванию остатка", "По возрастанию остатка", "По алфавиту"], key="sort_stock")
    
    items = get_all_items()
    
    if search_stock:
        items = [item for item in items if search_stock.lower() in item[1].lower()]
    
    if sort_by == "По убыванию остатка":
        items.sort(key=lambda x: x[9], reverse=True)
    elif sort_by == "По возрастанию остатка":
        items.sort(key=lambda x: x[9])
    elif sort_by == "По алфавиту":
        items.sort(key=lambda x: x[1])
    
    if not items:
        st.info("🌱 Ничего не найдено")
    else:
        total_count = sum([item[9] for item in items])
        st.caption(f"📌 Всего позиций: {len(items)} | Общее количество: {total_count:.1f} шт.")
        
        for idx, item in enumerate(items):
            unique_id = f"stock_{item[0]}_{idx}"
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**{item[1]}**")
                    st.caption(f"📍 {item[3]} | 🏠 {item[4]}")
                    if item[2]:
                        st.caption(f"📂 {item[2]}")
                
                with col2:
                    st.metric("📦 Текущий остаток", f"{item[9]} {item[10]}")
                    st.caption(f"🔴 Порог: {item[11]} {item[10]}")
                
                with col3:
                    conn = sqlite3.connect('storage.db')
                    c = conn.cursor()
                    c.execute("SELECT SUM(quantity) FROM consumption WHERE item_id = ? AND status = 'confirmed'", (item[0],))
                    total_consumed = c.fetchone()[0] or 0
                    conn.close()
                    
                    initial_qty = item[9] + total_consumed
                    diff = initial_qty - item[9]
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("📈 Было", f"{initial_qty:.1f} {item[10]}")
                    with col_b:
                        st.metric("📉 Списано", f"{diff:.1f} {item[10]}")
                
                with col4:
                    if item[9] <= 0:
                        st.error("🔴 КРИТИЧНО!")
                    elif item[9] <= item[11]:
                        st.warning("🟡 Скоро закончится")
                    else:
                        st.success("🟢 В норме")
                    
                    if total_consumed > 0:
                        days_until = item[9] / (total_consumed / 30) if total_consumed > 0 else 999
                        if days_until < 7:
                            st.caption(f"⏰ Хватит на {days_until:.0f} дней")

# --- ВКЛАДКА 6: ЗАЯВКИ НА ЗАКУПКУ ---
with tab6:
    st.subheader("🛒 Заявки на закупку")
    
    if role == "employee":
        with st.expander("📝 Создать заявку на закупку", expanded=True):
            with st.form("purchase_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    item_name = st.text_input("🔧 Название вещи*", placeholder="Например: Болт М10", key="purchase_name")
                    quantity = st.number_input("📦 Количество*", min_value=0.0, step=0.5, value=1.0, key="purchase_qty")
                    unit = st.selectbox("📏 Ед. измерения", ["шт", "л", "кг", "м", "комплект", "упаковка"], key="purchase_unit")
                with col2:
                    location = st.text_input("📍 Куда будет установлено*", placeholder="Стеллаж №3, Гараж...", key="purchase_location")
                    description = st.text_area("📝 Описание / Причина", placeholder="Для замены изношенных деталей...", key="purchase_desc")
                    photo = st.file_uploader("📷 Фото (опционально)", type=["jpg", "jpeg", "png"], key="purchase_photo")
                
                if st.form_submit_button("📤 Отправить заявку", use_container_width=True):
                    if item_name and quantity > 0 and location:
                        photo_path = ""
                        if photo:
                            ext = photo.name.split('.')[-1]
                            photo_path = f"images/request_{uuid.uuid4()}.{ext}"
                            with open(photo_path, "wb") as f:
                                f.write(photo.getbuffer())
                        
                        success, msg = add_purchase_request(item_name, quantity, unit, description, photo_path, location, user_name)
                        if success:
                            st.success(msg)
                            send_email(
                                "🛒 Новая заявка на закупку!",
                                f"Сотрудник {user_name} создал заявку на закупку:\n\n"
                                f"🔧 Вещь: {item_name}\n"
                                f"📦 Количество: {quantity} {unit}\n"
                                f"📍 Место: {location}\n"
                                f"📝 Описание: {description or '—'}\n\n"
                                f"Зайдите в приложение для подтверждения."
                            )
                            st.rerun()
                    else:
                        st.error("⚠️ Заполните обязательные поля!")
        
        st.divider()
    
    all_requests = get_purchase_requests(None)
    
    if not all_requests:
        st.info("🌱 Нет заявок")
    else:
        if role == "admin":
            status_filter = st.selectbox("📊 Фильтр по статусу", ["Все", "pending", "approved", "rejected", "purchased"], key="purchase_status_filter")
            if status_filter != "Все":
                all_requests = [req for req in all_requests if req[9] == status_filter]
        
        if role == "employee":
            all_requests = [req for req in all_requests if req[7] == user_name]
        
        if not all_requests:
            st.info("🌱 Нет заявок")
        else:
            for idx, req in enumerate(all_requests):
                unique_id = f"req_{req[0]}_{idx}"
                req_id = req[0]
                item_name = req[1]
                quantity = req[2]
                unit = req[3]
                description = req[4]
                photo = req[5]
                location = req[6]
                user = req[7]
                date = req[8]
                status = req[9]
                admin_comment = req[10] if len(req) > 10 else ""
                
                status_map = {
                    "pending": ("⏳", "Ожидает", "#FFA726"),
                    "approved": ("✅", "Одобрено", "#66BB6A"),
                    "rejected": ("❌", "Отклонено", "#EF5350"),
                    "purchased": ("🛒", "Закуплено", "#42A5F5")
                }
                emoji, status_text, color = status_map.get(status, ("❓", "Неизвестно", "#999"))
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{emoji} {item_name}**")
                        st.caption(f"📍 {location}")
                        if description:
                            st.caption(f"📝 {description}")
                    with col2:
                        st.metric("📦 Количество", f"{quantity} {unit}")
                        st.caption(f"👤 {user} | 🕒 {date[:16]}")
                    with col3:
                        st.markdown(f"""
                            <div style="
                                background-color: {color}20;
                                padding: 4px 10px;
                                border-radius: 12px;
                                display: inline-block;
                                border: 1px solid {color};
                                color: {color};
                                font-weight: bold;
                            ">
                                {emoji} {status_text}
                            </div>
                        """, unsafe_allow_html=True)
                    
                    if photo and os.path.exists(photo):
                        st.image(photo, caption="📷 Фото", width=150)
                    
                    if role == "admin" and status == "pending":
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if st.button("✅ Одобрить", key=f"app_req_{unique_id}", use_container_width=True):
                                update_purchase_request(req_id, "approved", "Одобрено администратором")
                                st.success("✅ Заявка одобрена!")
                                st.rerun()
                        with col2:
                            if st.button("❌ Отклонить", key=f"rej_req_{unique_id}", use_container_width=True):
                                admin_comment_text = st.text_input("Причина отклонения", key=f"rej_comment_{unique_id}")
                                if admin_comment_text:
                                    update_purchase_request(req_id, "rejected", admin_comment_text)
                                    st.success("❌ Заявка отклонена!")
                                    st.rerun()
                        with col3:
                            if st.button("🛒 Закуплено", key=f"buy_req_{unique_id}", use_container_width=True):
                                add_item(item_name, "Закуплено", location, "Склад", description, "", "", quantity, unit, 1, "", "", None, None)
                                update_purchase_request(req_id, "purchased", "Добавлено на склад")
                                st.success("✅ Вещь добавлена на склад!")
                                st.rerun()
                        with col4:
                            if st.button("🗑️ Удалить", key=f"del_req_{unique_id}", use_container_width=True):
                                delete_purchase_request(req_id)
                                st.success("✅ Заявка удалена!")
                                st.rerun()
                    
                    if admin_comment and status == "rejected":
                        st.warning(f"📝 Причина отклонения: {admin_comment}")

# --- ВКЛАДКА 7: УВЕДОМЛЕНИЯ (АДМИН) ---
with tab7:
    if role != "admin":
        st.warning("🔒 Только для администратора")
        st.stop()
    
    st.subheader("📊 Центр уведомлений")
    
    all_items = get_all_items()
    low_items = get_low_stock_items()
    pending_consumption = [c for c in get_all_consumption() if c[7] == "pending"]
    pending_requests = get_purchase_requests("pending")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⚠️ Критический остаток", len(low_items), delta="Требуют внимания" if low_items else None)
    with col2:
        st.metric("⏳ Ожидают подтверждения", len(pending_consumption), delta="Новые заявки" if pending_consumption else None)
    with col3:
        st.metric("🛒 Заявки на закупку", len(pending_requests), delta="Новые" if pending_requests else None)
    with col4:
        st.metric("📦 Всего позиций", len(all_items))
    
    st.divider()
    
    st.subheader("⚠️ Критический остаток")
    if low_items:
        for idx, item in enumerate(low_items):
            unique_id = f"low_{item[0]}_{idx}"
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.markdown(f"**{item[1]}**")
                    st.caption(f"📍 {item[3]} | 🏠 {item[4]}")
                with col2:
                    st.metric("📦 Остаток", f"{item[9]} {item[10]}")
                with col3:
                    st.metric("🔴 Порог", f"{item[11]} {item[10]}")
                with col4:
                    deficit = item[11] - item[9]
                    st.metric("Не хватает", f"{deficit if deficit > 0 else 0} {item[10]}")
    else:
        st.success("✅ Все вещи в норме!")
    
    st.divider()
    
    st.subheader("⏳ Ожидающие подтверждения списания")
    if pending_consumption:
        for idx, c in enumerate(pending_consumption):
            unique_id = f"pend_{c[0]}_{idx}"
            record_id, item_id, qty, unit, obj_name, user, date, status, photo, item_name = c
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{item_name}**")
                    st.caption(f"👤 {user} | 🚗 {obj_name}")
                with col2:
                    st.metric("📦 Количество", f"{qty} {unit}")
                with col3:
                    if st.button("✅ Подтвердить", key=f"notif_approve_{unique_id}", use_container_width=True):
                        approve_consumption(record_id)
                        st.success("✅ Подтверждено!")
                        st.rerun()
                    if st.button("❌ Отклонить", key=f"notif_reject_{unique_id}", use_container_width=True):
                        delete_consumption_record(record_id)
                        st.success("❌ Отклонено!")
                        st.rerun()
    else:
        st.success("✅ Нет заявок на подтверждение")
    
    st.divider()
    
    st.subheader("🛒 Заявки на закупку")
    if pending_requests:
        for idx, req in enumerate(pending_requests):
            unique_id = f"pend_req_{req[0]}_{idx}"
            req_id = req[0]
            item_name = req[1]
            quantity = req[2]
            unit = req[3]
            description = req[4]
            photo = req[5]
            location = req[6]
            user = req[7]
            date = req[8]
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{item_name}**")
                    st.caption(f"📍 {location}")
                    if description:
                        st.caption(f"📝 {description}")
                with col2:
                    st.metric("📦 Количество", f"{quantity} {unit}")
                    st.caption(f"👤 {user} | 🕒 {date[:16]}")
                with col3:
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("✅", key=f"notif_app_req_{unique_id}", help="Одобрить"):
                            update_purchase_request(req_id, "approved", "Одобрено из уведомлений")
                            st.success("✅ Одобрено!")
                            st.rerun()
                    with col_btn2:
                        if st.button("❌", key=f"notif_rej_req_{unique_id}", help="Отклонить"):
                            update_purchase_request(req_id, "rejected", "Отклонено из уведомлений")
                            st.success("❌ Отклонено!")
                            st.rerun()
                    with col_btn3:
                        if st.button("🛒", key=f"notif_buy_req_{unique_id}", help="Закуплено"):
                            add_item(item_name, "Закуплено", location, "Склад", description, "", "", quantity, unit, 1, "", "", None, None)
                            update_purchase_request(req_id, "purchased", "Добавлено на склад")
                            st.success("✅ Закуплено!")
                            st.rerun()
                
                if photo and os.path.exists(photo):
                    st.image(photo, caption="📷 Фото", width=150)
    else:
        st.success("✅ Нет новых заявок на закупку")

st.caption("📱 Мой Склад v2.0 | Уведомления, остатки, заявки")
