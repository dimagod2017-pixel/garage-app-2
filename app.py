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
    conn.close()
    return total_items, low_stock_count, total_rooms, total_equipment, total_consumption, top_categories

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

# --- ИНТЕРФЕЙС ---
total_items, low_stock_count, total_rooms, total_equipment, total_consumption, top_categories = get_statistics()

# Статистика
col1, col2, col3, col4, col5 = st.columns(5)
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📤 Списания", "🏠 Помещения"])

# --- ВКЛАДКА 1: ПОИСК ---
with tab1:
    st.subheader("🔍 Поиск вещей")
    
    rooms = ["Все помещения"] + get_room_names()
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("🔍 Что ищем?", placeholder="Введите название, категорию, место...")
    with col2:
        room_filter = st.selectbox("🏠 Помещение", rooms)
    
    if search_query:
        items = search_items(search_query, room_filter)
        if items:
            st.subheader(f"📌 Найдено: {len(items)}")
            for item in items:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{item[1]}**")
                        st.caption(f"📍 {item[3]} | 🏠 {item[4]}")
                        st.caption(f"📦 {item[9]} {item[10]}")
                    with col2:
                        if role == "admin":
                            if st.button("🗑️ Удалить", key=f"del_search_{item[0]}"):
                                delete_item(item[0])
                                st.rerun()
        else:
            st.info("🌱 Ничего не найдено")

# --- ВКЛАДКА 2: ВСЕ ВЕЩИ ---
with tab2:
    st.subheader("📋 Все вещи в базе данных")
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
                "Статус": "🔴 Критично" if item[9] <= 0 else "🟡 Скоро" if item[9] <= item[11] else "🟢 Норма",
                "Дата": item[8][:10] if len(item[8]) > 10 else item[8]
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Экспорт CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать таблицу (CSV)",
            data=csv,
            file_name=f"все_вещи_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
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
        if st.button("⬅️ Назад"):
            st.session_state.selected_equipment = None
            st.rerun()
        st.divider()
    
    if role == "admin":
        with st.expander("➕ Добавить технику", expanded=False):
            with st.form("add_equipment_form", clear_on_submit=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    eq_name = st.text_input("Название техники*", placeholder="МТЗ-82, К-700")
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

# --- ВКЛАДКА 4: СПИСАНИЯ (ОБНОВЛЕННАЯ) ---
with tab4:
    st.subheader("📤 История списаний")
    
    # Получаем все списания
    all_cons = get_all_consumption()
    
    if not all_cons:
        st.info("🌱 Пока нет списаний")
    else:
        # Фильтры
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            status_filter = st.selectbox(
                "📊 Статус",
                ["Все", "pending", "confirmed"],
                format_func=lambda x: {
                    "Все": "Все записи",
                    "pending": "⏳ Ожидают подтверждения",
                    "confirmed": "✅ Подтвержденные"
                }.get(x, x)
            )
        with col2:
            users = list(set([c[5] for c in all_cons]))
            user_filter = st.selectbox("👤 Пользователь", ["Все"] + users)
        with col3:
            st.write("")
            st.write("")
            if st.button("🔄 Обновить", use_container_width=True):
                st.rerun()
        
        # Фильтруем
        filtered = all_cons
        if status_filter != "Все":
            filtered = [c for c in filtered if c[7] == status_filter]
        if user_filter != "Все":
            filtered = [c for c in filtered if c[5] == user_filter]
        
        st.caption(f"📌 Найдено записей: {len(filtered)}")
        
        # Показываем каждое списание
        for c in filtered:
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
            
            # Определяем статус
            if status == "pending":
                status_emoji = "⏳"
                status_text = "Ожидает подтверждения"
                status_color = "#FFA726"
            else:
                status_emoji = "✅"
                status_text = "Подтверждено"
                status_color = "#66BB6A"
            
            # Карточка списания
            with st.container(border=True):
                # Заголовок
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
                            if st.button("✅", key=f"approve_{record_id}", help="Подтвердить"):
                                approve_consumption(record_id)
                                st.success("✅ Заявка подтверждена!")
                                st.rerun()
                        with col_btn2:
                            if st.button("❌", key=f"reject_{record_id}", help="Отклонить"):
                                delete_consumption_record(record_id)
                                st.success("❌ Заявка отклонена!")
                                st.rerun()
                
                # Основная информация
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Количество", f"{quantity} {unit}")
                with col2:
                    st.metric("🚗 Объект", object_name)
                with col3:
                    st.metric("👤 Сотрудник", user)
                with col4:
                    st.metric("🕒 Дата", date[:16] if len(date) > 16 else date)
                
                # Кнопка "Подробнее"
                if st.button(f"📋 Подробнее", key=f"details_{record_id}", use_container_width=True):
                    st.session_state[f"show_details_{record_id}"] = not st.session_state.get(f"show_details_{record_id}", False)
                    st.rerun()
                
                # Детальная карточка
                if st.session_state.get(f"show_details_{record_id}", False):
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
                        
                        # Действия для администратора
                        if role == "admin":
                            st.divider()
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("🗑️ Удалить запись", key=f"del_{record_id}", use_container_width=True):
                                    delete_consumption_record(record_id)
                                    st.success("✅ Запись удалена!")
                                    st.rerun()
                            with col2:
                                if status == "pending":
                                    if st.button("✅ Подтвердить", key=f"approve2_{record_id}", use_container_width=True):
                                        approve_consumption(record_id)
                                        st.success("✅ Заявка подтверждена!")
                                        st.rerun()
                            with col3:
                                if st.button("📧 Отправить отчет", key=f"report_{record_id}", use_container_width=True):
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
                        
                        if st.button("✖️ Закрыть", key=f"close_{record_id}", use_container_width=True):
                            st.session_state[f"show_details_{record_id}"] = False
                            st.rerun()
                
                st.divider()

# --- ВКЛАДКА 5: ПОМЕЩЕНИЯ ---
with tab5:
    st.subheader("🏠 Управление помещениями")
    
    if st.session_state.get("selected_room"):
        room_name = st.session_state.selected_room
        st.markdown(f"### 📦 Содержимое помещения **{room_name}**")
        items_in_room = get_items_by_room(room_name)
        if items_in_room:
            for item in items_in_room:
                status = "🔴" if item[9] <= 0 else "🟡" if item[9] <= item[11] else "🟢"
                st.write(f"{status} **{item[1]}** — {item[9]} {item[10]} ({item[3]})")
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
                new_room = st.text_input("Название нового помещения", placeholder="Гараж, Склад...")
            with col2:
                st.write("")
                st.write("")
                if st.form_submit_button("➕ Добавить"):
                    if new_room:
                        success, msg = add_room(new_room)
                        st.success(msg) if success else st.error(msg)
                        st.rerun()
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

st.caption("📱 Мой Склад v2.0")
