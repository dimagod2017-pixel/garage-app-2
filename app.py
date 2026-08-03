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
EMAIL_PASSWORD = "bpzhkwtwimhurhkt"
EMAIL_RECIPIENT = "Yvedomlenie-scald.sad@yandex.ru"
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 587

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
if "take_mode" not in st.session_state:
    st.session_state.take_mode = {}
if "qr_mode" not in st.session_state:
    st.session_state.qr_mode = {}
if "show_details" not in st.session_state:
    st.session_state.show_details = {}

# --- ФУНКЦИЯ ВХОДА ---
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
            .login-container h1 { color: #2E7D32; font-size: 2rem; margin-bottom: 10px; }
            .login-container .subtitle { color: #666; margin-bottom: 30px; }
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
            .stButton button:hover { background-color: #2E7D32 !important; }
            .stTextInput input {
                border-radius: 8px;
                border: 2px solid #e0e0e0;
                padding: 12px;
                font-size: 1.1rem;
                text-align: center;
                letter-spacing: 2px;
            }
            .stTextInput input:focus { border-color: #4CAF50; }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
            <div class="login-container">
                <h1>🌿 Мой Склад</h1>
                <p class="subtitle">Введите пароль для входа</p>
        """, unsafe_allow_html=True)
        
        password = st.text_input("🔑 Пароль", type="password", placeholder="Введите пароль...", key="login_password_main")
        
        if st.button("🔓 Войти", use_container_width=True):
            if password in USERS:
                st.session_state.user = USERS[password]
                st.rerun()
            else:
                st.error("❌ Неверный пароль!")
        
        st.markdown("""
            <div class="hint">
                💡 <strong>Для сотрудника:</strong> введите пароль <code>1111</code><br>
                🔑 <strong>Для администратора:</strong> введите пароль <code>12345</code>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.user is None:
    st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")
    show_login()
    st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

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

# --- ФУНКЦИИ ДЛЯ ЗАЯВОК ---
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

def update_item_photos(item_id, item_photo_path, location_photo_path, installed_photo_path):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""
        UPDATE items
        SET item_photo = ?, location_photo = ?, installed_photo = ?
        WHERE id = ?
    """, (item_photo_path, location_photo_path, installed_photo_path, item_id))
    conn.commit()
    conn.close()

def update_item_room(item_id, new_room):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET room = ? WHERE id = ?", (new_room, item_id))
    conn.commit()
    conn.close()

def update_item_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
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

init_db()

# --- СТАТИСТИКА ---
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
            
            item_pic = st.file_uploader("📷 Фото вещи", type=["jpg", "jpeg", "png"], key="item_pic")
            location_pic = st.file_uploader("📷 Фото места", type=["jpg", "jpeg", "png"], key="loc_pic")
            
            if st.form_submit_button("💾 Сохранить"):
                if name and location and room != "— Добавьте помещение —":
                    item_path = ""
                    loc_path = ""
                    if item_pic:
                        ext = item_pic.name.split('.')[-1]
                        item_path = f"images/{uuid.uuid4()}_item.{ext}"
                        with open(item_path, "wb") as f:
                            f.write(item_pic.getbuffer())
                    if location_pic:
                        ext = location_pic.name.split('.')[-1]
                        loc_path = f"images/{uuid.uuid4()}_loc.{ext}"
                        with open(loc_path, "wb") as f:
                            f.write(location_pic.getbuffer())
                    add_item(name, category, location, room, description, item_path, loc_path, quantity, unit, threshold, "", "", None, None)
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

# --- ОСНОВНАЯ СТРАНИЦА: КАРТОЧКИ ВЕЩЕЙ ---
st.subheader("📦 Все вещи на складе")

# Фильтры
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    search_query = st.text_input("🔍 Поиск", placeholder="Введите название...", key="main_search")
with col2:
    rooms = ["Все помещения"] + get_room_names()
    room_filter = st.selectbox("🏠 Помещение", rooms, key="main_room_filter")
with col3:
    st.write("")
    st.write("")
    if st.button("🔄 Обновить", use_container_width=True, key="main_refresh"):
        st.rerun()

# Получаем и фильтруем вещи
items = get_all_items()
if search_query:
    items = [item for item in items if search_query.lower() in item[1].lower()]
if room_filter != "Все помещения":
    items = [item for item in items if item[4] == room_filter]

if not items:
    st.info("🌱 На складе пока нет вещей. Добавьте их через боковое меню.")
else:
    st.caption(f"📌 Найдено: {len(items)}")
    
    # Отображаем карточки в сетке 3 колонки
    cols = st.columns(3)
    for idx, item in enumerate(items):
        with cols[idx % 3]:
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
            
            # Статус
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
            
            # Карточка
            with st.container(border=True):
                # Заголовок
                st.markdown(f"### {status_emoji} {name}")
                if category:
                    st.caption(f"📂 {category}")
                st.caption(f"🏠 {room} → 📍 {location}")
                st.caption(f"📦 {quantity} {unit}")
                st.caption(f"📊 {status_text}")
                
                # Фото
                if item_photo and os.path.exists(item_photo):
                    st.image(item_photo, use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/200/cccccc/969696?text=Нет+фото", use_container_width=True)
                
                if description:
                    st.caption(f"📝 {description}")
                st.caption(f"🕒 {date_added[:10]}")
                
                st.divider()
                
                # --- КНОПКИ ДЛЯ АДМИНИСТРАТОРА ---
                if role == "admin":
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button("✏️", key=f"main_edit_{item_id}", help="Редактировать"):
                            st.session_state.edit_mode[item_id] = True
                            st.rerun()
                    with col2:
                        if st.button("📤", key=f"main_cons_{item_id}", help="Списать"):
                            st.session_state.cons_mode[item_id] = True
                            st.rerun()
                    with col3:
                        if st.button("🚚", key=f"main_move_{item_id}", help="Переместить"):
                            st.session_state.move_mode[item_id] = True
                            st.rerun()
                    with col4:
                        if st.button("🗑️", key=f"main_del_{item_id}", help="Удалить"):
                            delete_item(item_id)
                            st.success(f"✅ '{name}' удалена!")
                            st.rerun()
                
                # --- КНОПКА ДЛЯ СОТРУДНИКА ---
                if role == "employee":
                    if st.button("📤 Взять", key=f"main_take_{item_id}", use_container_width=True):
                        st.session_state.take_mode[item_id] = True
                        st.rerun()
                
                # --- РЕДАКТИРОВАНИЕ (АДМИН) ---
                if role == "admin" and st.session_state.edit_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**✏️ Редактирование: {name}**")
                        with st.form(key=f"main_edit_form_{item_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                new_name = st.text_input("Название*", value=name, key=f"main_edit_name_{item_id}")
                                new_category = st.text_input("Категория", value=category, key=f"main_edit_cat_{item_id}")
                                room_names = get_room_names()
                                new_room = st.selectbox("Помещение*", room_names, 
                                                       index=room_names.index(room) if room in room_names else 0,
                                                       key=f"main_edit_room_{item_id}")
                                new_location = st.text_input("Место*", value=location, key=f"main_edit_loc_{item_id}")
                            with col2:
                                new_quantity = st.number_input("Количество", min_value=0.0, step=0.5, value=float(quantity), key=f"main_edit_qty_{item_id}")
                                new_unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект"], 
                                                       index=["шт", "л", "кг", "м", "комплект"].index(unit) if unit in ["шт", "л", "кг", "м", "комплект"] else 0,
                                                       key=f"main_edit_unit_{item_id}")
                                new_threshold = st.number_input("Порог", min_value=0, step=1, value=int(threshold), key=f"main_edit_threshold_{item_id}")
                                new_description = st.text_area("Описание", value=description, key=f"main_edit_desc_{item_id}")
                            
                            # Фото
                            st.write("**📷 Фото:**")
                            col1, col2 = st.columns(2)
                            with col1:
                                if item_photo and os.path.exists(item_photo):
                                    st.image(item_photo, caption="Текущее фото вещи", use_container_width=True)
                                new_item_pic = st.file_uploader("Заменить фото вещи", type=["jpg", "jpeg", "png"], key=f"main_edit_item_pic_{item_id}")
                            with col2:
                                if location_photo and os.path.exists(location_photo):
                                    st.image(location_photo, caption="Текущее фото места", use_container_width=True)
                                new_location_pic = st.file_uploader("Заменить фото места", type=["jpg", "jpeg", "png"], key=f"main_edit_loc_pic_{item_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Сохранить", use_container_width=True):
                                    if new_name and new_room and new_location:
                                        update_item(item_id, new_name, new_category, new_location, new_room, 
                                                   new_description, "", None, None)
                                        update_item_quantity(item_id, new_quantity)
                                        # Обновляем фото
                                        item_path = item_photo or ""
                                        loc_path = location_photo or ""
                                        if new_item_pic:
                                            ext = new_item_pic.name.split('.')[-1]
                                            if item_path and os.path.exists(item_path):
                                                os.remove(item_path)
                                            item_path = f"images/{uuid.uuid4()}_item.{ext}"
                                            with open(item_path, "wb") as f:
                                                f.write(new_item_pic.getbuffer())
                                        if new_location_pic:
                                            ext = new_location_pic.name.split('.')[-1]
                                            if loc_path and os.path.exists(loc_path):
                                                os.remove(loc_path)
                                            loc_path = f"images/{uuid.uuid4()}_loc.{ext}"
                                            with open(loc_path, "wb") as f:
                                                f.write(new_location_pic.getbuffer())
                                        update_item_photos(item_id, item_path, loc_path, "")
                                        st.session_state.edit_mode[item_id] = False
                                        st.success("✅ Изменения сохранены!")
                                        st.rerun()
                                    else:
                                        st.error("⚠️ Заполните обязательные поля!")
                            with col2:
                                if st.form_submit_button("❌ Отмена", use_container_width=True):
                                    st.session_state.edit_mode[item_id] = False
                                    st.rerun()
                
                # --- СПИСАНИЕ (АДМИН) ---
                if role == "admin" and st.session_state.cons_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**📤 Списание: {name}**")
                        st.caption(f"Доступно: {quantity} {unit}")
                        with st.form(key=f"main_cons_form_{item_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                cons_qty = st.number_input("Количество", min_value=0.0, step=0.5, 
                                                          max_value=float(quantity), value=min(1.0, float(quantity)),
                                                          key=f"main_cons_qty_{item_id}")
                                cons_user = st.text_input("Кто списывает", value=user_name, key=f"main_cons_user_{item_id}")
                            with col2:
                                cons_object = st.text_input("Куда списывается*", key=f"main_cons_obj_{item_id}")
                                cons_note = st.text_area("Примечание", key=f"main_cons_note_{item_id}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("✅ Списать", use_container_width=True):
                                    if cons_qty > 0 and cons_object:
                                        success, msg = consume_item(item_id, cons_qty, cons_object, cons_user, cons_note, "", "confirmed")
                                        if success:
                                            st.session_state.cons_mode[item_id] = False
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                    else:
                                        st.error("⚠️ Укажите количество и объект!")
                            with col2:
                                if st.form_submit_button("❌ Отмена", use_container_width=True):
                                    st.session_state.cons_mode[item_id] = False
                                    st.rerun()
                
                # --- ПЕРЕМЕЩЕНИЕ (АДМИН) ---
                if role == "admin" and st.session_state.move_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**🚚 Перемещение: {name}**")
                        st.caption(f"Текущее помещение: **{room}**")
                        available_rooms = [r for r in get_room_names() if r != room]
                        if available_rooms:
                            with st.form(key=f"main_move_form_{item_id}"):
                                new_room = st.selectbox("Новое помещение", available_rooms, key=f"main_move_room_{item_id}")
                                new_location = st.text_input("Новое место", value=location, key=f"main_move_loc_{item_id}")
                                new_location_pic = st.file_uploader("📷 Фото нового места", type=["jpg", "jpeg", "png"], key=f"main_move_pic_{item_id}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("✅ Переместить", use_container_width=True):
                                        update_item_room(item_id, new_room)
                                        if new_location:
                                            conn = sqlite3.connect('storage.db')
                                            c = conn.cursor()
                                            c.execute("UPDATE items SET location = ? WHERE id = ?", (new_location, item_id))
                                            conn.commit()
                                            conn.close()
                                        if new_location_pic:
                                            ext = new_location_pic.name.split('.')[-1]
                                            loc_path = f"images/{uuid.uuid4()}_loc.{ext}"
                                            with open(loc_path, "wb") as f:
                                                f.write(new_location_pic.getbuffer())
                                            update_item_photos(item_id, "", loc_path, "")
                                        st.session_state.move_mode[item_id] = False
                                        st.success(f"✅ Перемещено в '{new_room}'")
                                        st.rerun()
                                with col2:
                                    if st.form_submit_button("❌ Отмена", use_container_width=True):
                                        st.session_state.move_mode[item_id] = False
                                        st.rerun()
                        else:
                            st.warning("Нет доступных помещений")
                            if st.button("❌ Закрыть", key=f"main_close_move_{item_id}", use_container_width=True):
                                st.session_state.move_mode[item_id] = False
                                st.rerun()
                
                # --- ВЗЯТЬ (СОТРУДНИК) ---
                if role == "employee" and st.session_state.take_mode.get(item_id, False):
                    with st.container(border=True):
                        st.write(f"**📤 Взять: {name}**")
                        st.caption(f"Доступно: {quantity} {unit}")
                        with st.form(key=f"main_take_form_{item_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                take_qty = st.number_input("Количество", min_value=0.0, step=0.5, 
                                                          max_value=float(quantity), value=min(1.0, float(quantity)),
                                                          key=f"main_take_qty_{item_id}")
                            with col2:
                                # Поиск техники
                                equipment_list = get_equipment()
                                tech_options = ["Другое"]
                                for eq in equipment_list:
                                    tech_options.append(eq[1] + (f" ({eq[2]})" if eq[2] else ""))
                                    units = get_units(eq[0])
                                    for u in units:
                                        tech_options.append(f"{eq[1]} → {u[1]}")
                                
                                search_tech = st.text_input("🔍 На что взял?", placeholder="Техника или агрегат...", key=f"main_take_search_{item_id}")
                                filtered_tech = [opt for opt in tech_options if search_tech.lower() in opt.lower()] if search_tech else tech_options
                                
                                if filtered_tech:
                                    selected_tech = st.selectbox("Выберите объект", filtered_tech, key=f"main_take_sel_{item_id}")
                                    if selected_tech == "Другое":
                                        object_name_input = st.text_input("Введите название*", key=f"main_take_custom_{item_id}")
                                    else:
                                        object_name_input = selected_tech
                                else:
                                    st.warning("Ничего не найдено")
                                    object_name_input = st.text_input("Введите название*", key=f"main_take_custom_{item_id}")
                            
                            take_photo = st.file_uploader("📷 Фото (причина замены)", type=["jpg", "jpeg", "png"], key=f"main_take_photo_{item_id}")
                            note = st.text_area("Примечание", key=f"main_take_note_{item_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("✅ Подтвердить", use_container_width=True):
                                    if take_qty <= 0:
                                        st.error("Количество > 0")
                                    elif not object_name_input:
                                        st.error("Укажите объект")
                                    else:
                                        photo_path = ""
                                        if take_photo:
                                            ext = take_photo.name.split('.')[-1]
                                            photo_path = f"images/cons_{uuid.uuid4()}.{ext}"
                                            with open(photo_path, "wb") as f:
                                                f.write(take_photo.getbuffer())
                                        
                                        success, msg = consume_item(item_id, take_qty, object_name_input, user_name, note, photo_path, "pending")
                                        if success:
                                            send_email(
                                                "📤 Новая заявка на списание!",
                                                f"Сотрудник {user_name} создал заявку на списание:\n\n"
                                                f"📦 Вещь: {name}\n"
                                                f"📦 Количество: {take_qty} {unit}\n"
                                                f"🚗 Объект: {object_name_input}\n"
                                                f"📝 Примечание: {note or '—'}\n\n"
                                                f"Зайдите в приложение для подтверждения."
                                            )
                                            st.session_state.take_mode[item_id] = False
                                            st.success("✅ Заявка отправлена! Администратор получит уведомление.")
                                            st.rerun()
                                        else:
                                            st.error(msg)
                            with col2:
                                if st.form_submit_button("❌ Отмена", use_container_width=True):
                                    st.session_state.take_mode[item_id] = False
                                    st.rerun()

st.caption("📱 Мой Склад v2.0 | Карточки вещей на главной")
