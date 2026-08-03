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
if "photo_index" not in st.session_state:
    st.session_state.photo_index = {}
if "show_low_stock" not in st.session_state:
    st.session_state.show_low_stock = False

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
    
    # Счетчики заявок
    if role == "admin":
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM requests WHERE status = 'pending'")
            pending_count = c.fetchone()[0]
            if pending_count > 0:
                st.sidebar.warning(f"🔔 Новых заявок: {pending_count}")
        except:
            pass
        conn.close()
    else:
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM requests WHERE user = ? AND status = 'approved' AND seen = 0", (user_name,))
            approved_count = c.fetchone()[0]
            if approved_count > 0:
                st.sidebar.success(f"✅ Одобрено заявок: {approved_count}")
        except:
            pass
        conn.close()

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
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  quantity REAL,
                  unit TEXT,
                  description TEXT,
                  photo TEXT,
                  user TEXT,
                  date TEXT,
                  status TEXT DEFAULT 'pending',
                  seen INTEGER DEFAULT 0,
                  admin_comment TEXT)''')
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
    
    query_like = f"%{query}%"
    query_lower = f"%{query.lower()}%"
    query_upper = f"%{query.upper()}%"
    
    c.execute("""
        SELECT 'equipment' as type, id, name, number, date_added, NULL as unit_name, NULL as unit_id
        FROM equipment 
        WHERE name LIKE ? OR name LIKE ? OR name LIKE ?
           OR number LIKE ? OR number LIKE ? OR number LIKE ?
        ORDER BY name
    """, (query_like, query_lower, query_upper,
          query_like, query_lower, query_upper))
    equipment_results = c.fetchall()
    results.extend(equipment_results)
    
    c.execute("""
        SELECT 'unit' as type, e.id as eq_id, e.name as eq_name, e.number, e.date_added, u.name as unit_name, u.id as unit_id
        FROM units u
        JOIN equipment e ON u.equipment_id = e.id
        WHERE u.name LIKE ? OR u.name LIKE ? OR u.name LIKE ?
           OR e.name LIKE ? OR e.name LIKE ? OR e.name LIKE ?
           OR e.number LIKE ? OR e.number LIKE ? OR e.number LIKE ?
        ORDER BY e.name, u.name
    """, (query_like, query_lower, query_upper,
          query_like, query_lower, query_upper,
          query_like, query_lower, query_upper))
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
    query_lower = f"%{query.lower()}%"
    query_upper = f"%{query.upper()}%"
    
    if room_filter and room_filter != "Все помещения":
        c.execute("""
            SELECT * FROM items
            WHERE (name LIKE ? OR name LIKE ? OR name LIKE ?
                   OR category LIKE ? OR category LIKE ? OR category LIKE ?
                   OR location LIKE ? OR location LIKE ? OR location LIKE ?
                   OR room LIKE ? OR room LIKE ? OR room LIKE ?
                   OR description LIKE ? OR description LIKE ? OR description LIKE ?
                   OR application LIKE ? OR application LIKE ? OR application LIKE ?
                   OR CAST(quantity AS TEXT) LIKE ? OR CAST(quantity AS TEXT) LIKE ? OR CAST(quantity AS TEXT) LIKE ?
                   OR unit LIKE ? OR unit LIKE ? OR unit LIKE ?)
            AND room = ?
            ORDER BY 
                CASE WHEN name LIKE ? THEN 1 ELSE 2 END,
                name ASC
        """, (query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              room_filter, query_like))
    else:
        c.execute("""
            SELECT * FROM items
            WHERE name LIKE ? OR name LIKE ? OR name LIKE ?
               OR category LIKE ? OR category LIKE ? OR category LIKE ?
               OR location LIKE ? OR location LIKE ? OR location LIKE ?
               OR room LIKE ? OR room LIKE ? OR room LIKE ?
               OR description LIKE ? OR description LIKE ? OR description LIKE ?
               OR application LIKE ? OR application LIKE ? OR application LIKE ?
               OR CAST(quantity AS TEXT) LIKE ? OR CAST(quantity AS TEXT) LIKE ? OR CAST(quantity AS TEXT) LIKE ?
               OR unit LIKE ? OR unit LIKE ? OR unit LIKE ?
            ORDER BY 
                CASE WHEN name LIKE ? THEN 1 ELSE 2 END,
                name ASC
        """, (query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like, query_lower, query_upper,
              query_like))
    
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

def add_request(name, quantity, unit, description, photo_path, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO requests (name, quantity, unit, description, photo, user, date) VALUES (?,?,?,?,?,?,?)",
              (name, quantity, unit, description, photo_path, user, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return True

def get_requests(status=None, user=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if status and user:
        c.execute("SELECT * FROM requests WHERE status = ? AND user = ? ORDER BY date DESC", (status, user))
    elif status:
        c.execute("SELECT * FROM requests WHERE status = ? ORDER BY date DESC", (status,))
    elif user:
        c.execute("SELECT * FROM requests WHERE user = ? ORDER BY date DESC", (user,))
    else:
        c.execute("SELECT * FROM requests ORDER BY date DESC")
    results = c.fetchall()
    conn.close()
    return results

def update_request_status(request_id, status, admin_comment=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET status = ?, admin_comment = ?, seen = 0 WHERE id = ?", 
              (status, admin_comment, request_id))
    conn.commit()
    conn.close()
    return True

def mark_request_seen(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET seen = 1 WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

def delete_request(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT photo FROM requests WHERE id = ?", (request_id,))
    result = c.fetchone()
    if result and result[0] and os.path.exists(result[0]):
        os.remove(result[0])
    c.execute("DELETE FROM requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

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
        
        # Модальные окна (редактирование, количество, списание, перемещение)
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
                        units = get_units(new_eq_id)
                        if units:
                            unit_options = ["Не выбрано"] + [u[1] for u in units]
                            current_unit_index = 0
                            if unit_id:
                                for i, u in enumerate(units):
                                    if u[0] == unit_id:
                                        current_unit_index = i + 1
                                        break
                            new_selected_unit = st.selectbox("Агрегат", unit_options, index=current_unit_index)
                            if new_selected_unit != "Не выбрано":
                                new_unit_id = [u[0] for u in units if u[1] == new_selected_unit][0]
                            else:
                                new_unit_id = None
                        else:
                            new_unit_id = None
                    else:
                        new_eq_id = None
                        new_unit_id = None
                else:
                    new_eq_id = None
                    new_unit_id = None
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Сохранить"):
                        update_item(item_id, new_name, new_category, new_location, new_room, new_description, new_application, new_eq_id, new_unit_id)
                        st.session_state[f"show_edit_{item_id}"] = False
                        st.success("✅ Изменения сохранены!")
                        st.rerun()
                with col2:
                    if st.form_submit_button("❌ Отмена"):
                        st.session_state[f"show_edit_{item_id}"] = False
                        st.rerun()
        
        if st.session_state.get(f"show_qty_{item_id}"):
            with st.form(f"qty_form_{unique_prefix}"):
                st.markdown("### 📊 Изменить количество")
                new_qty = st.number_input("Новое количество", value=float(quantity), min_value=0.0, step=0.5)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Сохранить"):
                        update_quantity(item_id, new_qty)
                        st.session_state[f"show_qty_{item_id}"] = False
                        st.success(f"✅ Количество обновлено: {new_qty} {unit}")
                        st.rerun()
                with col2:
                    if st.form_submit_button("❌ Отмена"):
                        st.session_state[f"show_qty_{item_id}"] = False
                        st.rerun()
        
        if st.session_state.get(f"show_consume_{item_id}"):
            st.markdown("### 📤 Списать со склада")
            
            st.markdown("**🔍 Поиск техники/агрегата:**")
            search_query = st.text_input(
                "Введите название или номер техники", 
                placeholder="Например: МТЗ, 1234", 
                key=f"search_eq_{unique_prefix}"
            )
            
            if f"selected_object_{item_id}" not in st.session_state:
                st.session_state[f"selected_object_{item_id}"] = ""
            
            if search_query:
                search_results = search_equipment(search_query)
                if search_results:
                    options = ["Выберите из списка..."]
                    for result in search_results:
                        if result[0] == 'equipment':
                            label = f"🚜 {result[2]}" + (f" (№{result[3]})" if result[3] else "")
                            options.append(label)
                        else:
                            label = f"🔧 {result[5]} → 🚜 {result[2]}" + (f" (№{result[3]})" if result[3] else "")
                            options.append(label)
                    
                    selected = st.selectbox(
                        "Выберите технику/агрегат", 
                        options,
                        key=f"select_eq_{unique_prefix}"
                    )
                    
                    if selected and selected != "Выберите из списка...":
                        st.session_state[f"selected_object_{item_id}"] = selected
                else:
                    st.info("Ничего не найдено. Введите вручную:")
                    manual_input = st.text_input(
                        "На что списываем*", 
                        value=st.session_state[f"selected_object_{item_id}"],
                        key=f"manual_obj_{unique_prefix}"
                    )
                    if manual_input:
                        st.session_state[f"selected_object_{item_id}"] = manual_input
            else:
                manual_input = st.text_input(
                    "На что списываем*", 
                    value=st.session_state[f"selected_object_{item_id}"],
                    placeholder="Введите вручную или начните поиск",
                    key=f"manual_obj_{unique_prefix}"
                )
                if manual_input:
                    st.session_state[f"selected_object_{item_id}"] = manual_input
            
            with st.form(f"consume_form_{unique_prefix}"):
                consume_qty = st.number_input("Количество", min_value=0.1, max_value=float(quantity), value=1.0, step=0.5)
                consume_photo = st.file_uploader("📷 Фото (опционально)", type=["jpg", "jpeg", "png"], key=f"consume_photo_{unique_prefix}")
                
                object_name = st.session_state[f"selected_object_{item_id}"]
                if object_name:
                    st.info(f"Будет списано на: **{object_name}**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Списать"):
                        if object_name:
                            photo_path = ""
                            if consume_photo:
                                ext = consume_photo.name.split('.')[-1]
                                photo_path = f"images/consume_{uuid.uuid4()}.{ext}"
                                with open(photo_path, "wb") as f:
                                    f.write(consume_photo.getbuffer())
                            
                            status = "confirmed" if role == "admin" else "pending"
                            success, msg = consume_item(item_id, consume_qty, object_name, user_name, photo_path, status)
                            if success:
                                st.session_state[f"show_consume_{item_id}"] = False
                                st.session_state[f"selected_object_{item_id}"] = ""
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.error("Укажите объект списания!")
                with col2:
                    if st.form_submit_button("❌ Отмена"):
                        st.session_state[f"show_consume_{item_id}"] = False
                        st.session_state[f"selected_object_{item_id}"] = ""
                        st.rerun()
        
        if st.session_state.get(f"show_move_{item_id}"):
            with st.form(f"move_form_{unique_prefix}"):
                st.markdown("### 📍 Переместить вещь")
                st.info(f"Текущее местоположение: **{room}** → **{location}**")
                
                room_names = get_room_names()
                if room_names:
                    room_index = room_names.index(room) if room in room_names else 0
                    new_room = st.selectbox("Новое помещение", room_names, index=room_index)
                else:
                    new_room = room
                
                new_location = st.text_input("Новое место внутри помещения*", value=location)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Переместить"):
                        if new_location:
                            update_item_room(item_id, new_room)
                            update_item_location(item_id, new_location)
                            st.session_state[f"show_move_{item_id}"] = False
                            st.success(f"✅ Перемещено в: {new_room} → {new_location}")
                            st.rerun()
                        else:
                            st.error("Укажите новое место!")
                with col2:
                    if st.form_submit_button("❌ Отмена"):
                        st.session_state[f"show_move_{item_id}"] = False
                        st.rerun()

init_db()

st.title("🌿 Мой Склад")
st.caption(f"👋 Добро пожаловать, {user_name}! {('🔑 Администратор' if role == 'admin' else '🔧 Сотрудник')}")

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

total_items, total_rooms, low_stock_count, top_categories, total_equipment, total_rooms_list, total_consumption = get_statistics()

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    if st.button("📦\n" + str(total_items) + "\nВещи", use_container_width=True, key="stat_items"):
        st.session_state.active_tab = 1
        st.rerun()

with col2:
    if st.button("🏠\n" + str(total_rooms_list) + "\nПомещения", use_container_width=True, key="stat_rooms"):
        st.session_state.active_tab = 5
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

with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    st.divider()
    
    if role == "admin":
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
        st.info("Импорт пока в разработке")
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📤 Списания", "📝 Заявки", "🏠 Помещения"])

with tab1:
    if st.session_state.active_tab == 0:
        st.markdown("### 🔍 Поиск и списание")
    
    room_names = get_room_names()
    room_filter = st.selectbox("🏠 Фильтр по помещению", ["Все помещения"] + room_names, key="search_room_filter")
    
    if st.session_state.show_low_stock:
        st.info("⚠️ Показаны позиции с низким остатком")
        items = get_low_stock_items()
        st.session_state.show_low_stock = False
    else:
        search_query = st.text_input("🔍 Поиск по названию, категории, месту, описанию, применению", key="search_query")
        if search_query:
            items = search_items(search_query, room_filter)
            if items:
                st.success(f"Найдено: {len(items)} позиций")
        else:
            items = get_all_items(room_filter)
    
    if items:
        for item in items:
            show_item_card(item, expanded=item[9] <= item[11], tab_prefix="tab1")
    else:
        st.info("Ничего не найдено. Добавьте вещи через боковую панель.")

with tab2:
    st.markdown("### 📋 Все вещи")
    
    room_names = get_room_names()
    room_filter_all = st.selectbox("🏠 Фильтр по помещению", ["Все помещения"] + room_names, key="all_room_filter")
    
    items = get_all_items(room_filter_all)
    
    if items:
        for item in items:
            show_item_card(item, tab_prefix="tab2")
    else:
        st.info("Склад пуст. Добавьте вещи через боковую панель.")

with tab3:
    st.markdown("### 🚜 Парк техники и оборудования")
    
    if role == "admin":
        st.subheader("➕ Добавить технику")
        with st.form("add_equipment_form"):
            col1, col2 = st.columns(2)
            with col1:
                eq_name = st.text_input("Название техники*", placeholder="Например: Трактор МТЗ-80")
            with col2:
                eq_number = st.text_input("Номер/инвентарный номер", placeholder="Например: 1234 АВ")
            if st.form_submit_button("💾 Добавить технику"):
                if eq_name:
                    success, msg = add_equipment(eq_name, eq_number)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                    st.rerun()
                else:
                    st.error("Название обязательно!")
        
        st.divider()
        
        st.subheader("✏️ Редактировать технику")
        equipment_list = get_equipment()
        if equipment_list:
            eq_names = [eq[1] for eq in equipment_list]
            selected_eq_edit = st.selectbox("Выберите технику", eq_names, key="edit_eq_select")
            
            if selected_eq_edit:
                eq = [e for e in equipment_list if e[1] == selected_eq_edit][0]
                with st.form("edit_equipment_form"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        new_eq_name = st.text_input("Название", value=eq[1])
                    with col2:
                        new_eq_number = st.text_input("Номер", value=eq[2] or "")
                    with col3:
                        if st.form_submit_button("💾 Сохранить"):
                            update_equipment(eq[0], new_eq_name, new_eq_number)
                            st.success("✅ Обновлено!")
                            st.rerun()
                    
                    if st.form_submit_button("🗑️ Удалить технику"):
                        delete_equipment(eq[0])
                        st.success("🗑️ Техника удалена!")
                        st.rerun()
        
        st.divider()
        
        st.subheader("🔧 Агрегаты и узлы")
        if equipment_list:
            eq_names = ["Выберите технику"] + [eq[1] for eq in equipment_list]
            selected_eq_for_units = st.selectbox("Техника для агрегатов", eq_names)
            
            if selected_eq_for_units != "Выберите технику":
                eq_id = [eq[0] for eq in equipment_list if eq[1] == selected_eq_for_units][0]
                
                with st.form("add_unit_form"):
                    unit_name = st.text_input("Название агрегата/узла*", placeholder="Например: Двигатель, Генератор")
                    if st.form_submit_button("➕ Добавить агрегат"):
                        if unit_name:
                            success, msg = add_unit(unit_name, eq_id)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                            st.rerun()
                        else:
                            st.error("Название обязательно!")
                
                units = get_units(eq_id)
                if units:
                    st.markdown("**Существующие агрегаты:**")
                    for unit in units:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"🔧 {unit[1]}")
                        with col2:
                            if st.button("🗑️", key=f"del_unit_{unit[0]}"):
                                delete_unit(unit[0])
                                st.rerun()
                else:
                    st.info("Нет агрегатов для этой техники")
        else:
            st.info("Сначала добавьте технику")
    
    st.divider()
    st.subheader("📋 Обзор парка")
    equipment_list = get_equipment()
    if equipment_list:
        for eq in equipment_list:
            with st.expander(f"🚜 {eq[1]}" + (f" (№{eq[2]})" if eq[2] else "")):
                units = get_units(eq[0])
                if units:
                    st.markdown("**Агрегаты и узлы:**")
                    for unit in units:
                        st.write(f"  🔧 {unit[1]}")
                else:
                    st.caption("Нет агрегатов")
                
                conn = sqlite3.connect('storage.db')
                c = conn.cursor()
                c.execute("SELECT * FROM items WHERE equipment_id = ?", (eq[0],))
                items = c.fetchall()
                conn.close()
                
                if items:
                    st.markdown(f"**Запчасти ({len(items)}):**")
                    for item in items:
                        unit_info = ""
                        if item[15]:
                            for u in units:
                                if u[0] == item[15]:
                                    unit_info = f" → {u[1]}"
                                    break
                        st.write(f"  {'🔴' if item[9] <= item[11] else '🟢'} {item[1]} — {item[9]} {item[10]}{unit_info}")
                else:
                    st.caption("Нет связанных запчастей")
    else:
        st.info("Парк техники пуст")

with tab4:
    st.markdown("### 📤 История списаний")
    
    if role == "admin":
        tab4_1, tab4_2 = st.tabs(["📋 Все списания", "⏳ На подтверждении"])
        
        with tab4_1:
            consumption = get_all_consumption()
            if consumption:
                for record in consumption:
                    record_id, item_id, qty, unit, object_name, user, date, status, photo, item_name = record
                    
                    status_icon = {"confirmed": "✅", "pending": "⏳"}.get(status, "❓")
                    status_text = {"confirmed": "Подтверждено", "pending": "Ожидает"}.get(status, status)
                    
                    with st.expander(f"{status_icon} {item_name} — {qty} {unit} → {object_name} | {date}"):
                        st.markdown(f"**Пользователь:** {user}")
                        st.markdown(f"**Статус:** {status_text}")
                        st.markdown(f"**Объект:** {object_name}")
                        if photo and os.path.exists(photo):
                            st.image(photo, caption="Фото списания", width=200)
                        
                        if st.button("🗑️ Удалить запись", key=f"del_cons_{record_id}"):
                            delete_consumption_record(record_id)
                            st.success("Запись удалена!")
                            st.rerun()
            else:
                st.info("История списаний пуста")
        
        with tab4_2:
            pending = get_pending_consumption()
            if pending:
                for record in pending:
                    record_id, item_id, qty, unit, object_name, user, date, status, photo, item_name = record
                    
                    with st.expander(f"⏳ {item_name} — {qty} {unit} → {object_name} | {date}"):
                        st.markdown(f"**Пользователь:** {user}")
                        st.markdown(f"**Объект:** {object_name}")
                        if photo and os.path.exists(photo):
                            st.image(photo, caption="Фото списания", width=200)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Подтвердить", key=f"approve_{record_id}"):
                                approve_consumption(record_id)
                                st.success("Списание подтверждено!")
                                st.rerun()
                        with col2:
                            if st.button("❌ Отклонить", key=f"reject_{record_id}"):
                                delete_consumption_record(record_id)
                                st.success("Списание отклонено!")
                                st.rerun()
            else:
                st.info("Нет списаний на подтверждении")
    else:
        consumption = get_all_consumption()
        if consumption:
            for record in consumption:
                record_id, item_id, qty, unit, object_name, user, date, status, photo, item_name = record
                
                status_icon = {"confirmed": "✅", "pending": "⏳"}.get(status, "❓")
                status_text = {"confirmed": "Подтверждено", "pending": "Ожидает"}.get(status, status)
                
                with st.expander(f"{status_icon} {item_name} — {qty} {unit} → {object_name} | {date}"):
                    st.markdown(f"**Пользователь:** {user}")
                    st.markdown(f"**Статус:** {status_text}")
                    st.markdown(f"**Объект:** {object_name}")
                    if photo and os.path.exists(photo):
                        st.image(photo, caption="Фото списания", width=200)
        else:
            st.info("История списаний пуста")

with tab5:
    st.markdown("### 📝 Заявки на пополнение")
    
    if role == "employee":
        st.subheader("➕ Создать заявку")
        with st.form("request_form", clear_on_submit=True):
            req_name = st.text_input("Название*", placeholder="Что нужно закупить?")
            col1, col2 = st.columns(2)
            with col1:
                req_qty = st.number_input("Количество", min_value=0.1, step=0.5, value=1.0)
            with col2:
                req_unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект", "упаковка", "м²", "другой"])
                if req_unit == "другой":
                    req_unit = st.text_input("Своя единица")
            req_desc = st.text_area("Описание/примечание", placeholder="Для чего нужно, срочность и т.д.")
            req_photo = st.file_uploader("📷 Фото (опционально)", type=["jpg", "jpeg", "png"])
            
            if st.form_submit_button("📤 Отправить заявку"):
                if req_name:
                    photo_path = ""
                    if req_photo:
                        ext = req_photo.name.split('.')[-1]
                        photo_path = f"images/request_{uuid.uuid4()}.{ext}"
                        with open(photo_path, "wb") as f:
                            f.write(req_photo.getbuffer())
                    
                    add_request(req_name, req_qty, req_unit, req_desc, photo_path, user_name)
                    st.success("✅ Заявка отправлена!")
                    
                    send_email(
                        "📝 Новая заявка на пополнение",
                        f"Пользователь: {user_name}\n"
                        f"Название: {req_name}\n"
                        f"Количество: {req_qty} {req_unit}\n"
                        f"Описание: {req_desc}\n"
                        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    st.rerun()
                else:
                    st.error("Укажите название!")
        
        st.divider()
        
        st.subheader("📋 Мои заявки")
        my_requests = get_requests(user=user_name)
        
        if my_requests:
            for req in my_requests:
                req_id, name, qty, unit, desc, photo, req_user, date, status, seen, comment = req
                
                status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "❓")
                status_text = {"pending": "На рассмотрении", "approved": "Одобрено", "rejected": "Отклонено"}.get(status, status)
                
                with st.expander(f"{status_icon} {name} — {qty} {unit} | {date}"):
                    st.markdown(f"**Статус:** {status_text}")
                    if desc:
                        st.markdown(f"**Описание:** {desc}")
                    if comment:
                        st.markdown(f"**Комментарий:** {comment}")
                    if photo and os.path.exists(photo):
                        st.image(photo, caption="Фото", width=200)
                    
                    if status == "approved" and seen == 0:
                        if st.button("👁️ Отметить как прочитанное", key=f"seen_{req_id}"):
                            mark_request_seen(req_id)
                            st.rerun()
        else:
            st.info("У вас пока нет заявок")
    
    elif role == "admin":
        tab5_1, tab5_2, tab5_3 = st.tabs(["⏳ Новые", "✅ Одобренные", "❌ Отклоненные"])
        
        with tab5_1:
            pending_requests = get_requests(status="pending")
            if pending_requests:
                for req in pending_requests:
                    req_id, name, qty, unit, desc, photo, req_user, date, status, seen, comment = req
                    
                    with st.expander(f"⏳ {name} — {qty} {unit} | от {req_user} | {date}"):
                        st.markdown(f"**От:** {req_user}")
                        if desc:
                            st.markdown(f"**Описание:** {desc}")
                        if photo and os.path.exists(photo):
                            st.image(photo, caption="Фото", width=200)
                        
                        with st.form(f"approve_{req_id}"):
                            admin_comment = st.text_area("Комментарий", placeholder="Причина отказа или примечание")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.form_submit_button("✅ Одобрить"):
                                    update_request_status(req_id, "approved", admin_comment)
                                    st.success("Заявка одобрена!")
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Отклонить"):
                                    update_request_status(req_id, "rejected", admin_comment)
                                    st.success("Заявка отклонена!")
                                    st.rerun()
                            with col3:
                                if st.form_submit_button("🗑️ Удалить"):
                                    delete_request(req_id)
                                    st.success("Заявка удалена!")
                                    st.rerun()
            else:
                st.info("Нет новых заявок")
        
        with tab5_2:
            approved_requests = get_requests(status="approved")
            if approved_requests:
                for req in approved_requests:
                    req_id, name, qty, unit, desc, photo, req_user, date, status, seen, comment = req
                    
                    with st.expander(f"✅ {name} — {qty} {unit} | от {req_user} | {date}"):
                        st.markdown(f"**От:** {req_user}")
                        if desc:
                            st.markdown(f"**Описание:** {desc}")
                        if comment:
                            st.markdown(f"**Комментарий:** {comment}")
                        if photo and os.path.exists(photo):
                            st.image(photo, caption="Фото", width=200)
                        
                        if st.button("📦 Создать товар из заявки", key=f"create_{req_id}"):
                            st.session_state[f"create_from_request_{req_id}"] = True
                        
                        if st.session_state.get(f"create_from_request_{req_id}"):
                            with st.form(f"create_item_{req_id}"):
                                st.markdown("### 📦 Создать товар")
                                st.info(f"Название: **{name}**, Количество: **{qty} {unit}**")
                                
                                room_names = get_room_names()
                                if room_names:
                                    new_room = st.selectbox("Помещение*", room_names)
                                else:
                                    st.error("Нет помещений!")
                                    new_room = None
                                
                                new_location = st.text_input("Место внутри помещения*")
                                new_category = st.text_input("Категория")
                                new_application = st.text_area("Область применения")
                                
                                equipment_list = get_equipment()
                                if equipment_list:
                                    eq_names = ["Не выбрано"] + [eq[1] for eq in equipment_list]
                                    new_eq = st.selectbox("Техника", eq_names)
                                    if new_eq != "Не выбрано":
                                        new_eq_id = [eq[0] for eq in equipment_list if eq[1] == new_eq][0]
                                        units = get_units(new_eq_id)
                                        if units:
                                            unit_names = ["Не выбрано"] + [u[1] for u in units]
                                            new_unit = st.selectbox("Агрегат", unit_names)
                                            if new_unit != "Не выбрано":
                                                new_unit_id = [u[0] for u in units if u[1] == new_unit][0]
                                            else:
                                                new_unit_id = None
                                        else:
                                            new_unit_id = None
                                    else:
                                        new_eq_id = None
                                        new_unit_id = None
                                else:
                                    new_eq_id = None
                                    new_unit_id = None
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 Сохранить"):
                                        if new_room and new_location:
                                            add_item(name, new_category, new_location, new_room, desc or "", 
                                                    photo if photo and os.path.exists(photo) else "", 
                                                    "", qty, unit, 1, new_application, "", new_eq_id, new_unit_id)
                                            st.success(f"✅ Товар '{name}' создан!")
                                            st.session_state[f"create_from_request_{req_id}"] = False
                                            st.rerun()
                                        else:
                                            st.error("Укажите помещение и место!")
                                with col2:
                                    if st.form_submit_button("❌ Отмена"):
                                        st.session_state[f"create_from_request_{req_id}"] = False
                                        st.rerun()
                        
                        if st.button("🗑️ Удалить заявку", key=f"del_req_{req_id}"):
                            delete_request(req_id)
                            st.success("Заявка удалена!")
                            st.rerun()
            else:
                st.info("Нет одобренных заявок")
        
        with tab5_3:
            rejected_requests = get_requests(status="rejected")
            if rejected_requests:
                for req in rejected_requests:
                    req_id, name, qty, unit, desc, photo, req_user, date, status, seen, comment = req
                    
                    with st.expander(f"❌ {name} — {qty} {unit} | от {req_user} | {date}"):
                        st.markdown(f"**От:** {req_user}")
                        if desc:
                            st.markdown(f"**Описание:** {desc}")
                        if comment:
                            st.markdown(f"**Причина отказа:** {comment}")
                        if photo and os.path.exists(photo):
                            st.image(photo, caption="Фото", width=200)
                        
                        if st.button("🗑️ Удалить", key=f"del_rej_{req_id}"):
                            delete_request(req_id)
                            st.success("Заявка удалена!")
                            st.rerun()
            else:
                st.info("Нет отклоненных заявок")

with tab6:
    st.markdown("### 🏠 Помещения")
    
    if role == "admin":
        st.subheader("➕ Добавить помещение")
        with st.form("add_room_form"):
            room_name = st.text_input("Название помещения*", placeholder="Например: Склад №1, Гараж")
            if st.form_submit_button("💾 Добавить помещение"):
                if room_name:
                    success, msg = add_room(room_name)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                    st.rerun()
                else:
                    st.error("Название обязательно!")
        
        st.divider()
    
    rooms = get_rooms()
    if rooms:
        st.markdown("**Список помещений:**")
        for room in rooms:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"🏠 {room[1]}")
            with col2:
                items_count = len(get_items_by_room(room[1]))
                st.caption(f"📦 {items_count} вещей")
            with col3:
                if role == "admin":
                    if st.button("🗑️", key=f"del_room_{room[0]}"):
                        delete_room(room[0])
                        st.success("Помещение удалено!")
                        st.rerun()
    else:
        st.info("Нет помещений. Добавьте их через форму выше.")
