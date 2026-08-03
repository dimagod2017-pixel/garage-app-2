import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from PIL import Image
import pandas as pd
from io import BytesIO
import qrcode
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# --- НАСТРОЙКА ПОЧТЫ (ВСТАВЬТЕ СВОИ ДАННЫЕ) ---
EMAIL_SENDER = "Yvedomlenie-scald.sad@yandex.ru"
EMAIL_PASSWORD = "bpzhkwtwimhurhkt"  # ВАШ ПАРОЛЬ
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

# --- ПАРОЛИ И РОЛИ ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.sidebar.title("🔐 Вход")
    
    if st.session_state.user is not None:
        return
    
    password = st.sidebar.text_input("Введите пароль:", type="password", key="login_password")
    
    col1, col2 = st.sidebar.columns([2, 1])
    with col1:
        if st.button("🔓 Войти", use_container_width=True):
            if password in USERS:
                st.session_state.user = USERS[password]
                st.query_params["user"] = password
                st.rerun()
            else:
                st.sidebar.error("❌ Неверный пароль!")

if "user" in st.query_params:
    saved_user = st.query_params["user"]
    if saved_user in USERS and st.session_state.user is None:
        st.session_state.user = USERS[saved_user]

if st.session_state.user is None:
    login()
    st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

st.title("🌿 Мой Склад")
st.caption(f"👋 Добро пожаловать, {user_name}!")

if st.sidebar.button("🚪 Выйти"):
    st.query_params.clear()
    st.session_state.user = None
    st.rerun()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, category TEXT, location TEXT, 
                  room TEXT, description TEXT, item_photo TEXT, location_photo TEXT, 
                  date_added TEXT, quantity REAL, unit TEXT, threshold INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, quantity REAL, 
                  unit TEXT, object_name TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending', photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, number TEXT, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS units
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, equipment_id INTEGER, date_added TEXT)''')
    conn.commit()
    conn.close()

# --- ФУНКЦИИ ---
def get_rooms():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rooms ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def get_room_names():
    return [room[1] for room in get_rooms()]

def add_item(name, category, location, room, description, quantity, unit, threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("""INSERT INTO items 
                 (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (item_id, name, category, location, room, description, "", "", 
               datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold))
    conn.commit()
    conn.close()
    return item_id

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM items ORDER BY date_added DESC")
    results = c.fetchall()
    conn.close()
    return results

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

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

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

def get_equipment():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def delete_equipment(equipment_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
    conn.commit()
    conn.close()

def get_units(equipment_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM units WHERE equipment_id = ? ORDER BY name", (equipment_id,))
    results = c.fetchall()
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
        return False, f"Агрегат '{name}' уже существует"

def delete_unit(unit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM units WHERE id = ?", (unit_id,))
    conn.commit()
    conn.close()

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
    if result and result[2] == "confirmed":
        c.execute("UPDATE items SET quantity = quantity + ? WHERE id = ?", (result[1], result[0]))
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
                 WHERE c.object_name LIKE ? ORDER BY c.date DESC""", (f'%{eq_name}%',))
    results = c.fetchall()
    conn.close()
    return results

def search_items(query, room_filter=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    query_like = f"%{query}%"
    if room_filter and room_filter != "Все помещения":
        c.execute("SELECT * FROM items WHERE (name LIKE ?) AND room = ?", (query_like, room_filter))
    else:
        c.execute("SELECT * FROM items WHERE name LIKE ?", (query_like,))
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

# Уведомления
if role == "admin":
    low_items = get_low_stock_items()
    if low_items:
        st.warning(f"⚠️ {len(low_items)} вещей требуют пополнения!")
        for item in low_items:
            st.write(f"• {item[1]} — {item[9]} {item[10]}")

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
    
    # Добавление вещи (только админ)
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
                    add_item(name, category, location, room, description, quantity, unit, threshold)
                    st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
                    st.rerun()
                else:
                    st.error("⚠️ Название, Помещение и Место обязательны!")
        st.divider()

# --- ВКЛАДКИ ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📤 Списания", "🏠 Помещения"])

with tab1:
    st.subheader("🔍 Поиск")
    search_query = st.text_input("Что ищем?")
    rooms = ["Все помещения"] + get_room_names()
    room_filter = st.selectbox("🏠 Помещение", rooms)
    
    if search_query:
        items = search_items(search_query, room_filter)
        for item in items:
            st.write(f"• {item[1]} — {item[9]} {item[10]}")

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
                "Порог": item[11]
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

with tab3:
    st.subheader("🚜 Парк")
    if role == "admin":
        with st.form("add_eq", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                eq_name = st.text_input("Название техники")
            with col2:
                st.write("")
                if st.form_submit_button("➕ Добавить"):
                    if eq_name:
                        success, msg = add_equipment(eq_name)
                        st.success(msg) if success else st.error(msg)
    
    equipment = get_equipment()
    for eq in equipment:
        st.write(f"🚜 {eq[1]}")

with tab4:
    st.subheader("📤 История списаний")
    all_cons = get_all_consumption()
    for c in all_cons:
        st.write(f"{c[7]} → {c[2]} {c[3]}")

with tab5:
    st.subheader("🏠 Помещения")
    if role == "admin":
        with st.form("add_room", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_room = st.text_input("Название помещения")
            with col2:
                st.write("")
                if st.form_submit_button("➕ Добавить"):
                    if new_room:
                        success, msg = add_room(new_room)
                        st.success(msg) if success else st.error(msg)
    
    rooms = get_rooms()
    for room in rooms:
        st.write(f"🏠 {room[1]}")

st.caption("📱 Мой Склад v2.0")
