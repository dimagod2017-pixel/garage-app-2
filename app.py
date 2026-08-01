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

# --- ПЕРСОНАЛЬНЫЕ НАСТРОЙКИ ---
GARAGE_NAME = "Мой Склад"
OWNER_NAME = "Пользователь"
PRIMARY_COLOR = "#FF6B35"
SECONDARY_COLOR = "#004E89"

# --- ТЁМНАЯ ТЕМА ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

with st.sidebar:
    dark_mode_toggle = st.toggle("🌙 Тёмная тема", value=st.session_state.dark_mode)
    if dark_mode_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode_toggle
        st.rerun()

# --- CSS ДЛЯ ТЁМНОЙ ТЕМЫ ---
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

# --- ОСНОВНОЙ СТИЛЬ ---
st.markdown(f"""
    <style>
        .main-header {{
            background: linear-gradient(90deg, {PRIMARY_COLOR}, {SECONDARY_COLOR});
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }}
        .main-header h1 {{ margin: 0; font-size: 2.5rem; }}
        .main-header p {{ margin: 0; font-size: 1.2rem; opacity: 0.9; }}
        .stat-card {{
            background: {'#2d2d2d' if st.session_state.dark_mode else '#f5f5f5'};
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            border-left: 5px solid {PRIMARY_COLOR};
            margin-bottom: 1rem;
        }}
        .stat-number {{ font-size: 2rem; font-weight: bold; color: {PRIMARY_COLOR}; }}
        .critical-warning {{ background-color: #ffebee; border-left: 5px solid #f44336; padding: 0.8rem; border-radius: 5px; margin-bottom: 1rem; }}
        .warning-warning {{ background-color: #fff3e0; border-left: 5px solid #ff9800; padding: 0.8rem; border-radius: 5px; margin-bottom: 1rem; }}
        .item-card {{
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            background: {'#1a1d23' if st.session_state.dark_mode else '#f9f9f9'};
            border: 1px solid {'#333' if st.session_state.dark_mode else '#ddd'};
        }}
    </style>
""", unsafe_allow_html=True)

# --- ЗАГОЛОВОК ---
st.markdown(f"""
    <div class="main-header">
        <h1>📦 {GARAGE_NAME}</h1>
        <p>👋 Добро пожаловать, {OWNER_NAME}!</p>
    </div>
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
                  threshold INTEGER DEFAULT 1)''')
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
    conn.commit()
    conn.close()

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
    c.execute("SELECT * FROM park ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

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

def get_consumption_by_object(object_name=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if object_name:
        c.execute("""SELECT c.*, i.name FROM consumption c 
                     JOIN items i ON c.item_id = i.id 
                     WHERE c.object_name = ? 
                     ORDER BY c.date DESC""", (object_name,))
    else:
        c.execute("""SELECT c.*, i.name FROM consumption c 
                     JOIN items i ON c.item_id = i.id 
                     ORDER BY c.date DESC LIMIT 100""")
    results = c.fetchall()
    conn.close()
    return results

def get_all_objects():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT object_name FROM consumption ORDER BY object_name")
    objects = [row[0] for row in c.fetchall()]
    conn.close()
    return objects

def get_total_consumed():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT SUM(quantity) FROM consumption")
    total = c.fetchone()[0] or 0
    conn.close()
    return total

# --- ОСНОВНЫЕ ФУНКЦИИ ---
def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold))
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
    c.execute("SELECT item_photo, location_photo FROM items WHERE id = ?", (item_id,))
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
                     (name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ?) 
                     AND room = ?""", 
                  (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', room_filter))
    else:
        c.execute("""SELECT * FROM items WHERE 
                     name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ?""", 
                  (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
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

def get_all_rooms():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT room FROM items")
    rooms = [row[0] for row in c.fetchall()]
    conn.close()
    return rooms if rooms else ["Общий"]

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
    c.execute("SELECT SUM(quantity) FROM consumption")
    total_consumed = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM park")
    total_park = c.fetchone()[0]
    conn.close()
    return total_items, total_rooms, low_stock_count, top_categories, total_consumed, total_park

def export_to_excel():
    conn = sqlite3.connect('storage.db')
    df = pd.read_sql_query("SELECT name as 'Название', category as 'Категория', location as 'Место', room as 'Помещение', description as 'Описание', quantity as 'Количество', unit as 'Ед. изм.', threshold as 'Порог', date_added as 'Дата добавления' FROM items", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Инвентарь')
        for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            writer.sheets['Инвентарь'].column_dimensions[chr(65 + col_idx)].width = column_width + 2
    return output.getvalue()

def import_from_excel(file):
    try:
        df = pd.read_excel(file)
        required_columns = ['Название', 'Место', 'Помещение']
        for col in required_columns:
            if col not in df.columns:
                return False, f"В файле нет колонки '{col}'"
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        added = 0
        for _, row in df.iterrows():
            name = str(row.get('Название', ''))
            location = str(row.get('Место', ''))
            room = str(row.get('Помещение', 'Общий'))
            if name and location:
                category = str(row.get('Категория', ''))
                description = str(row.get('Описание', ''))
                quantity = float(row.get('Количество', 1)) if pd.notna(row.get('Количество')) else 1
                unit = str(row.get('Ед. изм.', 'шт'))
                threshold = int(row.get('Порог', 1)) if pd.notna(row.get('Порог')) else 1
                item_id = str(uuid.uuid4())[:8]
                c.execute("INSERT INTO items (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                          (item_id, name, category, location, room, description, "", "", datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold))
                added += 1
        conn.commit()
        conn.close()
        return True, f"Добавлено {added} позиций"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def render_item_card(item):
    """Отрисовка карточки одной вещи"""
    try:
        item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item
    except ValueError:
        item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit = item
        threshold = 1
    
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
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
        st.caption(f"📦 Количество: **{qty} {unit}**")
        st.caption(f"📊 Статус: **{status_text}**")
        
        c1, c2 = st.columns(2)
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
        
        if description:
            st.write(f"📝 {description}")
        st.caption(f"🕒 Добавлено: {date_added}")
        
        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
        with col_btn1:
            if st.button("✏️ Кол-во", key=f"edit_{item_id}"):
                quantity_dialog(item_id, name, qty, unit)
        with col_btn2:
            if st.button("⚙️ Порог", key=f"thr_{item_id}"):
                threshold_dialog(item_id, name, threshold)
        with col_btn3:
            if st.button("📤 Спис.", key=f"cons_{item_id}"):
                consume_dialog(item_id, name, qty, unit)
        with col_btn4:
            if st.button("📷 QR", key=f"qr_{item_id}"):
                qr_dialog(item_id, name)
        with col_btn5:
            if st.button("🗑️", key=f"del_{item_id}"):
                delete_item(item_id)
                st.rerun()

init_db()

# --- СТАТИСТИКА ---
total_items, total_rooms, low_stock_count, top_categories, total_consumed, total_park = get_statistics()

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.markdown(f"""<div class="stat-card"><div class="stat-number">{total_items}</div><div>📦 Вещей</div></div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="stat-card"><div class="stat-number">{total_rooms}</div><div>🏠 Помещ.</div></div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div class="stat-card" style="border-left-color: #f44336;"><div class="stat-number" style="color: #f44336;">{low_stock_count}</div><div>⚠️ Пополнить</div></div>""", unsafe_allow_html=True)
with col4:
    top_cat_str = ", ".join([f"{cat}" for cat, count in top_categories[:2]]) if top_categories else "—"
    st.markdown(f"""<div class="stat-card"><div class="stat-number">🏆</div><div>{top_cat_str}</div></div>""", unsafe_allow_html=True)
with col5:
    st.markdown(f"""<div class="stat-card" style="border-left-color: #4CAF50;"><div class="stat-number" style="color: #4CAF50;">{total_consumed:.1f}</div><div>📤 Списано</div></div>""", unsafe_allow_html=True)
with col6:
    st.markdown(f"""<div class="stat-card" style="border-left-color: #9C27B0;"><div class="stat-number" style="color: #9C27B0;">{total_park}</div><div>🚗 В парке</div></div>""", unsafe_allow_html=True)

# --- УВЕДОМЛЕНИЯ ---
low_stock = get_low_stock_items()
if low_stock:
    st.markdown('<div class="critical-warning">⚠️ <b>ВНИМАНИЕ! Заканчиваются:</b></div>', unsafe_allow_html=True)
    critical = [item for item in low_stock if item[9] == 0]
    warning = [item for item in low_stock if item[9] > 0]
    col1, col2 = st.columns(2)
    with col1:
        if critical:
            st.error(f"🔴 **Критично (0 осталось):**")
            for item in critical:
                st.write(f"- {item[1]} ({item[9]} {item[10]}) в {item[4]}")
    with col2:
        if warning:
            st.warning(f"🟡 **Скоро закончится:**")
            for item in warning:
                st.write(f"- {item[1]} ({item[9]} {item[10]}) в {item[4]}")
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
        for obj in park_objects:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.caption(f"• {obj[1]}")
            with col2:
                if st.button("🗑️", key=f"del_park_{obj[0]}"):
                    delete_park_object(obj[0])
                    st.rerun()
    else:
        st.caption("Пока нет объектов")
    
    st.divider()
    
    # --- ДОБАВЛЕНИЕ ВЕЩИ ---
    st.header("➕ Добавить вещь")
    existing_rooms = get_all_rooms()
    room_options = ["Новое помещение"] + existing_rooms
    
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Название вещи*")
        category = st.text_input("Категория")
        room_choice = st.selectbox("Помещение", room_options)
        if room_choice == "Новое помещение":
            room = st.text_input("Название нового помещения*")
        else:
            room = room_choice
        location = st.text_input("Место внутри помещения*")
        description = st.text_area("Описание")
        col1, col2, col3 = st.columns(3)
        with col1:
            quantity = st.number_input("Количество", min_value=0.0, step=0.5, value=1.0)
        with col2:
            unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект", "упаковка", "м²", "другой"])
            if unit == "другой":
                unit = st.text_input("Своя единица")
        with col3:
            threshold = st.number_input("Порог", min_value=0, step=1, value=1)
        item_pic = st.file_uploader("Фото вещи", type=["jpg", "jpeg", "png"], key="item")
        location_pic = st.file_uploader("Фото места", type=["jpg", "jpeg", "png"], key="loc")
        submitted = st.form_submit_button("💾 Сохранить")
        if submitted and name and location and room:
            item_path = ""; loc_path = ""
            if item_pic:
                ext = item_pic.name.split('.')[-1]
                item_path = f"images/{uuid.uuid4()}_item.{ext}"
                with open(item_path, "wb") as f: f.write(item_pic.getbuffer())
            if location_pic:
                ext = location_pic.name.split('.')[-1]
                loc_path = f"images/{uuid.uuid4()}_loc.{ext}"
                with open(loc_path, "wb") as f: f.write(location_pic.getbuffer())
            add_item(name, category, location, room, description, item_path, loc_path, quantity, unit, threshold)
            st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
            st.rerun()
        elif submitted:
            st.error("⚠️ Название, Помещение и Место обязательны!")
    
    st.divider()
    
    # --- РАСХОД ПО ОБЪЕКТАМ ---
    st.header("📊 Расход по объектам")
    objects = get_all_objects()
    if objects:
        selected_object = st.selectbox("Выберите объект", objects)
        if selected_object:
            consumptions = get_consumption_by_object(selected_object)
            if consumptions:
                st.caption(f"Всего: {len(consumptions)}")
                for c in consumptions[:10]:
                    st.write(f"• {c[8]} → **{c[2]} {c[3]}** ({c[5]}, {c[6][:10]})")
                if len(consumptions) > 10:
                    st.caption("... последние 10")
            else:
                st.info("Нет записей")
    else:
        st.info("Пока нет списаний")
    
    st.divider()
    
    # --- ИМПОРТ/ЭКСПОРТ ---
    st.header("📥 Импорт Excel")
    uploaded_file = st.file_uploader("Выберите Excel-файл", type=["xlsx", "xls"])
    if uploaded_file:
        if st.button("📤 Импортировать"):
            success, message = import_from_excel(uploaded_file)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
    
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
tab1, tab2 = st.tabs(["🔍 Поиск и управление", "📋 Все вещи"])

with tab1:
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 Что ищем?", placeholder="Введите название, категорию, место...")
    with col_filter:
        rooms = ["Все помещения"] + get_all_rooms()
        room_filter = st.selectbox("🏠 Помещение", rooms)

    items = search_items(search_query, room_filter) if search_query else get_all_items(room_filter)
    st.subheader(f"📌 Найдено: {len(items)}")

    if not items:
        st.info("Ничего нет. Добавьте через меню.")
    else:
        cols = st.columns(3)
        for idx, item in enumerate(items):
            with cols[idx % 3]:
                render_item_card(item)

with tab2:
    st.subheader("📋 Все вещи в базе данных")
    all_items = get_all_items()
    
    if not all_items:
        st.info("В базе пока нет вещей. Добавьте первую вещь через боковое меню!")
    else:
        # Показываем таблицу
        data = []
        for item in all_items:
            try:
                item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item
            except ValueError:
                item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit = item
                threshold = 1
            try:
                qty = float(quantity)
            except (TypeError, ValueError):
                qty = 0
            data.append({
                "Название": name,
                "Категория": category or "",
                "Помещение": room,
                "Место": location,
                "Количество": f"{qty} {unit}",
                "Статус": "🔴 Критично" if qty <= 0 else "🟡 Скоро" if qty <= threshold else "🟢 Норма",
                "Дата": date_added[:10]
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Кнопка для скачивания таблицы
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать таблицу (CSV)",
            data=csv,
            file_name=f"все_вещи_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

# --- ДИАЛОГИ ---
@st.dialog("✏️ Изменение количества")
def quantity_dialog(item_id, current_name, current_quantity, current_unit):
    st.write(f"Изменяем количество для **{current_name}**")
    new_q = st.number_input(f"Новое количество ({current_unit})", min_value=0.0, step=0.5, value=float(current_quantity))
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Сохранить"):
            update_quantity(item_id, new_q)
            st.rerun()
    with col2:
        if st.button("❌ Отмена"):
            st.rerun()

@st.dialog("⚙️ Настройка порога")
def threshold_dialog(item_id, current_name, current_threshold):
    st.write(f"Настраиваем порог для **{current_name}**")
    new_thr = st.number_input("Минимальное количество для уведомления", min_value=0, step=1, value=current_threshold)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Сохранить"):
            update_threshold(item_id, new_thr)
            st.rerun()
    with col2:
        if st.button("❌ Отмена"):
            st.rerun()

@st.dialog("📤 Списание на объект")
def consume_dialog(item_id, item_name, current_quantity, unit):
    st.write(f"Списание **{item_name}**")
    st.caption(f"Доступно: {current_quantity} {unit}")
    
    col1, col2 = st.columns(2)
    with col1:
        qty = st.number_input("Количество", min_value=0.0, step=0.5, max_value=float(current_quantity), value=min(1.0, float(current_quantity)))
    with col2:
        park_names = get_park_names()
        if park_names:
            object_name = st.selectbox("Объект списания", park_names)
        else:
            object_name = st.text_input("Объект*")
    
    user = st.text_input("Кто списывает", value=OWNER_NAME)
    note = st.text_area("Примечание")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Списать", use_container_width=True):
            if qty <= 0:
                st.error("Количество должно быть > 0")
            elif not object_name:
                st.error("Укажите объект")
            else:
                success, message = consume_item(item_id, qty, object_name, user, note)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    with col2:
        if st.button("❌ Отмена", use_container_width=True):
            st.rerun()

@st.dialog("📷 QR-код")
def qr_dialog(item_id, item_name):
    st.write(f"QR-код для **{item_name}**")
    app_url = "https://garage-app-2-fcfztptpvqdfqmrh3vczif.streamlit.app"
    qr_data = f"{app_url}?search={item_id}"
    qr = qrcode.make(qr_data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    st.image(buf, caption=f"QR для {item_name}", use_container_width=True)
    st.download_button(
        label="⬇️ Скачать QR",
        data=buf.getvalue(),
        file_name=f"qr_{item_name}_{item_id}.png",
        mime="image/png"
    )
