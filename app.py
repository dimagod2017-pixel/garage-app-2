import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO
import qrcode
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# --- НАСТРОЙКА YANDEX ПОЧТЫ ---
EMAIL_SENDER = "Yvedomlenie-scald.sad@yandex.ru"
EMAIL_PASSWORD = "ваш_реальный_пароль_здесь"  # ЗАМЕНИТЕ!
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

# --- ПАРОЛИ ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

# --- ИНИЦИАЛИЗАЦИЯ ---
if "user" not in st.session_state:
    st.session_state.user = None
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

# --- ВХОД ---
def login():
    st.sidebar.title("🔐 Вход")
    if st.session_state.user is not None:
        return
    
    password = st.sidebar.text_input("Введите пароль:", type="password")
    
    if st.sidebar.button("🔓 Войти"):
        if password in USERS:
            st.session_state.user = USERS[password]
            st.session_state.user["password"] = password
            st.rerun()
        else:
            st.sidebar.error("❌ Неверный пароль!")

if st.session_state.user is None:
    login()
    st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

st.title("🌿 Мой Склад")
st.caption(f"👋 Добро пожаловать, {user_name}!")

if st.sidebar.button("🚪 Выйти"):
    st.session_state.user = None
    st.rerun()

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
                  threshold INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  date_added TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С БД ---
def get_rooms():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rooms ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def get_room_names():
    return [room[1] for room in get_rooms()]

def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("""INSERT INTO items 
                 (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path, 
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

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
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

# --- СОЗДАНИЕ ПАПКИ ДЛЯ ИЗОБРАЖЕНИЙ ---
if not os.path.exists("images"):
    os.makedirs("images")

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
# СТАТИСТИКА
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
            
            item_pic = st.file_uploader("📷 Фото вещи", type=["jpg", "jpeg", "png"])
            location_pic = st.file_uploader("📷 Фото места", type=["jpg", "jpeg", "png"])
            
            submitted = st.form_submit_button("💾 Сохранить")
            
            if submitted and name and location and room != "— Добавьте помещение —":
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
                
                add_item(name, category, location, room, description, item_path, loc_path, quantity, unit, threshold)
                st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
                st.rerun()
            elif submitted:
                st.error("⚠️ Название, Помещение и Место обязательны!")
        st.divider()
    
    # Экспорт/Импорт
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
tab1, tab2, tab3 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🏠 Помещения"])

with tab1:
    st.subheader("🔍 Поиск вещей")
    search_query = st.text_input("Что ищем?", placeholder="Введите название...")
    
    rooms = ["Все помещения"] + get_room_names()
    room_filter = st.selectbox("🏠 Помещение", rooms)
    
    items = get_all_items() if not search_query else []
    if items:
        st.subheader(f"📌 Найдено: {len(items)}")
        for item in items:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{item[1]}**")
                    st.caption(f"📍 {item[3]} | 🏠 {item[4]}")
                    st.caption(f"📦 {item[9]} {item[10]}")
                with col2:
                    if role == "admin" and st.button("🗑️ Удалить", key=f"del_{item[0]}"):
                        delete_item(item[0])
                        st.rerun()
                with col3:
                    if item[6] and os.path.exists(item[6]):
                        st.image(item[6], width=100)
    else:
        st.info("🌱 Ничего не найдено")

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

with tab3:
    st.subheader("🏠 Управление помещениями")
    
    if role == "admin":
        with st.form("add_room_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_room = st.text_input("Название помещения", placeholder="Гараж, Склад...")
            with col2:
                st.write("")
                st.write("")
                if st.form_submit_button("➕ Добавить"):
                    if new_room:
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
        for room_id, room_name, room_date in rooms:
            items = get_items_by_room(room_name)
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"🏠 **{room_name}**")
                    st.caption(f"📦 {len(items)} вещей | Добавлено: {room_date[:10]}")
                with col2:
                    if st.button("📦 Открыть", key=f"open_{room_id}"):
                        st.session_state.selected_room = room_name
                with col3:
                    if role == "admin" and st.button("🗑️", key=f"del_room_{room_id}"):
                        delete_room(room_id)
                        st.rerun()
            
            if st.session_state.get("selected_room") == room_name:
                st.write(f"**Содержимое {room_name}:**")
                if items:
                    for item in items:
                        st.write(f"• {item[1]} — {item[9]} {item[10]}")
                else:
                    st.info("Пусто")
                if st.button("Закрыть"):
                    st.session_state.selected_room = None
                    st.rerun()
                st.divider()

st.caption("📱 Мой Склад v1.0")
