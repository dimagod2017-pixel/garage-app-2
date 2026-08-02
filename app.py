import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import pandas as pd
from io import BytesIO
import qrcode

# --- ПАРОЛЬ ---
PASSWORD = "12345"

user_pass = st.sidebar.text_input("🔑 Введите пароль:", type="password")
if user_pass != PASSWORD:
    st.sidebar.warning("⚠️ Неверный пароль!")
    st.stop()

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="📦", layout="wide")
st.title("📦 Мой Склад")
st.caption("Добро пожаловать! Храните и находите вещи легко.")

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
            .stApp { background-color: #0e1117; color: #fafafa; }
            .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
                color: #fafafa !important;
            }
            .stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label {
                color: #cccccc !important;
            }
            .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
                background-color: #262730 !important;
                color: #fafafa !important;
                border-radius: 8px;
            }
            .stButton button {
                background-color: #FF6B35 !important;
                color: #ffffff !important;
                border-radius: 8px;
                font-weight: bold;
            }
            .stButton button:hover {
                background-color: #004E89 !important;
                color: #ffffff !important;
            }
            .stCaption, .stCaption p {
                color: #aaaaaa !important;
            }
            .stInfo, .stWarning, .stError, .stSuccess {
                background-color: #262730 !important;
                color: #fafafa !important;
            }
            .stAlert { background-color: #262730 !important; }
            .element-container, .stContainer, .stColumn { background-color: transparent !important; }
            div[data-testid="stSidebar"] { background-color: #1a1d23 !important; }
            div[data-testid="stSidebar"] * { color: #fafafa !important; }
            div[data-testid="stSidebar"] .stTextInput input { background-color: #262730 !important; color: #fafafa !important; }
            div[data-testid="stDialog"] { background-color: #1a1d23 !important; }
            div[data-testid="stDialog"] * { color: #fafafa !important; }
            div[data-testid="stDialog"] input, div[data-testid="stDialog"] textarea {
                background-color: #262730 !important;
                color: #fafafa !important;
            }
        </style>
    """, unsafe_allow_html=True)

# --- ПАПКА ДЛЯ ФОТО ---
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
                  date TEXT)''')
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
    
    c.execute("PRAGMA table_info(equipment)")
    eq_columns = [col[1] for col in c.fetchall()]
    if 'number' not in eq_columns:
        c.execute("ALTER TABLE equipment ADD COLUMN number TEXT")
    
    conn.commit()
    conn.close()

# --- ФУНКЦИИ ДЛЯ ПОМЕЩЕНИЙ ---
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

# --- ФУНКЦИИ ДЛЯ ТЕХНИКИ ---
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

# --- ФУНКЦИИ ДЛЯ АГРЕГАТОВ ---
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

# --- ФУНКЦИИ ДЛЯ РАСХОДА ---
def consume_item(item_id, quantity, object_name, user="Пользователь", note=""):
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
    c.execute("INSERT INTO consumption (item_id, quantity, unit, object_name, user, date) VALUES (?,?,?,?,?,?)",
              (item_id, quantity, unit, object_name, user, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return True, f"Списано {quantity} {unit} на '{object_name}'"

def get_all_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c 
                 JOIN items i ON c.item_id = i.id 
                 ORDER BY c.date DESC LIMIT 200""")
    results = c.fetchall()
    conn.close()
    return results

# --- ОСНОВНЫЕ ФУНКЦИИ ---
def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo, equipment_id, unit_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id))
    conn.commit()
    conn.close()
    return item_id

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

# --- ПРОСТОЙ И НАДЁЖНЫЙ ПОИСК ---
def search_items(query, room_filter=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    query_lower = f"%{query.lower()}%"
    
    try:
        if room_filter and room_filter != "Все помещения":
            c.execute("""
                SELECT * FROM items 
                WHERE (LOWER(name) LIKE ? 
                       OR LOWER(category) LIKE ? 
                       OR LOWER(location) LIKE ? 
                       OR LOWER(description) LIKE ?)
                AND room = ?
            """, (query_lower, query_lower, query_lower, query_lower, room_filter))
        else:
            c.execute("""
                SELECT * FROM items 
                WHERE LOWER(name) LIKE ? 
                   OR LOWER(category) LIKE ? 
                   OR LOWER(location) LIKE ? 
                   OR LOWER(description) LIKE ?
            """, (query_lower, query_lower, query_lower, query_lower))
    except Exception as e:
        st.error(f"Ошибка поиска: {e}")
        conn.close()
        return []
    
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
    conn.close()
    return total_items, total_rooms, low_stock_count, top_categories, total_equipment, total_rooms_list

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
total_items, total_rooms, low_stock_count, top_categories, total_equipment, total_rooms_list = get_statistics()

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("📦 Вещей", total_items)
with col2:
    st.metric("🏠 Помещ.", total_rooms_list)
with col3:
    st.metric("⚠️ Пополнить", low_stock_count)
with col4:
    top_cat_str = ", ".join([f"{cat}" for cat, count in top_categories[:2]]) if top_categories else "—"
    st.metric("🏆 Топ", top_cat_str)
with col5:
    st.metric("🚜 Техники", total_equipment)
with col6:
    st.metric("📤 Списано", 0)

# --- УВЕДОМЛЕНИЯ ---
low_stock = get_low_stock_items()
if low_stock:
    st.warning("⚠️ **ВНИМАНИЕ! Заканчиваются:**")
    for item in low_stock:
        qty = item[9]
        name = item[1]
        unit = item[10]
        room = item[4]
        if qty <= 0:
            st.error(f"🔴 {name} — 0 {unit} (в {room})")
        else:
            st.warning(f"🟡 {name} — {qty} {unit} (в {room})")
    st.divider()

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
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
            item_path = ""; loc_path = ""; installed_path = ""
            if item_pic:
                ext = item_pic.name.split('.')[-1]
                item_path = f"images/{uuid.uuid4()}_item.{ext}"
                with open(item_path, "wb") as f: f.write(item_pic.getbuffer())
            if location_pic:
                ext = location_pic.name.split('.')[-1]
                loc_path = f"images/{uuid.uuid4()}_loc.{ext}"
                with open(loc_path, "wb") as f: f.write(location_pic.getbuffer())
            if installed_pic:
                ext = installed_pic.name.split('.')[-1]
                installed_path = f"images/{uuid.uuid4()}_installed.{ext}"
                with open(installed_path, "wb") as f: f.write(installed_pic.getbuffer())
            add_item(name, category, location, room, description, item_path, loc_path, quantity, unit, threshold, application, installed_path, eq_id, unit_id)
            st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
            st.rerun()
        elif submitted:
            st.error("⚠️ Название, Помещение и Место обязательны!")
    
    st.divider()
    
    st.header("📥 Импорт Excel")
    uploaded_file = st.file_uploader("Выберите Excel-файл", type=["xlsx", "xls"])
    if uploaded_file:
        if st.button("📤 Импортировать"):
            st.success("Импорт пока в разработке")
    
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

# --- ОСНОВНАЯ ОБЛАСТЬ: ВКЛАДКИ ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "🚗 История списаний", "🏠 Помещения"])

with tab1:
    col_search, col_btn = st.columns([5, 1])
    with col_search:
        search_query = st.text_input("🔍 Что ищем?", placeholder="Введите название, категорию, место...", key="search_input")
    with col_btn:
        st.write("")
        search_clicked = st.button("🔍 Найти", use_container_width=True)
    
    rooms = ["Все помещения"] + get_room_names()
    room_filter = st.selectbox("🏠 Помещение", rooms, key="room_filter_tab1")
    
    if search_query:
        st.caption(f"🔎 Ищем: **{search_query}**")
        items = search_items(search_query, room_filter)
    else:
        items = get_all_items(room_filter)
    
    st.subheader(f"📌 Найдено: {len(items)}")

    if not items:
        st.info("Ничего нет. Добавьте через меню.")
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
                        eq_name = eq[1]
                        if eq[2]:
                            eq_name += f" ({eq[2]})"
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
                    st.markdown(f"**{status_emoji} {name}**")
                    if category:
                        st.caption(f"📂 {category}")
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
                    
                    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5, col_btn6 = st.columns(6)
                    with col_btn1:
                        if st.button("✏️ Кол-во", key=f"edit_{item_id}"):
                            st.session_state[f"edit_mode_{item_id}"] = True
                            st.rerun()
                    with col_btn2:
                        if st.button("⚙️ Порог", key=f"thr_{item_id}"):
                            st.session_state[f"thr_mode_{item_id}"] = True
                            st.rerun()
                    with col_btn3:
                        if st.button("📤 Спис.", key=f"cons_{item_id}"):
                            st.session_state[f"cons_mode_{item_id}"] = True
                            st.rerun()
                    with col_btn4:
                        if st.button("📷 QR", key=f"qr_{item_id}"):
                            st.session_state[f"qr_mode_{item_id}"] = True
                            st.rerun()
                    with col_btn5:
                        if st.button("🚚 Переместить", key=f"move_{item_id}"):
                            st.session_state[f"move_mode_{item_id}"] = True
                            st.rerun()
                    with col_btn6:
                        if st.button("🗑️", key=f"del_{item_id}"):
                            delete_item(item_id)
                            st.rerun()
                    
                    if st.session_state.get(f"edit_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**Изменение количества для {name}**")
                            new_q = st.number_input(f"Новое количество ({unit})", min_value=0.0, step=0.5, value=float(qty), key=f"input_q_{item_id}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Сохранить", key=f"save_q_{item_id}"):
                                    update_quantity(item_id, new_q)
                                    st.session_state[f"edit_mode_{item_id}"] = False
                                    st.rerun()
                            with col2:
                                if st.button("❌ Отмена", key=f"cancel_q_{item_id}"):
                                    st.session_state[f"edit_mode_{item_id}"] = False
                                    st.rerun()
                    
                    if st.session_state.get(f"thr_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**Настройка порога для {name}**")
                            new_thr = st.number_input("Минимальное количество для уведомления", min_value=0, step=1, value=int(threshold), key=f"input_thr_{item_id}")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Сохранить", key=f"save_thr_{item_id}"):
                                    update_threshold(item_id, new_thr)
                                    st.session_state[f"thr_mode_{item_id}"] = False
                                    st.rerun()
                            with col2:
                                if st.button("❌ Отмена", key=f"cancel_thr_{item_id}"):
                                    st.session_state[f"thr_mode_{item_id}"] = False
                                    st.rerun()
                    
                    if st.session_state.get(f"cons_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**Списание {name}**")
                            st.caption(f"Доступно: {qty} {unit}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                consume_qty = st.number_input("Количество", min_value=0.0, step=0.5, max_value=float(qty), value=min(1.0, float(qty)), key=f"cons_qty_{item_id}")
                            with col2:
                                equipment_list = get_equipment()
                                search_options = ["Другое"]
                                for eq in equipment_list:
                                    eq_name = eq[1]
                                    if eq[2]:
                                        eq_name += f" ({eq[2]})"
                                    search_options.append(eq_name)
                                    units = get_units(eq[0])
                                    for unit in units:
                                        search_options.append(f"{eq_name} → {unit[1]}")
                                
                                search_equipment = st.text_input("🔍 Поиск техники или агрегата", placeholder="Начните вводить название...", key=f"search_eq_{item_id}")
                                
                                if search_equipment:
                                    filtered_eq = [opt for opt in search_options if search_equipment.lower() in opt.lower()]
                                else:
                                    filtered_eq = search_options
                                
                                if filtered_eq:
                                    selected_eq = st.selectbox("Выберите технику или агрегат", filtered_eq, key=f"sel_eq_{item_id}")
                                    if selected_eq == "Другое":
                                        object_name = st.text_input("Введите название объекта*", key=f"custom_obj_{item_id}")
                                    else:
                                        object_name = selected_eq
                                else:
                                    st.warning("Ничего не найдено. Выберите 'Другое' или добавьте технику в разделе '🚜 Парк'")
                                    object_name = st.text_input("Введите название объекта*", key=f"custom_obj_{item_id}")
                            
                            user = st.text_input("Кто списывает", value="Пользователь", key=f"cons_user_{item_id}")
                            note = st.text_area("Примечание", key=f"cons_note_{item_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Списать", key=f"save_cons_{item_id}"):
                                    if consume_qty <= 0:
                                        st.error("Количество должно быть > 0")
                                    elif not object_name:
                                        st.error("Укажите объект")
                                    else:
                                        success, message = consume_item(item_id, consume_qty, object_name, user, note)
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
                    
                    if st.session_state.get(f"move_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**Перемещение {name}**")
                            st.caption(f"Текущее помещение: **{room}**")
                            
                            room_names = get_room_names()
                            available_rooms = [r for r in room_names if r != room]
                            
                            if available_rooms:
                                new_room = st.selectbox("Выберите новое помещение", available_rooms, key=f"new_room_{item_id}")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Переместить", key=f"save_move_{item_id}"):
                                        update_item_room(item_id, new_room)
                                        st.session_state[f"move_mode_{item_id}"] = False
                                        st.success(f"✅ Вещь перемещена в '{new_room}'")
                                        st.rerun()
                                with col2:
                                    if st.button("❌ Отмена", key=f"cancel_move_{item_id}"):
                                        st.session_state[f"move_mode_{item_id}"] = False
                                        st.rerun()
                            else:
                                st.warning("Нет доступных помещений для перемещения. Сначала добавьте их в разделе 'Помещения'.")
                                if st.button("❌ Закрыть", key=f"close_move_{item_id}"):
                                    st.session_state[f"move_mode_{item_id}"] = False
                                    st.rerun()
                    
                    if st.session_state.get(f"qr_mode_{item_id}", False):
                        with st.container(border=True):
                            st.write(f"**QR-код для {name}**")
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
                                mime="image/png"
                            )
                            if st.button("❌ Закрыть QR", key=f"close_qr_{item_id}"):
                                st.session_state[f"qr_mode_{item_id}"] = False
                                st.rerun()

with tab2:
    st.subheader("📋 Все вещи в базе данных")
    all_items = get_all_items()
    
    if not all_items:
        st.info("В базе пока нет вещей. Добавьте первую вещь через боковое меню!")
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
                    eq_name = eq[1]
                    if eq[2]:
                        eq_name += f" ({eq[2]})"
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
        st.download_button(
            label="📥 Скачать таблицу (CSV)",
            data=csv,
            file_name=f"все_вещи_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

with tab3:
    st.subheader("🚜 Управление техникой и агрегатами")
    
    with st.expander("➕ Добавить технику", expanded=True):
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
        st.info("Пока нет техники. Добавьте первую!")
    else:
        for eq in equipment_list:
            eq_id, eq_name, eq_number, eq_date = eq
            with st.expander(f"🚜 {eq_name}" + (f" ({eq_number})" if eq_number else "")):
                with st.form(key=f"edit_eq_{eq_id}"):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        new_name = st.text_input("Название", value=eq_name, key=f"eq_name_{eq_id}")
                    with col2:
                        new_number = st.text_input("Госномер", value=eq_number or "", key=f"eq_number_{eq_id}")
                    with col3:
                        st.write("")
                        st.write("")
                        if st.form_submit_button("💾 Сохранить"):
                            update_equipment(eq_id, new_name, new_number)
                            st.success("Данные обновлены")
                            st.rerun()
                
                with st.form(key=f"add_unit_{eq_id}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        unit_name = st.text_input("Название агрегата/оборудования", placeholder="Борона дисковая БДМ-100", key=f"unit_name_{eq_id}")
                    with col2:
                        st.write("")
                        st.write("")
                        if st.form_submit_button("➕ Добавить агрегат"):
                            if unit_name:
                                success, msg = add_unit(unit_name, eq_id)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.error("Введите название агрегата")
                
                units = get_units(eq_id)
                if units:
                    st.caption(f"Закреплённые агрегаты ({len(units)})")
                    for unit in units:
                        unit_id, unit_name, _, _ = unit
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"🔧 {unit_name}")
                        with col2:
                            if st.button("🗑️", key=f"del_unit_{unit_id}"):
                                delete_unit(unit_id)
                                st.rerun()
                else:
                    st.caption("Нет закреплённых агрегатов")
                
                if st.button("🗑️ Удалить технику", key=f"del_eq_{eq_id}"):
                    delete_equipment(eq_id)
                    st.rerun()

with tab4:
    st.subheader("🚗 История списаний по объектам")
    
    all_consumption = get_all_consumption()
    if not all_consumption:
        st.info("Пока нет списаний")
    else:
        for c in all_consumption[:50]:
            st.write(f"• **{c[7]}** → {c[2]} {c[3]} на **{c[4]}** (списал {c[5]}, {c[6]})")
        if len(all_consumption) > 50:
            st.caption("... показаны последние 50 записей")

with tab5:
    st.subheader("🏠 Управление помещениями")
    
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
        st.info("Пока нет помещений. Добавьте первое!")
    else:
        st.caption(f"Всего помещений: {len(rooms)}")
        for room_id, room_name, room_date in rooms:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"🏠 **{room_name}** (добавлено {room_date[:10]})")
            with col2:
                if st.button("🗑️", key=f"del_room_{room_id}"):
                    delete_room(room_id)
                    st.rerun()
