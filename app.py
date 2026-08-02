import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO

# --- ПАРОЛИ ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

# --- ИНИЦИАЛИЗАЦИЯ ---
if "user" not in st.session_state:
    st.session_state.user = None

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

# --- ФУНКЦИИ БД ---
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

def get_statistics():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM items")
    total_items = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = c.fetchone()[0]
    conn.close()
    return total_items, total_rooms

# --- СОЗДАНИЕ ПАПКИ ---
if not os.path.exists("images"):
    os.makedirs("images")

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
total_items, total_rooms = get_statistics()

col1, col2 = st.columns(2)
with col1:
    st.metric("📦 Вещи", total_items)
with col2:
    st.metric("🏠 Помещения", total_rooms)

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    st.divider()
    
    if role == "admin":
        st.header("➕ Добавить вещь")
        room_names = get_room_names()
        
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
    
    st.header("🏠 Добавить помещение")
    if role == "admin":
        with st.form("add_room_form", clear_on_submit=True):
            new_room = st.text_input("Название помещения")
            if st.form_submit_button("➕ Добавить"):
                if new_room:
                    success, msg = add_room(new_room)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

# --- ВКЛАДКИ ---
tab1, tab2 = st.tabs(["📋 Все вещи", "🏠 Помещения"])

with tab1:
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
        
        # Удаление
        for item in items:
            if st.button(f"🗑️ Удалить {item[1]}", key=f"del_{item[0]}"):
                delete_item(item[0])
                st.rerun()

with tab2:
    st.subheader("🏠 Помещения")
    rooms = get_rooms()
    if not rooms:
        st.info("🌱 Пока нет помещений")
    else:
        for room_id, room_name, room_date in rooms:
            items = get_items_by_room(room_name)
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"🏠 **{room_name}**")
                    st.caption(f"📦 {len(items)} вещей")
                with col2:
                    if role == "admin" and st.button("🗑️", key=f"del_room_{room_id}"):
                        delete_room(room_id)
                        st.rerun()
                
                if items:
                    for item in items:
                        st.write(f"• {item[1]} — {item[9]} {item[10]}")

st.caption("📱 Мой Склад v1.0")
