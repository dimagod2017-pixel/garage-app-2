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
EMAIL_PASSWORD = "ТВОЙ_ПАРОЛЬ_ОТ_ПОЧТЫ"
EMAIL_RECIPIENT = "Yvedomlenie-scald.sad@yandex.ru"
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 587

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
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

def login_page():
    st.markdown("""
        <style>
            .login-container {
                max-width: 400px;
                margin: 100px auto;
                padding: 2rem;
                background: linear-gradient(135deg, #f5f5f5, #e0e0e0);
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
            }
            .login-title {
                font-size: 2.5rem;
                font-weight: bold;
                color: #2E7D32;
                margin-bottom: 1rem;
            }
            .login-subtitle {
                font-size: 1.1rem;
                color: #666;
                margin-bottom: 2rem;
            }
            .login-icon {
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            input[type="password"] {
                -webkit-text-security: disc !important;
                font-size: 1.2rem !important;
                letter-spacing: 4px !important;
                text-align: center;
                padding: 10px !important;
            }
            input[type="password"]:focus {
                outline: 2px solid #4CAF50 !important;
                border-color: #4CAF50 !important;
            }
            .stButton button {
                background: linear-gradient(135deg, #4CAF50, #2E7D32) !important;
                color: white !important;
                border: none !important;
                border-radius: 10px !important;
                padding: 10px 30px !important;
                font-size: 1.1rem !important;
                font-weight: bold !important;
                transition: all 0.3s;
            }
            .stButton button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
            }
            .login-footer {
                margin-top: 1rem;
                color: #999;
                font-size: 0.8rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-icon">🌿</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Мой Склад</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Система учета запчастей и материалов</div>', unsafe_allow_html=True)
        
        password = st.text_input(
            "Введите пароль",
            type="password",
            key="login_password",
            placeholder="Введите пароль здесь",
            label_visibility="collapsed"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔓 Войти", use_container_width=True):
                if password in USERS:
                    st.session_state.user = USERS[password]
                    st.session_state.user["password"] = password
                    st.query_params["user"] = password
                    st.rerun()
                else:
                    st.error("❌ Неверный пароль!")
        with col_b:
            if st.button("🔄 Сброс", use_container_width=True):
                st.session_state.login_password = ""
                st.rerun()
        
        st.markdown('<div class="login-footer">🔐 Доступ только для авторизованных пользователей</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.user is None:
    if "user" in st.query_params:
        saved_user = st.query_params["user"]
        if saved_user in USERS:
            st.session_state.user = USERS[saved_user]
            st.session_state.user["password"] = saved_user
    
    if st.session_state.user is None:
        login_page()
        st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

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
if "photo_index" not in st.session_state:
    st.session_state.photo_index = {}

with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    
    col1, col2 = st.columns(2)
    with col1:
        dark_mode_toggle = st.toggle("🌙 Тёмная тема", value=st.session_state.dark_mode)
        if dark_mode_toggle != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode_toggle
            st.rerun()
    with col2:
        if st.button("🚪 Выйти"):
            st.query_params.clear()
            st.session_state.user = None
            st.rerun()
    
    st.divider()

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
        </style>
    """, unsafe_allow_html=True)

if not os.path.exists("images"):
    os.makedirs("images")

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

def search_equipment(query):
    if not query:
        return []
    
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    results = []
    
    words = query.strip().split()
    
    equipment_conditions = []
    equipment_params = []
    for word in words:
        word_pattern = f'%{word}%'
        equipment_conditions.append("(name LIKE ? OR number LIKE ?)")
        equipment_params.extend([word_pattern, word_pattern])
    
    if equipment_conditions:
        where_clause = " AND ".join(equipment_conditions)
        c.execute(f"""
            SELECT 'equipment' as type, id, name, number, date_added, NULL as unit_name, NULL as unit_id
            FROM equipment 
            WHERE {where_clause}
        """, equipment_params)
        equipment_results = c.fetchall()
        results.extend(equipment_results)
    
    unit_conditions = []
    unit_params = []
    for word in words:
        word_pattern = f'%{word}%'
        unit_conditions.append("(u.name LIKE ? OR e.name LIKE ? OR e.number LIKE ?)")
        unit_params.extend([word_pattern, word_pattern, word_pattern])
    
    if unit_conditions:
        where_clause = " AND ".join(unit_conditions)
        c.execute(f"""
            SELECT 'unit' as type, e.id as eq_id, e.name as eq_name, e.number, e.date_added, u.name as unit_name, u.id as unit_id
            FROM units u
            JOIN equipment e ON u.equipment_id = e.id
            WHERE {where_clause}
        """, unit_params)
        unit_results = c.fetchall()
        results.extend(unit_results)
    
    conn.close()
    return results

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

def consume_item(item_id, quantity, object_name, user="Пользователь", photo_path="", status="pending"):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit, name FROM items WHERE id = ?", (item_id,))
    result = c.fetchone()
    if result is None:
        conn.close()
        return False, "Вещь не найдена"
    current_q, unit, item_name = result
    if quantity > current_q:
        conn.close()
        return False, f"Недостаточно! Есть {current_q} {unit}"
    new_q = current_q - quantity
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_q, item_id))
    c.execute("INSERT INTO consumption (item_id, quantity, unit, object_name, user, date, status, photo) VALUES (?,?,?,?,?,?,?,?)",
              (item_id, quantity, unit, object_name, user, datetime.now().strftime("%Y-%m-%d %H:%M"), status, photo_path))
    conn.commit()
    conn.close()
    
    if role == "admin":
        email_subject = f"📦 Списание: {item_name}"
        email_body = f"""Списание запчасти:
        
Название: {item_name}
Количество: {quantity} {unit}
Объект: {object_name}
Пользователь: {user}
Дата: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Остаток: {new_q} {unit}

Статус: {'✅ Подтверждено' if status == 'confirmed' else '⏳ Ожидает подтверждения'}
"""
        send_email(email_subject, email_body)
    
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

def update_item_location(item_id, new_location):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET location = ? WHERE id = ?", (new_location, item_id))
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
    if room_filter and room_filter != "Все помещения":
        c.execute("""
            SELECT * FROM items
            WHERE (name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ? OR application LIKE ?)
            AND room = ?
        """, (query_like, query_like, query_like, query_like, query_like, room_filter))
    else:
        c.execute("""
            SELECT * FROM items
            WHERE name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ? OR application LIKE ?
        """, (query_like, query_like, query_like, query_like, query_like))
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

def show_photo_carousel(unique_id, photos):
    if not photos:
        return
    
    if unique_id not in st.session_state.photo_index:
        st.session_state.photo_index[unique_id] = 0
    
    total_photos = len(photos)
    current_index = st.session_state.photo_index[unique_id]
    
    if total_photos > 0:
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col1:
            if st.button("◀", key=f"prev_{unique_id}", use_container_width=True):
                st.session_state.photo_index[unique_id] = (current_index - 1) % total_photos
                st.rerun()
        
        with col2:
            if os.path.exists(photos[current_index]):
                st.image(photos[current_index], use_container_width=True)
                st.caption(f"Фото {current_index + 1} из {total_photos}")
        
        with col3:
            if st.button("▶", key=f"next_{unique_id}", use_container_width=True):
                st.session_state.photo_index[unique_id] = (current_index + 1) % total_photos
                st.rerun()

def show_item_card(item, expanded=False, tab_prefix=""):
    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo, equipment_id, unit_id = item
    
    photos = []
    if item_photo and os.path.exists(item_photo):
        photos.append(item_photo)
    if location_photo and os.path.exists(location_photo):
        photos.append(location_photo)
    if installed_photo and os.path.exists(installed_photo):
        photos.append(installed_photo)
    
    eq_info = ""
    if equipment_id:
        eq = get_equipment_by_id(equipment_id)
        if eq:
            eq_info = f"🚜 {eq[1]}"
            if eq[2]:
                eq_info += f" (№{eq[2]})"
            if unit_id:
                units = get_units(equipment_id)
                for u in units:
                    if u[0] == unit_id:
                        eq_info += f" → 🔧 {u[1]}"
                        break
    
    with st.expander(f"{'🔴' if quantity <= threshold else '🟢'} {name} — {quantity} {unit} | {room} {eq_info}", expanded=expanded):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(f"**Категория:** {category or '—'}")
            st.markdown(f"**Место:** {location}")
            st.markdown(f"**Помещение:** {room}")
            if description:
                st.markdown(f"**Описание:** {description}")
            if application:
                st.markdown(f"**🔧 Применение:** {application}")
            if eq_info:
                st.markdown(f"**Техника:** {eq_info}")
            st.markdown(f"**Добавлено:** {date_added}")
            if quantity <= threshold:
                st.error(f"⚠️ Осталось {quantity} {unit} (порог: {threshold})")
            else:
                st.success(f"✅ В наличии: {quantity} {unit} (порог: {threshold})")
        
        with col2:
            if photos:
                show_photo_carousel(f"{tab_prefix}_{item_id}", photos)
        
        st.divider()
        
        role_prefix = "admin" if role == "admin" else "emp"
        unique_prefix = f"{tab_prefix}_{role_prefix}_{item_id}"
        
        if role == "admin":
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                if st.button("✏️ Редактировать", key=f"{unique_prefix}_edit_btn", use_container_width=True):
                    st.session_state[f"show_edit_{item_id}"] = True
            
            with col_b:
                if st.button("📊 Изменить количество", key=f"{unique_prefix}_qty_btn", use_container_width=True):
                    st.session_state[f"show_qty_{item_id}"] = True
            
            with col_c:
                if st.button("📤 Списать", key=f"{unique_prefix}_consume_btn", use_container_width=True):
                    st.session_state[f"show_consume_{item_id}"] = True
                    st.session_state[f"selected_object_{item_id}"] = ""
            
            with col_d:
                if st.button("🗑️ Удалить", key=f"{unique_prefix}_delete_btn", use_container_width=True):
                    if st.session_state.get(f"confirm_delete_{item_id}"):
                        delete_item(item_id)
                        st.success("🗑️ Вещь удалена!")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_{item_id}"] = True
                        st.warning("Нажмите ещё раз для подтверждения удаления")
                        st.rerun()
        else:
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("📤 Списать", key=f"{unique_prefix}_consume_btn", use_container_width=True):
                    st.session_state[f"show_consume_{item_id}"] = True
                    st.session_state[f"selected_object_{item_id}"] = ""
            
            with col_b:
                if st.button("📍 Переместить", key=f"{unique_prefix}_move_btn", use_container_width=True):
                    st.session_state[f"show_move_{item_id}"] = True
        
        # Модальное окно: Редактирование
        if st.session_state.get(f"show_edit_{item_id}"):
            with st.form(f"edit_form_{unique_prefix}"):
                st.markdown("### ✏️ Редактировать вещь")
                new_name = st.text_input("Название", value=name)
                new_category = st.text_input("Категория", value=category or "")
                new_location = st.text_input("Место", value=location)
                
                room_names = get_room_names()
                if room_names:
                    room_index = room_names.index(room) if room in room_names else 0
                    new_room = st.selectbox("Помещение", room_names, index=room_index)
                else:
                    new_room = room
                
                new_description = st.text_area("Описание", value=description or "")
                new_application = st.text_area("Область применения", value=application or "")
                
                equipment_list = get_equipment()
                if equipment_list:
                    eq_options = ["Не выбрано"] + [eq[1] for eq in equipment_list]
                    current_eq_index = 0
                    if equipment_id:
                        for i, eq in enumerate(equipment_list):
                            if eq[0] == equipment_id:
                                current_eq_index = i + 1
                                break
                    new_selected_eq = st.selectbox("Техника", eq_options, index=current_eq_index)
                    
                    if new_selected_eq != "Не выбрано":
                        new_eq_id = [eq[0] for eq in equipment_list if eq[1] == new_selected_eq][0]
                        units = get_units
