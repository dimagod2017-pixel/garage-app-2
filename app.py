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

# --- НАСТРОЙКА YANDEX ПОЧТЫ ---
EMAIL_SENDER = "Yvedomlenie-scald.sad@yandex.ru"
EMAIL_PASSWORD = "ТВОЙ_ПАРОЛЬ_ОТ_ПОЧТЫ"  # ← ЗАМЕНИ НА СВОЙ ПАРОЛЬ
EMAIL_RECIPIENT = "Yvedomlenie-scald.sad@yandex.ru"
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 587

def send_email(subject, body):
    """Отправляет email через Yandex с поддержкой UTF-8"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        
        # Ключевое исправление: указываем кодировку UTF-8
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "✅ Email отправлен"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

# --- ПАРОЛИ И РОЛИ ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.sidebar.title("🔐 Вход")
    
    if "user" in st.session_state and st.session_state.user is not None:
        return
    
    st.sidebar.markdown("""
        <style>
            input[type="password"] {
                -webkit-text-security: disc !important;
                font-size: 1.2rem !important;
                letter-spacing: 4px !important;
            }
            input[type="password"]:focus {
                outline: 2px solid #4CAF50 !important;
                border-color: #4CAF50 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    password = st.sidebar.text_input(
        "Введите пароль:",
        type="password",
        key="login_password",
        placeholder="12345"
    )
    
    st.markdown("""
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const passwordInput = document.querySelector('input[type="password"]');
                if (passwordInput) {
                    passwordInput.setAttribute('inputmode', 'numeric');
                    passwordInput.setAttribute('autocomplete', 'off');
                    passwordInput.setAttribute('pattern', '[0-9]*');
                }
            });
        </script>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.sidebar.columns([2, 1, 1])
    with col1:
        if st.button("🔓 Войти", use_container_width=True):
            if password in USERS:
                st.session_state.user = USERS[password]
                st.session_state.user["password"] = password
                st.query_params["user"] = password
                st.rerun()
            else:
                st.sidebar.error("❌ Неверный пароль!")
    with col2:
        if st.button("🔄 Сброс", use_container_width=True, help="Очистить сохранённый пароль"):
            st.query_params.clear()
            st.session_state.user = None
            st.rerun()
    with col3:
        if st.button("✖️", help="Очистить поле"):
            st.session_state.login_password = ""
            st.rerun()

if "user" in st.query_params:
    saved_user = st.query_params["user"]
    if saved_user in USERS and st.session_state.user is None:
        st.session_state.user = USERS[saved_user]
        st.session_state.user["password"] = saved_user

if st.session_state.user is None:
    login()
    st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

st.title("🌿 Мой Склад")
st.caption(f"👋 Добро пожаловать, {user_name}! {('🔑 Администратор' if role == 'admin' else '🔧 Сотрудник')}")

if st.sidebar.button("🚪 Выйти"):
    st.query_params.clear()
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
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "selected_room" not in st.session_state:
    st.session_state.selected_room = None
if "selected_equipment" not in st.session_state:
    st.session_state.selected_equipment = None
if "show_low_stock" not in st.session_state:
    st.session_state.show_low_stock = False

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
            .element-container, .stContainer, .stColumn { background-color: transparent !important; }
            div[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0d1a0d, #1a2a1a) !important;
                border-right: 2px solid #2e5a2e !important;
            }
            div[data-testid="stSidebar"] * { color: #d4e8d4 !important; }
            div[data-testid="stSidebar"] .stTextInput input {
                background-color: #1a2a1a !important;
                color: #d4e8d4 !important;
                border-color: #2e5a2e !important;
            }
            .main-header {
                background: linear-gradient(135deg, #1B5E20, #2E7D32) !important;
            }
            .stat-btn-wrap {
                background: #1a2a1a !important;
                border-color: #2e5a2e !important;
                color: #d4e8d4 !important;
            }
            .stat-btn-wrap:hover {
                border-color: #4CAF50 !important;
            }
            .stat-number { color: #4CAF50 !important; }
            .stat-label { color: #9acd9a !important; }
        </style>
    """, unsafe_allow_html=True)

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
                  date_added TEXT,
                  UNIQUE(name, equipment_id))''')
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

def update_equipment(equipment_id, name, number):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE equipment SET name = ?, number = ? WHERE id = ?", (name, number, equipment_id))
    conn.commit()
    conn.close()
    return True, "Данные обновлены"

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
        return False, f"Агрегат '{name}' уже существует для этой техники"

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

def approve_consumption(record_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE consumption SET status = 'confirmed' WHERE id = ?", (record_id,))
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

def get_pending_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c
                 JOIN items i ON c.item_id = i.id
                 WHERE c.status = 'pending'
                 ORDER BY c.date DESC""")
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

def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo, equipment_id, unit_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id))
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

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def update_threshold(item_id, new_threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET threshold = ? WHERE id = ?", (new_threshold, item_id))
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

def search_items(query, room_filter=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    query_like = f"%{query}%"
    query_lower = f"%{query.lower()}%"
    if room_filter and room_filter != "Все помещения":
        c.execute("""
            SELECT * FROM items
            WHERE (name LIKE ?
                   OR category LIKE ?
                   OR location LIKE ?
                   OR description LIKE ?
                   OR application LIKE ?
                   OR LOWER(name) LIKE ?
                   OR LOWER(category) LIKE ?
                   OR LOWER(location) LIKE ?
                   OR LOWER(description) LIKE ?
                   OR LOWER(application) LIKE ?)
            AND room = ?
        """, (query_like, query_like, query_like, query_like, query_like,
              query_lower, query_lower, query_lower, query_lower, query_lower,
              room_filter))
    else:
        c.execute("""
            SELECT * FROM items
            WHERE name LIKE ?
               OR category LIKE ?
               OR location LIKE ?
               OR description LIKE ?
               OR application LIKE ?
               OR LOWER(name) LIKE ?
               OR LOWER(category) LIKE ?
               OR LOWER(location) LIKE ?
               OR LOWER(description) LIKE ?
               OR LOWER(application) LIKE ?
        """, (query_like, query_like, query_like, query_like, query_like,
              query_lower, query_lower, query_lower, query_lower, query_lower))
    results = c.fetchall()
    conn.close()
    return results

def get_all_items(room_filter=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if room_filter and room_filter != "Все помещения":
        c.execute("SELECT * FROM items WHERE room = ? ORDER BY date_added DESC", (room_filter,))
    else:
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

def get_statistics():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM items")
    total_items = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT room) FROM items")
    total_rooms = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM items WHERE quantity <= threshold")
    low_stock_count = c.fetchone()[0]
    c.execute("SELECT category, COUNT(*) FROM items GROUP BY category ORDER BY COUNT(*) DESC LIMIT 3")
    top_categories = c.fetchall()
    c.execute("SELECT COUNT(*) FROM equipment")
    total_equipment = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rooms")
    total_rooms_list = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM consumption")
    total_consumption = c.fetchone()[0]
    conn.close()
    return total_items, total_rooms, low_stock_count, top_categories, total_equipment, total_rooms_list, total_consumption

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

# --- ПОКАЗ УВЕДОМЛЕНИЙ ---
def show_low_stock_banner():
    if role != "admin":
        return
    low_items = get_low_stock_items()
    if low_items:
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, #ffebee, #ffcdd2);
                border-left: 5px solid #f44336;
                border-radius: 12px;
                padding: 1.2rem 1.5rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 4px 15px rgba(244, 67, 54, 0.2);
            ">
                <div style="display: flex; align-items: center; gap: 0.8rem;">
                    <span style="font-size: 2rem;">🔴</span>
                    <div>
                        <strong style="font-size: 1.1rem; color: #c62828;">⚠️ ВНИМАНИЕ! Нужно пополнить склад!</strong>
                        <div style="font-size: 0.9rem; color: #b71c1c; margin-top: 0.3rem;">
        """, unsafe_allow_html=True)
        for item in low_items:
            st.write(f"• **{item[1]}** — {item[9]} {item[10]} (порог: {item[11]}) в **{item[4]}**")
        st.markdown("""
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# --- СТАТИСТИКА ---
total_items, total_rooms, low_stock_count, top_categories, total_equipment, total_rooms_list, total_consumption = get_statistics()

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    if st.button("📦\n" + str(total_items) + "\nВещи", use_container_width=True, key="stat_items"):
        st.session_state.active_tab = 1
        st.rerun()

with col2:
    if st.button("🏠\n" + str(total_rooms_list) + "\nПомещения", use_container_width=True, key="stat_rooms"):
        st.session_state.active_tab = 4
        st.rerun()

with col3:
    if role == "admin":
        if st.button("⚠️\n" + str(low_stock_count) + "\nПополнить", use_container_width=True, key="stat_low_stock"):
            st.session_state.active_tab = 0
            st.session_state.show_low_stock = True
            st.rerun()
    else:
        st.button("⚠️\n" + str(low_stock_count) + "\nПополнить", use_container_width=True, key="stat_low_stock", disabled=True)

with col4:
    top_cat_str = "\n".join([f"{cat}" for cat, count in top_categories[:2]]) if top_categories else "—"
    st.button("🏆\nТоп\n" + top_cat_str, use_container_width=True, key="stat_top", disabled=True)

with col5:
    if st.button("🚜\n" + str(total_equipment) + "\nТехника", use_container_width=True, key="stat_equipment"):
        st.session_state.active_tab = 2
        st.rerun()

with col6:
    if st.button("📤\n" + str(total_consumption) + "\nСписано", use_container_width=True, key="stat_consumption"):
        st.session_state.active_tab = 3
        st.rerun()

show_low_stock_banner()

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    st.divider()
    
    # --- ТЕСТ EMAIL ---
    st.subheader("📧 Тест Email")
    if st.button("📧 Отправить тестовое письмо", use_container_width=True):
        success, msg = send_email(
            "✅ Тестовое письмо из приложения!",
            "Если вы читаете это письмо — уведомления работают!\n\n"
            "Проверено: " + datetime.now().strftime("%Y-%m-%d %H:%M")
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
            st.warning("⚠️ Сначала добавьте помещения в разделе 'Помещения'!")
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Название вещи*")
            category = st.text_input("Категория")
            if room_names:
                room = st.selectbox("Помещение*", room_names)
            else:
                room = st.selectbox("Помещение*", ["— Сначала добавьте помещение —"])
            location = st.text_input("Место внутри помещения*")
            description = st.text_area("Описание")
            st.subheader("🔧 Привязка к технике")
            equipment_list = get_equipment()
            if equipment_list:
                eq_names = [eq[1] for eq in equipment_list]
                selected_eq = st.selectbox("Техника", ["Не выбрано"] + eq_names)
                if selected_eq != "Не выбрано":
                    eq_id = [eq[0] for eq in equipment_list if eq[1] == selected_eq][0]
                    units = get_units(eq_id)
                    if units:
                        unit_names = [u[1] for u in units]
                        selected_unit = st.selectbox("Агрегат/оборудование", ["Не выбрано"] + unit_names)
                        if selected_unit != "Не выбрано":
                            unit_id = [u[0] for u in units if u[1] == selected_unit][0]
                        else:
                            unit_id = None
                    else:
                        st.caption("Нет агрегатов для этой техники")
                        unit_id = None
                else:
                    eq_id = None
                    unit_id = None
            else:
                st.info("Сначала добавьте технику в разделе '🚜 Парк'")
                eq_id = None
                unit_id = None
            application = st.text_area("🔧 Область применения", placeholder="Например: ремень генератора трактора МТЗ-80")
            col1, col2, col3 = st.columns(3)
            with col1:
                quantity = st.number_input("Количество", min_value=0.0, step=0.5, value=1.0)
            with col2:
                unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект", "упаковка", "м²", "другой"])
                if unit == "другой":
                    unit = st.text_input("Своя единица")
            with col3:
                threshold = st.number_input("Порог", min_value=0, step=1, value=1)
            item_pic = st.file_uploader("📷 Фото вещи", type=["jpg", "jpeg", "png"], key="item")
            location_pic = st.file_uploader("📷 Фото места", type=["jpg", "jpeg", "png"], key="loc")
            installed_pic = st.file_uploader("📷 Фото установки на агрегате", type=["jpg", "jpeg", "png"], key="installed")
            submitted = st.form_submit_button("💾 Сохранить")
            if submitted and name and location and room and room != "— Сначала добавьте помещение —":
                item_path = ""
                loc_path = ""
                installed_path = ""
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
                if installed_pic:
                    ext = installed_pic.name.split('.')[-1]
                    installed_path = f"images/{uuid.uuid4()}_installed.{ext}"
                    with open(installed_path, "wb") as f:
                        f.write(installed_pic.getbuffer())
                add_item(name, category, location, room, description, item_path, loc_path, quantity, unit, threshold, application, installed_path, eq_id, unit_id)
                st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
                st.rerun()
            elif submitted:
                st.error("⚠️ Название, Помещение и Место обязательны!")
        st.divider()
    
    st.header("📥 Импорт Excel")
    uploaded_file = st.file_uploader("Выберите Excel-файл", type=["xlsx", "xls"])
    if uploaded_file and st.button("📤 Импортировать"):
        st.success("Импорт пока в разработке")
    st.header("📤 Экспорт Excel")
    if st.button("📥 Скачать Excel", use_container_width=True):
        excel_data = export_to_excel()
        st.download_button(label="⬇️ Скачать", data=excel_data, file_name=f"инвентарь_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

# --- ОСНОВНАЯ ОБЛАСТЬ: ВКЛАДКИ ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📤 История списаний", "🏠 Помещения"])

with tab1:
    col_search, col_btn = st.columns([5, 1])
    with col_search:
        search_query = st.text_input("🔍 Что ищем?", placeholder="Введите название, категорию, место...", key="search_input", value="")
        if search_query and len(search_query) > 0 and search_query[0].islower():
            search_query = search_query[0].upper() + search_query[1:] if len(search_query) > 1 else search_query.upper()
    with col_btn:
        st.write("")
        search_clicked = st.button("🔍 Найти", use_container_width=True)
    
    if st.session_state.get("show_low_stock", False) and role == "admin":
        st.info("📋 **Вещи, которые нужно пополнить:**")
        low_items = get_low_stock_items()
        if low_items:
            for item in low_items:
                qty = item[9]
                name = item[1]
                unit = item[10]
                room = item[4]
                threshold = item[11]
                st.write(f"• **{name}** — {qty} {unit} (порог: {threshold}) в **{room}**")
        else:
            st.success("✅ Все вещи в норме!")
        st.divider()
        st.session_state.show_low_stock = False
    
    rooms = ["Все помещения"] + get_room_names()
    room_filter = st.selectbox("🏠 Помещение", rooms, key="room_filter_tab1")
    items = search_items(search_query, room_filter) if search_query else get_all_items(room_filter)
    st.subheader(f"📌 Найдено: {len(items)}")
    if not items:
        st.info("🌱 Ничего нет. Добавьте через меню.")
    else:
        cols = st.columns(3)
        for idx, item in enumerate(items):
            with cols[idx % 3]:
                if len(item) >= 16:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo, equipment_id, unit_id = item[:16]
                elif len(item) >= 14:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo = item[:14]
                    equipment_id = None
                    unit_id = None
                else:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item[:12]
                    application = ""
                    installed_photo = ""
                    equipment_id = None
                    unit_id = None
                eq_name = ""
                unit_name = ""
                if equipment_id:
                    eq = get_equipment_by_id(equipment_id)
                    if eq:
                        eq_name = eq[1] + (f" ({eq[2]})" if eq[2] else "")
                if unit_id and equipment_id:
                    units = get_units(equipment_id)
                    for u in units:
                        if u[0] == unit_id:
                            unit_name = u[1]
                            break
                try:
                    qty = float(quantity)
                except:
                    qty = 0
                if qty <= 0:
                    status_emoji = "🔴"
                    status_text = "КРИТИЧНО!"
                elif qty <= threshold:
                    status_emoji = "🟡"
                    status_text = f"Скоро закончится (≤ {threshold})"
                else:
                    status_emoji = "🟢"
                    status_text = "В норме"

                with st.container(border=True):
                    col_title, col_dots = st.columns([6, 1])
                    with col_title:
                        st.markdown(f"**{status_emoji} {name}**")
                        if category:
                            st.caption(f"📂 {category}")
                    with col_dots:
                        if role == "admin":
                            menu_key = f"show_menu_{item_id}"
                            if st.button("⋮", key=f"menu_btn_{item_id}", help="Меню"):
                                st.session_state[menu_key] = not st.session_state.get(menu_key, False)
                                st.rerun()
                    st.caption(f"🏠 {room} → 📍 {location}")
                    if eq_name:
                        st.caption(f"🚜 **Техника:** {eq_name}")
                    if unit_name:
                        st.caption(f"🔧 **Агрегат:** {unit_name}")
                    if application:
                        st.caption(f"📝 **Область применения:** {application}")
                    st.caption(f"📦 Количество: **{qty} {unit}**")
                    st.caption(f"📊 Статус: **{status_text}**")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if item_photo and os.path.exists(item_photo):
                            st.image(item_photo, caption="Вещь", use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                    with c2:
                        if location_photo and os.path.exists(location_photo):
                            st.image(location_photo, caption="Место", use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                    with c3:
                        if installed_photo and os.path.exists(installed_photo):
                            st.image(installed_photo, caption="Установка", use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                    if description:
                        st.write(f"📝 {description}")
                    st.caption(f"🕒 Добавлено: {date_added}")

                    # --- МЕНЮ (ТОЛЬКО ДЛЯ АДМИНА) ---
                    if role == "admin":
                        menu_key = f"show_menu_{item_id}"
                        if st.session_state.get(menu_key, False):
                            with st.container(border=True):
                                st.write("**📋 Действия:**")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("✏️ Редактировать", key=f"edit_{item_id}", use_container_width=True):
                                        st.session_state[f"edit_mode_{item_id}"] = True
                                        st.session_state[menu_key] = False
                                        st.rerun()
                                with col2:
                                    if st.button("📤 Списать", key=f"cons_{item_id}", use_container_width=True):
                                        st.session_state[f"cons_mode_{item_id}"] = True
                                        st.session_state[menu_key] = False
                                        st.rerun()
                                    if st.button("📷 QR", key=f"qr_{item_id}", use_container_width=True):
                                        st.session_state[f"qr_mode_{item_id}"] = True
                                        st.session_state[menu_key] = False
                                        st.rerun()
                                with col3:
                                    if st.button("🚚 Переместить", key=f"move_{item_id}", use_container_width=True):
                                        st.session_state[f"move_mode_{item_id}"] = True
                                        st.session_state[menu_key] = False
                                        st.rerun()
                                    if st.button("🗑️ Удалить", key=f"del_{item_id}", use_container_width=True):
                                        delete_item(item_id)
                                        st.rerun()

                    # --- КНОПКА "ВЗЯЛ" ДЛЯ СОТРУДНИКА ---
                    if role == "employee":
                        if st.button("📤 Взял", key=f"take_{item_id}", use_container_width=True):
                            st.session_state[f"take_mode_{item_id}"] = True
                            st.rerun()
                    
                    # --- ДИАЛОГ ДЛЯ СОТРУДНИКА (ВЗЯЛ) ---
                    if st.session_state.get(f"take_mode_{item_id}", False) and role == "employee":
                        with st.container(border=True):
                            st.write(f"**📤 Взять {name}**")
                            st.caption(f"Доступно: {qty} {unit}")
                            col1, col2 = st.columns(2)
                            with col1:
                                take_qty = st.number_input("Количество", min_value=0.0, step=0.5, max_value=float(qty), value=min(1.0, float(qty)), key=f"take_qty_{item_id}")
                            with col2:
                                equipment_list = get_equipment()
                                search_options = ["Другое"]
                                for eq in equipment_list:
                                    eq_name = eq[1] + (f" ({eq[2]})" if eq[2] else "")
                                    search_options.append(eq_name)
                                    units = get_units(eq[0])
                                    for unit in units:
                                        search_options.append(f"{eq_name} → {unit[1]}")
                                search_equipment = st.text_input("🔍 На что взял?", placeholder="Машина №5...", key=f"take_search_{item_id}")
                                filtered_eq = [opt for opt in search_options if search_equipment.lower() in opt.lower()] if search_equipment else search_options
                                if filtered_eq:
                                    selected_eq = st.selectbox("Выберите объект", filtered_eq, key=f"take_sel_{item_id}")
                                    if selected_eq == "Другое":
                                        object_name = st.text_input("Введите название*", key=f"take_custom_{item_id}")
                                    else:
                                        object_name = selected_eq
                                else:
                                    st.warning("Ничего не найдено")
                                    object_name = st.text_input("Введите название*", key=f"take_custom_{item_id}")
                            
                            # --- ФОТО ДЛЯ СОТРУДНИКА ---
                            take_photo = st.file_uploader("📷 Фото (причина замены)", type=["jpg", "jpeg", "png"], key=f"take_photo_{item_id}")
                            
                            note = st.text_area("Примечание", key=f"take_note_{item_id}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Подтвердить", key=f"save_take_{item_id}"):
                                    if take_qty <= 0:
                                        st.error("Количество > 0")
                                    elif not object_name:
                                        st.error("Укажите объект")
                                    else:
                                        # Сохраняем фото
                                        photo_path = ""
                                        if take_photo:
                                            ext = take_photo.name.split('.')[-1]
                                            photo_path = f"images/cons_{uuid.uuid4()}.{ext}"
                                            with open(photo_path, "wb") as f:
                                                f.write(take_photo.getbuffer())
                                        
                                        success, message = consume_item(item_id, take_qty, object_name, user_name, note, photo_path, "pending")
                                        if success:
                                            # --- ОТПРАВКА EMAIL ---
                                            subject = "📤 Новая заявка на списание!"
                                            body = (
                                                f"👤 Сотрудник: {user_name}\n"
                                                f"📦 Вещь: {name}\n"
                                                f"📦 Количество: {take_qty} {unit}\n"
                                                f"🚗 Объект: {object_name}\n"
                                                f"📝 Примечание: {note or '—'}\n\n"
                                                f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                                                f"Зайдите в приложение, чтобы подтвердить или отклонить заявку."
                                            )
                                            send_email(subject, body)
                                            
                                            st.success("✅ Заявка отправлена! Администратор получит уведомление на почту.")
                                            st.session_state[f"take_mode_{item_id}"] = False
                                            st.rerun()
                                        else:
                                            st.error(message)
                            with col2:
                                if st.button("❌ Отмена", key=f"cancel_take_{item_id}"):
                                    st.session_state[f"take_mode_{item_id}"] = False
                                    st.rerun()

                    # --- ОСТАЛЬНЫЕ ДИАЛОГИ (ТОЛЬКО ДЛЯ АДМИНА) ---
                    if role == "admin":
                        # Редактирование
                        if st.session_state.get(f"edit_mode_{item_id}", False):
                            with st.container(border=True):
                                st.write(f"**✏️ Редактирование {name}**")
                                new_name = st.text_input("Название", value=name, key=f"new_name_{item_id}")
                                new_category = st.text_input("Категория", value=category or "", key=f"new_cat_{item_id}")
                                new_description = st.text_area("Описание", value=description or "", key=f"new_desc_{item_id}")
                                new_application = st.text_area("Область применения", value=application or "", key=f"new_app_{item_id}")
                                room_names = get_room_names()
                                new_room = st.selectbox("Помещение", room_names, index=room_names.index(room) if room in room_names else 0, key=f"new_room_{item_id}")
                                equipment_list = get_equipment()
                                eq_names = ["Не выбрано"] + [eq[1] for eq in equipment_list]
                                current_eq = eq_names[0]
                                if equipment_id:
                                    eq = get_equipment_by_id(equipment_id)
                                    if eq:
                                        current_eq = eq[1]
                                new_eq = st.selectbox("Техника", eq_names, index=eq_names.index(current_eq) if current_eq in eq_names else 0, key=f"new_eq_{item_id}")
                                new_eq_id = None
                                if new_eq != "Не выбрано":
                                    for eq in equipment_list:
                                        if eq[1] == new_eq:
                                            new_eq_id = eq[0]
                                            break
                                unit_names = ["Не выбрано"]
                                if new_eq_id:
                                    units = get_units(new_eq_id)
                                    unit_names += [u[1] for u in units]
                                current_unit = unit_names[0]
                                if unit_id:
                                    units = get_units(equipment_id)
                                    for u in units:
                                        if u[0] == unit_id:
                                            current_unit = u[1]
                                            break
                                new_unit = st.selectbox("Агрегат", unit_names, index=unit_names.index(current_unit) if current_unit in unit_names else 0, key=f"new_unit_{item_id}")
                                new_unit_id = None
                                if new_unit != "Не выбрано" and new_eq_id:
                                    units = get_units(new_eq_id)
                                    for u in units:
                                        if u[1] == new_unit:
                                            new_unit_id = u[0]
                                            break
                                st.divider()
                                st.write("**📷 Фото:**")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.caption("Фото вещи")
                                    if item_photo and os.path.exists(item_photo):
                                        st.image(item_photo, use_container_width=True)
                                    new_item_pic = st.file_uploader("Заменить", type=["jpg", "jpeg", "png"], key=f"new_item_{item_id}", label_visibility="collapsed")
                                with col2:
                                    st.caption("Фото места")
                                    if location_photo and os.path.exists(location_photo):
                                        st.image(location_photo, use_container_width=True)
                                    new_location_pic = st.file_uploader("Заменить", type=["jpg", "jpeg", "png"], key=f"new_loc_{item_id}", label_visibility="collapsed")
                                with col3:
                                    st.caption("Фото установки")
                                    if installed_photo and os.path.exists(installed_photo):
                                        st.image(installed_photo, use_container_width=True)
                                    new_installed_pic = st.file_uploader("Заменить", type=["jpg", "jpeg", "png"], key=f"new_inst_{item_id}", label_visibility="collapsed")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Сохранить", key=f"save_edit_{item_id}"):
                                        update_item(item_id, new_name, new_category, location, new_room, new_description, new_application, new_eq_id, new_unit_id)
                                        item_path = item_photo or ""
                                        loc_path = location_photo or ""
                                        installed_path = installed_photo or ""
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
                                        if new_installed_pic:
                                            ext = new_installed_pic.name.split('.')[-1]
                                            if installed_path and os.path.exists(installed_path):
                                                os.remove(installed_path)
                                            installed_path = f"images/{uuid.uuid4()}_installed.{ext}"
                                            with open(installed_path, "wb") as f:
                                                f.write(new_installed_pic.getbuffer())
                                        update_item_photos(item_id, item_path, loc_path, installed_path)
                                        st.session_state[f"edit_mode_{item_id}"] = False
                                        st.success("✅ Изменения сохранены!")
                                        st.rerun()
                                with col2:
                                    if st.button("❌ Отмена", key=f"cancel_edit_{item_id}"):
                                        st.session_state[f"edit_mode_{item_id}"] = False
                                        st.rerun()

                        # Списание (админ)
                        if st.session_state.get(f"cons_mode_{item_id}", False):
                            with st.container(border=True):
                                st.write(f"**📤 Списание {name}**")
                                st.caption(f"Доступно: {qty} {unit}")
                                col1, col2 = st.columns(2)
                                with col1:
                                    consume_qty = st.number_input("Количество", min_value=0.0, step=0.5, max_value=float(qty), value=min(1.0, float(qty)), key=f"cons_qty_{item_id}")
                                with col2:
                                    equipment_list = get_equipment()
                                    search_options = ["Другое"]
                                    for eq in equipment_list:
                                        eq_name = eq[1] + (f" ({eq[2]})" if eq[2] else "")
                                        search_options.append(eq_name)
                                        units = get_units(eq[0])
                                        for unit in units:
                                            search_options.append(f"{eq_name} → {unit[1]}")
                                    search_equipment = st.text_input("🔍 Поиск техники или агрегата", placeholder="Начните вводить...", key=f"search_eq_{item_id}")
                                    filtered_eq = [opt for opt in search_options if search_equipment.lower() in opt.lower()] if search_equipment else search_options
                                    if filtered_eq:
                                        selected_eq = st.selectbox("Выберите объект", filtered_eq, key=f"sel_eq_{item_id}")
                                        if selected_eq == "Другое":
                                            object_name = st.text_input("Введите название объекта*", key=f"custom_obj_{item_id}")
                                        else:
                                            object_name = selected_eq
                                    else:
                                        st.warning("Ничего не найдено")
                                        object_name = st.text_input("Введите название объекта*", key=f"custom_obj_{item_id}")
                                user = st.text_input("Кто списывает", value=user_name, key=f"cons_user_{item_id}")
                                note = st.text_area("Примечание", key=f"cons_note_{item_id}")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Списать", key=f"save_cons_{item_id}"):
                                        if consume_qty <= 0:
                                            st.error("Количество > 0")
                                        elif not object_name:
                                            st.error("Укажите объект")
                                        else:
                                            success, message = consume_item(item_id, consume_qty, object_name, user, note, "", "confirmed")
                                            if success:
                                                st.success(message)
                                                st.session_state[f"cons_mode_{item_id}"] = False
                                                st.rerun()
                                            else:
                                                st.error(message)
                                with col2:
                                    if st.button("❌ Отмена", key=f"cancel_cons_{item_id}"):
                                        st.session_state[f"cons_mode_{item_id}"] = False
                                        st.rerun()

                        # Перемещение
                        if st.session_state.get(f"move_mode_{item_id}", False):
                            with st.container(border=True):
                                st.write(f"**🚚 Перемещение {name}**")
                                st.caption(f"Текущее: **{room}**")
                                room_names = get_room_names()
                                available_rooms = [r for r in room_names if r != room]
                                if available_rooms:
                                    new_room = st.selectbox("Новое помещение", available_rooms, key=f"new_room_move_{item_id}")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("✅ Переместить", key=f"save_move_{item_id}"):
                                            update_item_room(item_id, new_room)
                                            st.session_state[f"move_mode_{item_id}"] = False
                                            st.success(f"✅ Перемещено в '{new_room}'")
                                            st.rerun()
                                    with col2:
                                        if st.button("❌ Отмена", key=f"cancel_move_{item_id}"):
                                            st.session_state[f"move_mode_{item_id}"] = False
                                            st.rerun()
                                else:
                                    st.warning("Нет доступных помещений")
                                    if st.button("❌ Закрыть", key=f"close_move_{item_id}"):
                                        st.session_state[f"move_mode_{item_id}"] = False
                                        st.rerun()

                        # QR
                        if st.session_state.get(f"qr_mode_{item_id}", False):
                            with st.container(border=True):
                                st.write(f"**📷 QR-код для {name}**")
                                app_url = "https://garage-app-2-fcfztptpvqdfqmrh3vczif.streamlit.app"
                                qr_data = f"{app_url}?search={item_id}"
                                qr = qrcode.make(qr_data)
                                buf = BytesIO()
                                qr.save(buf, format="PNG")
                                st.image(buf, caption=f"QR для {name}", use_container_width=True)
                                st.download_button(label="⬇️ Скачать QR", data=buf.getvalue(), file_name=f"qr_{name}_{item_id}.png", mime="image/png")
                                if st.button("❌ Закрыть QR", key=f"close_qr_{item_id}"):
                                    st.session_state[f"qr_mode_{item_id}"] = False
                                    st.rerun()

with tab2:
    st.subheader("📋 Все вещи в базе данных")
    all_items = get_all_items()
    if not all_items:
        st.info("🌱 В базе пока нет вещей")
    else:
        data = []
        for item in all_items:
            if len(item) >= 14:
                item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo = item[:14]
                equipment_id = None
                unit_id = None
            else:
                item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item[:12]
                application = ""
                installed_photo = ""
                equipment_id = None
                unit_id = None
            eq_name = ""
            unit_name = ""
            if equipment_id:
                eq = get_equipment_by_id(equipment_id)
                if eq:
                    eq_name = eq[1] + (f" ({eq[2]})" if eq[2] else "")
            if unit_id and equipment_id:
                units = get_units(equipment_id)
                for u in units:
                    if u[0] == unit_id:
                        unit_name = u[1]
                        break
            try:
                qty = float(quantity)
            except:
                qty = 0
            data.append({
                "Название": name,
                "Категория": category or "",
                "Помещение": room,
                "Место": location,
                "Техника": eq_name or "",
                "Агрегат": unit_name or "",
                "Область применения": application or "",
                "Количество": f"{qty} {unit}",
                "Статус": "🔴 Критично" if qty <= 0 else "🟡 Скоро" if qty <= threshold else "🟢 Норма",
                "Дата": date_added[:10]
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Скачать таблицу (CSV)", data=csv, file_name=f"все_вещи_{datetime.now().strftime('%Y-%m-%d')}.csv", mime="text/csv")

with tab3:
    st.subheader("🚜 Управление техникой")
    if st.session_state.get("selected_equipment"):
        eq_name = st.session_state.selected_equipment
        st.markdown(f"### 🔧 История списаний на **{eq_name}**")
        consumptions = get_consumption_by_equipment(eq_name)
        if consumptions:
            for c in consumptions:
                record_id, item_id, qty, unit, obj_name, user, date, item_name, status, photo = c
                status_text = "✅" if status == "confirmed" else "⏳"
                st.write(f"{status_text} **{item_name}** → {qty} {unit} (списал {user}, {date})")
                if photo and os.path.exists(photo):
                    st.image(photo, caption="Фото", use_container_width=True)
        else:
            st.info(f"🌱 Нет списаний на '{eq_name}'")
        if st.button("⬅️ Назад"):
            st.session_state.selected_equipment = None
            st.rerun()
        st.divider()
    if role == "admin":
        with st.expander("➕ Добавить технику", expanded=False):
            with st.form("add_equipment_form", clear_on_submit=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    eq_name = st.text_input("Название техники*", placeholder="МТЗ-82, К-700, ДОН-1500")
                with col2:
                    eq_number = st.text_input("Госномер", placeholder="А123ВС")
                with col3:
                    st.write("")
                    st.write("")
                    add_eq_btn = st.form_submit_button("➕ Добавить")
                if add_eq_btn and eq_name:
                    success, msg = add_equipment(eq_name, eq_number)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    equipment_list = get_equipment()
    if not equipment_list:
        st.info("🌱 Пока нет техники")
    else:
        st.caption(f"Всего техники: {len(equipment_list)}")
        for eq in equipment_list:
            eq_id, eq_name, eq_number, eq_date = eq
            cons = get_consumption_by_equipment(eq_name)
            cons_count = len(cons)
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                display = f"🚜 {eq_name}" + (f" ({eq_number})" if eq_number else "") + (f" — {cons_count} списаний" if cons_count > 0 else "")
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

with tab4:
    st.subheader("📤 История списаний")
    all_consumption = get_all_consumption()
    if not all_consumption:
        st.info("🌱 Пока нет списаний")
    else:
        if role == "employee":
            all_consumption = [c for c in all_consumption if c[5] == user_name]
        
        st.caption(f"Всего записей: {len(all_consumption)}")
        
        objects = list(set([c[4] for c in all_consumption]))
        filter_obj = st.selectbox("🔍 Фильтр по объекту", ["Все"] + objects)
        filtered = [c for c in all_consumption if filter_obj == "Все" or c[4] == filter_obj]
        
        if role == "admin":
            pending = [c for c in all_consumption if c[8] == "pending"]
            if pending:
                st.warning(f"⏳ **{len(pending)} заявок ожидают подтверждения!**")
                for c in pending:
                    record_id, item_id, qty, unit, obj_name, user, date, item_name, status, photo = c
                    col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
                    with col1:
                        st.write(f"⏳ **{item_name}** → {qty} {unit} на **{obj_name}** (запросил {user}, {date})")
                        if photo and os.path.exists(photo):
                            st.image(photo, caption="Фото причины", use_container_width=True)
                    with col2:
                        if st.button("✅ Подтвердить", key=f"approve_{record_id}"):
                            approve_consumption(record_id)
                            st.success("✅ Заявка подтверждена!")
                            st.rerun()
                    with col3:
                        if st.button("❌ Отклонить", key=f"reject_{record_id}"):
                            delete_consumption_record(record_id)
                            st.success("❌ Заявка отклонена!")
                            st.rerun()
                    with col4:
                        if st.button("📷", key=f"view_photo_{record_id}"):
                            if photo and os.path.exists(photo):
                                st.image(photo, caption="Фото", use_container_width=True)
                            else:
                                st.info("Нет фото")
                st.divider()
        
        for c in filtered:
            record_id, item_id, qty, unit, obj_name, user, date, item_name, status, photo = c
            status_text = "✅" if status == "confirmed" else "⏳"
            col1, col2, col3 = st.columns([7, 1, 1])
            with col1:
                st.write(f"{status_text} **{item_name}** → {qty} {unit} на **{obj_name}** (списал {user}, {date})")
                if photo and os.path.exists(photo):
                    st.image(photo, caption="Фото", use_container_width=True)
            with col2:
                if role == "admin":
                    if st.button("🗑️", key=f"del_cons_{record_id}", help="Удалить запись"):
                        delete_consumption_record(record_id)
                        st.success(f"✅ Запись удалена!")
                        st.rerun()
            with col3:
                if role == "admin" and photo and os.path.exists(photo):
                    if st.button("📷", key=f"view_photo2_{record_id}"):
                        st.image(photo, caption="Фото", use_container_width=True)
        st.caption("🗑️ — удалить запись")

with tab5:
    st.subheader("🏠 Управление помещениями")
    if st.session_state.get("selected_room"):
        room_name = st.session_state.selected_room
        st.markdown(f"### 📦 Содержимое помещения **{room_name}**")
        items_in_room = get_items_by_room(room_name)
        if items_in_room:
            for item in items_in_room:
                if len(item) >= 14:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo = item[:14]
                else:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item[:12]
                    application = ""
                try:
                    qty = float(quantity)
                except:
                    qty = 0
                status = "🔴" if qty <= 0 else "🟡" if qty <= threshold else "🟢"
                st.write(f"{status} **{name}** — {qty} {unit} ({location})" + (f"  📝 {application}" if application else ""))
        else:
            st.info(f"🌱 В помещении '{room_name}' пока нет вещей")
        if st.button("⬅️ Назад"):
            st.session_state.selected_room = None
            st.rerun()
        st.divider()
    
    if role == "admin":
        with st.form("add_room_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_room = st.text_input("Название нового помещения", placeholder="Гараж, Склад, Мастерская...")
            with col2:
                st.write("")
                st.write("")
                add_room_btn = st.form_submit_button("➕ Добавить")
            if add_room_btn and new_room:
                success, msg = add_room(new_room)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        st.divider()
    
    rooms = get_rooms()
    if not rooms:
        st.info("🌱 Пока нет помещений")
    else:
        st.caption(f"Всего помещений: {len(rooms)}")
        for room_id, room_name, room_date in rooms:
            items_in_room = get_items_by_room(room_name)
            count = len(items_in_room)
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"🏠 **{room_name}** — {count} вещей")
                st.caption(f"Добавлено: {room_date[:10]}")
            with col2:
                if st.button("📦 Открыть", key=f"room_open_{room_id}"):
                    st.session_state.selected_room = room_name
                    st.rerun()
            with col3:
                if role == "admin" and st.button("🗑️", key=f"del_room_{room_id}"):
                    delete_room(room_id)
                    st.rerun()
