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

# --- ФУНКЦИЯ ВХОДА ---
def login():
    st.sidebar.title("🔐 Вход")
    
    if st.session_state.user is not None:
        return
    
    password = st.sidebar.text_input("Введите пароль:", type="password")
    
    if st.sidebar.button("🔓 Войти"):
        if password in USERS:
            st.session_state.user = USERS[password]
            st.rerun()
        else:
            st.sidebar.error("❌ Неверный пароль!")

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
    conn.commit()
    conn.close()

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

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
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

def get_statistics():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM items")
    total_items = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM items WHERE quantity <= threshold")
    low_stock_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = c.fetchone()[0]
    conn.close()
    return total_items, low_stock_count, total_rooms

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

init_db()

# --- ИНТЕРФЕЙС ---
total_items, low_stock_count, total_rooms = get_statistics()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📦 Вещи", total_items)
with col2:
    st.metric("🏠 Помещения", total_rooms)
with col3:
    st.metric("⚠️ Пополнить", low_stock_count)

# Уведомления о низких остатках
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
    
    # Тест Email
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
            room = st.selectbox("Помещение*", room_names if room_names else ["— Добавьте помещение —"])
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
    
    st.header("📤 Экспорт")
    if st.button("📥 Скачать данные", use_container_width=True):
        items = get_all_items()
        if items:
            data = []
            for item in items:
                data.append({
                    "Название": item[1],
                    "Категория": item[2] or "",
                    "Место": item[3],
                    "Помещение": item[4],
                    "Количество": f"{item[9]} {item[10]}",
                    "Порог": item[11]
                })
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Скачать CSV",
                data=csv,
                file_name=f"склад_{datetime.now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv"
            )

# --- ВКЛАДКИ ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📤 Списания", "🏠 Помещения"])

# Вкладка 1: Поиск
with tab1:
    st.subheader("🔍 Поиск вещей")
    search_query = st.text_input("Что ищем?", placeholder="Введите название...")
    
    if search_query:
        items = get_all_items()
        found = [item for item in items if search_query.lower() in item[1].lower()]
        if found:
            for item in found:
                st.write(f"• {item[1]} — {item[9]} {item[10]} ({item[4]})")
        else:
            st.info("🌱 Ничего не найдено")

# Вкладка 2: Все вещи
with tab2:
    st.subheader("📋 Все вещи")
    items = get_all_items()
    if not items:
        st.info("🌱 В базе пока нет вещей")
    else:
        data = []
        for item in items:
            data.append({
                "Название": item[1],
                "Категория": item[2] or "",
                "Помещение": item[4],
                "Место": item[3],
                "Количество": f"{item[9]} {item[10]}",
                "Порог": item[11],
                "Статус": "🔴" if item[9] <= 0 else "🟡" if item[9] <= item[11] else "🟢"
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

# Вкладка 3: Парк
with tab3:
    st.subheader("🚜 Управление техникой")
    
    if role == "admin":
        with st.form("add_equipment_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                eq_name = st.text_input("Название техники", placeholder="МТЗ-82")
            with col2:
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
        for eq in equipment:
            st.write(f"🚜 {eq[1]}")

# Вкладка 4: Списания
with tab4:
    st.subheader("📤 История списаний")
    all_cons = get_all_consumption()
    if not all_cons:
        st.info("🌱 Пока нет списаний")
    else:
        for c in all_cons:
            st.write(f"• {c[7]} → {c[2]} {c[3]} на {c[4]} (списал {c[5]})")

# Вкладка 5: Помещения
with tab5:
    st.subheader("🏠 Управление помещениями")
    
    if role == "admin":
        with st.form("add_room_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_room = st.text_input("Название помещения", placeholder="Гараж, Склад...")
            with col2:
                st.write("")
                if st.form_submit_button("➕ Добавить"):
                    if new_room:
                        success, msg = add_room(new_room)
                        st.success(msg) if success else st.error(msg)
                        st.rerun()
    
    rooms = get_rooms()
    if not rooms:
        st.info("🌱 Пока нет помещений")
    else:
        for room in rooms:
            st.write(f"🏠 {room[1]}")

st.caption("📱 Мой Склад v1.0")
