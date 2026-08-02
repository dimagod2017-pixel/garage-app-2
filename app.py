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
                  installed_photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS park
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  date_added TEXT)''')
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
    
    # Добавляем новые колонки, если их нет
    c.execute("PRAGMA table_info(items)")
    columns = [col[1] for col in c.fetchall()]
    if 'application' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN application TEXT")
    if 'installed_photo' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN installed_photo TEXT")
    
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

# --- ФУНКЦИИ ДЛЯ ПАРКА ---
def add_park_object(name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO park (name, date_added) VALUES (?,?)",
                  (name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True, f"Объект '{name}' добавлен"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Объект '{name}' уже существует"

def delete_park_object(object_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM park WHERE id = ?", (object_id,))
    conn.commit()
    conn.close()

def get_park_objects():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM park ORDER BY name")
        results = c.fetchall()
    except sqlite3.OperationalError:
        c.execute('''CREATE TABLE IF NOT EXISTS park
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT UNIQUE,
                      date_added TEXT)''')
        results = []
    conn.close()
    
    formatted_results = []
    for row in results:
        if len(row) == 3:
            formatted_results.append(row)
        elif len(row) == 2:
            formatted_results.append((row[0], row[1], "—"))
        elif len(row) == 1:
            formatted_results.append((None, row[0], "—"))
        else:
            formatted_results.append((None, str(row), "—"))
    return formatted_results

def get_park_names():
    return [obj[1] for obj in get_park_objects()]

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

def get_consumption_by_object(object_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c 
                 JOIN items i ON c.item_id = i.id 
                 WHERE c.object_name = ? 
                 ORDER BY c.date DESC""", (object_name,))
    results = c.fetchall()
    conn.close()
    return results

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
def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold, application, installed_photo_path):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold, application, installed_photo_path))
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
    if room_filter and room_filter != "Все помещения":
        c.execute("""SELECT * FROM items WHERE 
                     (name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ? OR application LIKE ?) 
                     AND room = ?""", 
                  (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', room_filter))
    else:
        c.execute("""SELECT * FROM items WHERE 
                     name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ? OR application LIKE ?""", 
                  (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
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
    c.execute("SELECT COUNT(*) FROM park")
    total_park = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rooms")
    total_rooms_list = c.fetchone()[0]
    conn.close()
    return total_items, total_rooms, low_stock_count, top_categories, total_park, total_rooms_list

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
total_items, total_rooms, low_stock_count, top_categories, total_park, total_rooms_list = get_statistics()

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
    st.metric("🚗 В парке", total_park)
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
    # --- ПАРК ---
    st.header("🚗 Парк объектов")
    with st.form("add_park_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_park_object = st.text_input("Новый объект", placeholder="Машина №5")
        with col2:
            st.write("")
            st.write("")
            add_park_btn = st.form_submit_button("➕ Добавить")
        if add_park_btn and new_park_object:
            success, msg = add_park_object(new_park_object)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    
    park_objects = get_park_objects()
    if park_objects:
        for obj_id, obj_name, obj_date in park_objects:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.caption(f"• {obj_name}")
            with col2:
                if st.button("🗑️", key=f"del_park_{obj_id}"):
                    delete_park_object(obj_id)
                    st.rerun()
    else:
        st.caption("Пока нет объектов")
    
    st.divider()
    
    # --- ДОБАВЛЕНИЕ ВЕЩИ ---
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
        
        # --- НОВОЕ ПОЛЕ: Область применения ---
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
        # --- НОВОЕ ПОЛЕ: Фото установки ---
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
            add_item(name, category, location, room, description, item_path, loc_path, quantity, unit, threshold, application, installed_path)
            st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
            st.rerun()
        elif submitted:
            st.error("⚠️ Название, Помещение и Место обязательны!")
    
    st.divider()
    
    # --- ИМПОРТ/ЭКСПОРТ ---
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
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Поиск и управление", "📋 Все вещи", "🚗 Парк", "🏠 Помещения"])

with tab1:
    col_search, col_btn = st.columns([5, 1])
    with col_search:
        search_query = st.text_input("🔍 Что ищем?", placeholder="Введите название, категорию, место или область применения...", key="search_input")
    with col_btn:
        st.write("")
        search_clicked = st.button("🔍 Найти", use_container_width=True)
    
    rooms = ["Все помещения"] + get_room_names()
    room_filter = st.selectbox("🏠 Помещение", rooms, key="room_filter_tab1")
    
    if search_query:
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
                # Распаковка с учётом новых полей
                try:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo = item
                except ValueError:
                    # Если старые данные без новых полей
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item
                    application = ""
                    installed_photo = ""
                
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
                    if application:
                        st.caption(f"🔧 **Область применения:** {application}")
                    st.caption(f"📦 Количество: **{qty} {unit}**")
                    st.caption(f"📊 Статус: **{status_text}**")
                    
                    # Три фото в ряд
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
                    
                    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
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
                        if st.button("🗑️", key=f"del_{item_id}"):
                            delete_item(item_id)
                            st.rerun()
                    
                    # --- Диалоги ---
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
                                park_names = get_park_names()
                                if park_names:
                                    object_name = st.selectbox("Объект списания", park_names, key=f"cons_obj_{item_id}")
                                else:
                                    st.warning("Сначала добавьте объекты в парк!")
                                    object_name = st.text_input("Объект*", key=f"cons_obj_{item_id}")
                            
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
            try:
                item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo = item
            except ValueError:
                item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item
                application = ""
                installed_photo = ""
            try:
                qty = float(quantity)
            except:
                qty = 0
            data.append({
                "Название": name,
                "Категория": category or "",
                "Помещение": room,
                "Место": location,
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
    st.subheader("🚗 История списаний по объектам парка")
    
    park_objects = get_park_objects()
    if not park_objects:
        st.info("Пока нет объектов в парке. Добавьте их через боковое меню!")
    else:
        for obj_id, obj_name, obj_date in park_objects:
            with st.expander(f"🚗 {obj_name} (добавлен {obj_date[:10] if obj_date != '—' else 'неизвестно'})"):
                consumptions = get_consumption_by_object(obj_name)
                if not consumptions:
                    st.caption("Нет списаний на этот объект")
                else:
                    st.caption(f"Всего списаний: {len(consumptions)}")
                    for c in consumptions:
                        st.write(f"• {c[7]} → **{c[2]} {c[3]}** (списал {c[5]}, {c[6][:10]})")
    
    st.divider()
    st.subheader("📋 Общая история списаний")
    all_consumption = get_all_consumption()
    if not all_consumption:
        st.info("Пока нет списаний")
    else:
        for c in all_consumption[:50]:
            st.write(f"• **{c[7]}** → {c[2]} {c[3]} на **{c[4]}** (списал {c[5]}, {c[6]})")
        if len(all_consumption) > 50:
            st.caption("... показаны последние 50 записей")

with tab4:
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
