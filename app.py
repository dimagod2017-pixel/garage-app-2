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
st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

# --- ЗЕЛЁНАЯ ЦВЕТОВАЯ СХЕМА ---
PRIMARY_COLOR = "#2E7D32"
SECONDARY_COLOR = "#4CAF50"

st.title("🌿 Мой Склад")
st.caption("Добро пожаловать! Храните и находите вещи легко.")

# --- КАСТОМНЫЙ CSS ---
st.markdown(f"""
    <style>
        .stApp {{ background-color: #f0f7f0; }}
        .main-header {{
            background: linear-gradient(135deg, {PRIMARY_COLOR}, {SECONDARY_COLOR});
            padding: 1.5rem;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(46, 125, 50, 0.3);
        }}
        .main-header h1 {{ margin: 0; font-size: 2.5rem; font-weight: 700; }}
        .main-header p {{ margin: 0; font-size: 1.2rem; opacity: 0.95; }}
        
        /* --- ВЕРТИКАЛЬНЫЕ КНОПКИ ДЛЯ КОМПЬЮТЕРА --- */
        @media (min-width: 769px) {{
            .vertical-btn-wrap {{
                display: flex !important;
                flex-direction: column !important;
                gap: 0.3rem !important;
                width: 100% !important;
            }}
            .vertical-btn-wrap .stButton {{
                width: 100% !important;
            }}
            .vertical-btn-wrap .stButton button {{
                width: 100% !important;
                padding: 0.5rem 0.8rem !important;
                font-size: 0.8rem !important;
                min-height: 36px !important;
                border-radius: 8px !important;
                white-space: nowrap !important;
                font-weight: 600 !important;
            }}
        }}
        @media (max-width: 768px) {{
            .vertical-btn-wrap {{
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: wrap !important;
                gap: 0.15rem !important;
            }}
            .vertical-btn-wrap .stButton {{
                flex: 1 !important;
                min-width: 35px !important;
            }}
            .vertical-btn-wrap .stButton button {{
                padding: 0.15rem 0.2rem !important;
                font-size: 0.5rem !important;
                min-height: 24px !important;
                border-radius: 4px !important;
                white-space: nowrap !important;
                font-weight: 600 !important;
            }}
        }}
        
        /* --- ЦВЕТНЫЕ КНОПКИ --- */
        .btn-edit .stButton button {{ 
            background-color: #4CAF50 !important; 
            color: white !important;
            box-shadow: 0 2px 6px rgba(76, 175, 80, 0.3);
        }}
        .btn-edit .stButton button:hover {{ 
            background-color: #388E3C !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
        }}
        .btn-threshold .stButton button {{ 
            background-color: #FF9800 !important; 
            color: white !important;
            box-shadow: 0 2px 6px rgba(255, 152, 0, 0.3);
        }}
        .btn-threshold .stButton button:hover {{ 
            background-color: #F57C00 !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 152, 0, 0.4);
        }}
        .btn-consume .stButton button {{ 
            background-color: #2196F3 !important; 
            color: white !important;
            box-shadow: 0 2px 6px rgba(33, 150, 243, 0.3);
        }}
        .btn-consume .stButton button:hover {{ 
            background-color: #1976D2 !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(33, 150, 243, 0.4);
        }}
        .btn-qr .stButton button {{ 
            background-color: #9C27B0 !important; 
            color: white !important;
            box-shadow: 0 2px 6px rgba(156, 39, 176, 0.3);
        }}
        .btn-qr .stButton button:hover {{ 
            background-color: #7B1FA2 !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(156, 39, 176, 0.4);
        }}
        .btn-move .stButton button {{ 
            background-color: #FF5722 !important; 
            color: white !important;
            box-shadow: 0 2px 6px rgba(255, 87, 34, 0.3);
        }}
        .btn-move .stButton button:hover {{ 
            background-color: #E64A19 !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 87, 34, 0.4);
        }}
        .btn-delete .stButton button {{ 
            background-color: #f44336 !important; 
            color: white !important;
            box-shadow: 0 2px 6px rgba(244, 67, 54, 0.3);
        }}
        .btn-delete .stButton button:hover {{ 
            background-color: #c62828 !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(244, 67, 54, 0.4);
        }}
        
        /* --- Tooltip при наведении --- */
        .stButton button[title]:hover::after {{
            content: attr(title);
            position: absolute;
            bottom: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a1a;
            color: #fff;
            padding: 0.3rem 0.7rem;
            border-radius: 6px;
            font-size: 0.7rem;
            white-space: nowrap;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .stButton button[title]:hover::before {{
            content: '';
            position: absolute;
            bottom: calc(100% + 4px);
            left: 50%;
            transform: translateX(-50%);
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #1a1a1a;
            z-index: 1000;
        }}
        .stButton button {{
            position: relative;
        }}
        
        /* --- Тёмная тема для цветных кнопок --- */
        .dark-mode .btn-edit .stButton button {{ background-color: #2E7D32 !important; }}
        .dark-mode .btn-edit .stButton button:hover {{ background-color: #1B5E20 !important; }}
        .dark-mode .btn-threshold .stButton button {{ background-color: #E65100 !important; }}
        .dark-mode .btn-threshold .stButton button:hover {{ background-color: #BF360C !important; }}
        .dark-mode .btn-consume .stButton button {{ background-color: #0D47A1 !important; }}
        .dark-mode .btn-consume .stButton button:hover {{ background-color: #0D47A1 !important; }}
        .dark-mode .btn-qr .stButton button {{ background-color: #4A148C !important; }}
        .dark-mode .btn-qr .stButton button:hover {{ background-color: #4A148C !important; }}
        .dark-mode .btn-move .stButton button {{ background-color: #BF360C !important; }}
        .dark-mode .btn-move .stButton button:hover {{ background-color: #BF360C !important; }}
        .dark-mode .btn-delete .stButton button {{ background-color: #B71C1C !important; }}
        .dark-mode .btn-delete .stButton button:hover {{ background-color: #B71C1C !important; }}
        
        div[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #f5faf5, #e8f5e9);
            border-right: 2px solid {SECONDARY_COLOR};
        }}
        div[data-testid="stSidebar"] * {{ color: #1e3a1e !important; }}
        
        .critical-warning {{
            background: linear-gradient(135deg, #ffebee, #ffcdd2);
            border-left: 5px solid #f44336;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }}
        .warning-warning {{
            background: linear-gradient(135deg, #fff3e0, #ffe0b2);
            border-left: 5px solid #ff9800;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }}
        
        /* --- Статистика --- */
        .stat-btn-wrap {{
            background: white;
            border: 2px solid #e8f5e9;
            border-radius: 14px;
            padding: 0.8rem 0.3rem;
            text-align: center;
            transition: all 0.3s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            min-height: 90px;
            width: 100%;
            cursor: pointer;
        }}
        .stat-btn-wrap:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(46, 125, 50, 0.2);
            border-color: {SECONDARY_COLOR};
        }}
        .stat-number {{
            font-size: 2.2rem;
            font-weight: bold;
            color: {PRIMARY_COLOR};
            line-height: 1.2;
        }}
        .stat-label {{
            color: #555;
            font-size: 0.85rem;
            font-weight: 500;
            margin-top: 2px;
        }}
        @media (max-width: 768px) {{
            .stat-number {{ font-size: 1.6rem; }}
            .stat-label {{ font-size: 0.65rem; }}
            .stat-btn-wrap {{ min-height: 65px; padding: 0.4rem 0.2rem; }}
        }}
    </style>
""", unsafe_allow_html=True)

# --- ШАПКА ---
st.markdown(f"""
    <div class="main-header">
        <h1>🌿 Мой Склад</h1>
        <p>👋 Добро пожаловать!</p>
    </div>
""", unsafe_allow_html=True)

# --- ТЁМНАЯ ТЕМА ---
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

with st.sidebar:
    dark_mode_toggle = st.toggle("🌙 Тёмная тема", value=st.session_state.dark_mode)
    if dark_mode_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode_toggle
        st.rerun()

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

def delete_consumption_record(record_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_id, quantity FROM consumption WHERE id = ?", (record_id,))
    result = c.fetchone()
    if result:
        item_id, quantity = result
        c.execute("UPDATE items SET quantity = quantity + ? WHERE id = ?", (quantity, item_id))
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

def search_items(query, room_filter=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    query_like = f"%{query}%"
    query_lower = f"%{query.lower()}%"
    
    if room_filter and room_filter != "Все помещения":
        c.execute("""
            SELECT * FROM items 
            WHERE (name LIKE ? 
                   OR category LIKE ? 
                   OR location LIKE ? 
                   OR description LIKE ? 
                   OR application LIKE ?
                   OR LOWER(name) LIKE ? 
                   OR LOWER(category) LIKE ? 
                   OR LOWER(location) LIKE ? 
                   OR LOWER(description) LIKE ? 
                   OR LOWER(application) LIKE ?)
            AND room = ?
        """, (query_like, query_like, query_like, query_like, query_like, 
              query_lower, query_lower, query_lower, query_lower, query_lower,
              room_filter))
    else:
        c.execute("""
            SELECT * FROM items 
            WHERE name LIKE ? 
               OR category LIKE ? 
               OR location LIKE ? 
               OR description LIKE ? 
               OR application LIKE ?
               OR LOWER(name) LIKE ? 
               OR LOWER(category) LIKE ? 
               OR LOWER(location) LIKE ? 
               OR LOWER(description) LIKE ? 
               OR LOWER(application) LIKE ?
        """, (query_like, query_like, query_like, query_like, query_like,
              query_lower, query_lower, query_lower, query_lower, query_lower))
    
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

init_db()

# --- СТАТИСТИКА ---
total_items, total_rooms, low_stock_count, top_categories, total_equipment, total_rooms_list, total_consumption = get_statistics()

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    if st.button(
        "📦\n" + str(total_items) + "\nВещи",
        use_container_width=True,
        key="stat_items",
        help="Показать все вещи"
    ):
        st.session_state.active_tab = 1
        st.session_state.selected_room = None
        st.session_state.show_low_stock = False
        st.rerun()

with col2:
    if st.button(
        "🏠\n" + str(total_rooms_list) + "\nПомещения",
        use_container_width=True,
        key="stat_rooms",
        help="Показать помещения"
    ):
        st.session_state.active_tab = 4
        st.session_state.selected_room = None
        st.session_state.show_low_stock = False
        st.rerun()

with col3:
    if st.button(
        "⚠️\n" + str(low_stock_count) + "\nПополнить",
        use_container_width=True,
        key="stat_low_stock",
        help="Показать что нужно пополнить"
    ):
        st.session_state.active_tab = 0
        st.session_state.show_low_stock = True
        st.session_state.selected_room = None
        st.rerun()

with col4:
    top_cat_str = "\n".join([f"{cat}" for cat, count in top_categories[:2]]) if top_categories else "—"
    st.button(
        "🏆\nТоп\n" + top_cat_str,
        use_container_width=True,
        key="stat_top",
        disabled=True,
        help="Топ категорий (неактивно)"
    )

with col5:
    if st.button(
        "🚜\n" + str(total_equipment) + "\nТехника",
        use_container_width=True,
        key="stat_equipment",
        help="Показать технику"
    ):
        st.session_state.active_tab = 2
        st.session_state.selected_equipment = None
        st.rerun()

with col6:
    if st.button(
        "📤\n" + str(total_consumption) + "\nСписано",
        use_container_width=True,
        key="stat_consumption",
        help="Показать историю списаний"
    ):
        st.session_state.active_tab = 3
        st.rerun()

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
    st.markdown("### 🌿 Управление")
    
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
active_tab = st.session_state.get("active_tab", 0)
show_low_stock = st.session_state.get("show_low_stock", False)
selected_room = st.session_state.get("selected_room", None)
selected_equipment = st.session_state.get("selected_equipment", None)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📤 История списаний", "🏠 Помещения"])

with tab1:
    col_search, col_btn = st.columns([5, 1])
    with col_search:
        search_query = st.text_input(
            "🔍 Что ищем?", 
            placeholder="Введите название, категорию, место...", 
            key="search_input",
            value=""
        )
        if search_query and len(search_query) > 0:
            if search_query[0].islower():
                if len(search_query) > 1:
                    search_query = search_query[0].upper() + search_query[1:]
                else:
                    search_query = search_query.upper()
    
    with col_btn:
        st.write("")
        search_clicked = st.button("🔍 Найти", use_container_width=True)
    
    if show_low_stock:
        st.info("📋 **Вещи, которые нужно пополнить:**")
        low_items = get_low_stock_items()
        if low_items:
            for item in low_items:
                qty = item[9]
                name = item[1]
                unit = item[10]
                room = item[4]
                threshold = item[11]
                st.write(f"• **{name}** — {qty} {unit} (порог: {threshold}) в **{room}**")
        else:
            st.success("✅ Все вещи в норме!")
        st.divider()
        st.session_state.show_low_stock = False
    
    rooms = ["Все помещения"] + get_room_names()
    room_filter = st.selectbox("🏠 Помещение", rooms, key="room_filter_tab1")
    
    if search_query:
        st.caption(f"🔎 Ищем: **{search_query}**")
        items = search_items(search_query, room_filter)
    else:
        items = get_all_items(room_filter)
    
    st.subheader(f"📌 Найдено: {len(items)}")

    if not items:
        st.info("🌱 Ничего нет. Добавьте через меню.")
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
                    
                    # --- ВЕРТИКАЛЬНЫЕ ЦВЕТНЫЕ КНОПКИ ---
                    st.markdown("""
                        <style>
                            @media (min-width: 769px) {
                                .vertical-btn-wrap {
                                    display: flex !important;
                                    flex-direction: column !important;
                                    gap: 0.3rem !important;
                                    width: 100% !important;
                                }
                                .vertical-btn-wrap .stButton {
                                    width: 100% !important;
                                }
                                .vertical-btn-wrap .stButton button {
                                    width: 100% !important;
                                    padding: 0.5rem 0.8rem !important;
                                    font-size: 0.8rem !important;
                                    min-height: 36px !important;
                                    border-radius: 8px !important;
                                    white-space: nowrap !important;
                                    font-weight: 600 !important;
                                }
                            }
                            @media (max-width: 768px) {
                                .vertical-btn-wrap {
                                    display: flex !important;
                                    flex-direction: row !important;
                                    flex-wrap: wrap !important;
                                    gap: 0.15rem !important;
                                }
                                .vertical-btn-wrap .stButton {
                                    flex: 1 !important;
                                    min-width: 35px !important;
                                }
                                .vertical-btn-wrap .stButton button {
                                    padding: 0.15rem 0.2rem !important;
                                    font-size: 0.5rem !important;
                                    min-height: 24px !important;
                                    border-radius: 4px !important;
                                    white-space: nowrap !important;
                                    font-weight: 600 !important;
                                }
                            }
                            .btn-edit .stButton button { background-color: #4CAF50 !important; color: white !important; }
                            .btn-edit .stButton button:hover { background-color: #388E3C !important; }
                            .btn-threshold .stButton button { background-color: #FF9800 !important; color: white !important; }
                            .btn-threshold .stButton button:hover { background-color: #F57C00 !important; }
                            .btn-consume .stButton button { background-color: #2196F3 !important; color: white !important; }
                            .btn-consume .stButton button:hover { background-color: #1976D2 !important; }
                            .btn-qr .stButton button { background-color: #9C27B0 !important; color: white !important; }
                            .btn-qr .stButton button:hover { background-color: #7B1FA2 !important; }
                            .btn-move .stButton button { background-color: #FF5722 !important; color: white !important; }
                            .btn-move .stButton button:hover { background-color: #E64A19 !important; }
                            .btn-delete .stButton button { background-color: #f44336 !important; color: white !important; }
                            .btn-delete .stButton button:hover { background-color: #c62828 !important; }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('<div class="vertical-btn-wrap">', unsafe_allow_html=True)
                    
                    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5, col_btn6 = st.columns(6)
                    with col_btn1:
                        st.markdown('<div class="btn-edit">', unsafe_allow_html=True)
                        if st.button(
                            "✏️ Кол-во", 
                            key=f"edit_{item_id}", 
                            use_container_width=True,
                            help="Изменить количество"
                        ):
                            st.session_state[f"edit_mode_{item_id}"] = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_btn2:
                        st.markdown('<div class="btn-threshold">', unsafe_allow_html=True)
                        if st.button(
                            "⚙️ Порог", 
                            key=f"thr_{item_id}", 
                            use_container_width=True,
                            help="Настроить порог"
                        ):
                            st.session_state[f"thr_mode_{item_id}"] = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_btn3:
                        st.markdown('<div class="btn-consume">', unsafe_allow_html=True)
                        if st.button(
                            "📤 Списать", 
                            key=f"cons_{item_id}", 
                            use_container_width=True,
                            help="Списать на объект"
                        ):
                            st.session_state[f"cons_mode_{item_id}"] = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_btn4:
                        st.markdown('<div class="btn-qr">', unsafe_allow_html=True)
                        if st.button(
                            "📷 QR", 
                            key=f"qr_{item_id}", 
                            use_container_width=True,
                            help="Сгенерировать QR"
                        ):
                            st.session_state[f"qr_mode_{item_id}"] = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_btn5:
                        st.markdown('<div class="btn-move">', unsafe_allow_html=True)
                        if st.button(
                            "🚚 Пер.", 
                            key=f"move_{item_id}", 
                            use_container_width=True,
                            help="Переместить"
                        ):
                            st.session_state[f"move_mode_{item_id}"] = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_btn6:
                        st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
                        if st.button(
                            "🗑️ Удалить", 
                            key=f"del_{item_id}", 
                            use_container_width=True,
                            help="Удалить вещь"
                        ):
                            delete_item(item_id)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
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
        st.info("🌱 В базе пока нет вещей. Добавьте первую вещь через боковое меню!")
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
    st.subheader("🚜 Управление техникой")
    
    if selected_equipment:
        st.markdown(f"### 🔧 История списаний на **{selected_equipment}**")
        consumptions = get_consumption_by_equipment(selected_equipment)
        if consumptions:
            for c in consumptions:
                record_id, item_id, qty, unit, obj_name, user, date, item_name = c
                st.write(f"• **{item_name}** → {qty} {unit} (списал {user}, {date})")
        else:
            st.info(f"🌱 Нет списаний на '{selected_equipment}'")
        if st.button("⬅️ Назад к списку техники"):
            st.session_state.selected_equipment = None
            st.rerun()
        st.divider()
    
    with st.expander("➕ Добавить технику", expanded=False):
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
        st.info("🌱 Пока нет техники. Добавьте первую!")
    else:
        st.caption(f"Всего техники: {len(equipment_list)}")
        for eq in equipment_list:
            eq_id, eq_name, eq_number, eq_date = eq
            cons = get_consumption_by_equipment(eq_name)
            cons_count = len(cons)
            
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                display_name = f"🚜 {eq_name}"
                if eq_number:
                    display_name += f" ({eq_number})"
                if cons_count > 0:
                    display_name += f" — {cons_count} списаний"
                st.markdown(f"**{display_name}**")
                st.caption(f"Добавлено: {eq_date[:10]}")
            with col2:
                if st.button("📊 История", key=f"eq_history_{eq_id}"):
                    st.session_state.selected_equipment = eq_name
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_eq_{eq_id}"):
                    delete_equipment(eq_id)
                    st.rerun()

with tab4:
    st.subheader("📤 История списаний")
    
    all_consumption = get_all_consumption()
    if not all_consumption:
        st.info("🌱 Пока нет списаний")
    else:
        st.caption(f"Всего записей: {len(all_consumption)}")
        
        objects = list(set([c[4] for c in all_consumption]))
        filter_obj = st.selectbox("🔍 Фильтр по объекту", ["Все"] + objects)
        
        filtered = [c for c in all_consumption if filter_obj == "Все" or c[4] == filter_obj]
        
        for c in filtered:
            record_id, item_id, qty, unit, obj_name, user, date, item_name = c
            
            col1, col2, col3 = st.columns([8, 1, 1])
            with col1:
                st.write(f"• **{item_name}** → {qty} {unit} на **{obj_name}** (списал {user}, {date})")
            with col2:
                if st.button("🗑️", key=f"del_cons_{record_id}", help="Удалить запись"):
                    delete_consumption_record(record_id)
                    st.success(f"✅ Запись удалена! Количество '{item_name}' восстановлено на складе.")
                    st.rerun()
            with col3:
                if st.button("↩️", key=f"restore_cons_{record_id}", help="Вернуть на склад"):
                    delete_consumption_record(record_id)
                    st.success(f"✅ Запись удалена! Количество '{item_name}' восстановлено на складе.")
                    st.rerun()
        
        st.caption("🗑️ — удалить запись и вернуть количество на склад")

with tab5:
    st.subheader("🏠 Управление помещениями")
    
    if selected_room:
        st.markdown(f"### 📦 Содержимое помещения **{selected_room}**")
        items_in_room = get_items_by_room(selected_room)
        if items_in_room:
            for item in items_in_room:
                if len(item) >= 14:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold, application, installed_photo = item[:14]
                else:
                    item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item[:12]
                    application = ""
                try:
                    qty = float(quantity)
                except:
                    qty = 0
                status = "🔴" if qty <= 0 else "🟡" if qty <= threshold else "🟢"
                st.write(f"{status} **{name}** — {qty} {unit} ({location})")
                if application:
                    st.caption(f"  📝 {application}")
        else:
            st.info(f"🌱 В помещении '{selected_room}' пока нет вещей")
        if st.button("⬅️ Назад к списку помещений"):
            st.session_state.selected_room = None
            st.rerun()
        st.divider()
    
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
        st.info("🌱 Пока нет помещений. Добавьте первое!")
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
                if st.button("🗑️", key=f"del_room_{room_id}"):
                    delete_room(room_id)
                    st.rerun()
