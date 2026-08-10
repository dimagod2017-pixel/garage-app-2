import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from PIL import Image
import shutil
import base64
import time
import pandas as pd
import io

# ============================================================
# 1. НАСТРОЙКА И ПЕРЕМЕННЫЕ
# ============================================================
UTC_OFFSET = 3

def now_local():
    return (datetime.utcnow() + timedelta(hours=UTC_OFFSET)).strftime("%Y-%m-%d %H:%M")

def now_local_file():
    return now_local().replace(" ", "_").replace(":", "")

for folder in ["images", "images/items", "images/take", "backups", "backgrounds"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

if "user" not in st.session_state:
    st.session_state.user = None
if "dismissed_notifications" not in st.session_state:
    st.session_state.dismissed_notifications = []

st.set_page_config(page_title="Мой Склад", page_icon="📦", layout="wide")

# ============================================================
# ПРИМЕНЕНИЕ ФОНА
# ============================================================
def apply_background():
    try:
        if os.path.exists("backgrounds") and os.path.isdir("backgrounds"):
            bg_files = [f for f in os.listdir("backgrounds") if f.startswith("background.")]
            if bg_files:
                bg_path = f"backgrounds/{bg_files[0]}"
                ext = bg_path.split('.')[-1].lower()
                mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                with open(bg_path, 'rb') as f:
                    bg_base64 = base64.b64encode(f.read()).decode()
                opacity = st.session_state.get("bg_opacity", 0.85)
                st.markdown(f"""
                <style>
                .stApp {{
                    background-image: url('data:{mime_type};base64,{bg_base64}') !important;
                    background-size: cover !important;
                    background-position: center !important;
                    background-attachment: fixed !important;
                    background-repeat: no-repeat !important;
                }}
                .stApp::before {{
                    content: '' !important;
                    position: fixed !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100% !important;
                    height: 100% !important;
                    background: rgba(255, 255, 255, {opacity}) !important;
                    z-index: -1 !important;
                    pointer-events: none !important;
                }}
                .main .block-container {{
                    background: transparent !important;
                }}
                </style>
                """, unsafe_allow_html=True)
    except:
        pass

apply_background()

# ============================================================
# 🎨 КРАСИВЫЙ ДИЗАЙН (CSS)
# ============================================================
st.markdown("""
<style>
h1 {
    background: linear-gradient(135deg, #2563eb, #10b981, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.5rem;
    margin-bottom: 1rem;
}
h2 {
    color: #1e293b;
    font-weight: 700;
    border-bottom: 3px solid #10b981;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}
h3 {
    color: #334155;
    font-weight: 600;
}
.stContainer {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
    transition: all 0.3s ease;
}
.stContainer:hover {
    box-shadow: 0 10px 25px rgba(16, 185, 129, 0.15);
    transform: translateY(-2px);
}
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f0fdf4, #ffffff);
    border-radius: 12px;
    padding: 15px;
    border: 1px solid #d1fae5;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    transition: all 0.3s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 6px 12px rgba(16, 185, 129, 0.2);
    transform: translateY(-2px);
}
[data-testid="stMetric"] label { font-weight: 600; color: #64748b; }
[data-testid="stMetric"] div { font-weight: 700; color: #065f46; }
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.3s ease;
    border: none;
    padding: 10px 20px;
    font-size: 14px;
    letter-spacing: 0.3px;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(16, 185, 129, 0.3);
}
.stButton > button:active { transform: translateY(0); }
.stButton > button:not([kind="secondary"]):not([kind="tertiary"]) {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    border-radius: 10px;
    border: 2px solid #e2e8f0;
    padding: 10px 15px;
    font-size: 14px;
    transition: all 0.3s ease;
    background: #f8fafc;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
    background: white;
}
.streamlit-expanderHeader {
    background: linear-gradient(135deg, #f0fdf4, #ffffff);
    border-radius: 10px;
    border: 1px solid #d1fae5;
    font-weight: 600;
    color: #065f46;
    padding: 12px 15px;
    transition: all 0.3s ease;
}
.streamlit-expanderHeader:hover {
    background: linear-gradient(135deg, #d1fae5, #f0fdf4);
    border-color: #10b981;
}
[data-testid="stExpander"] {
    border-radius: 10px;
    margin: 8px 0;
    border: 1px solid #e2e8f0;
    overflow: hidden;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a, #1e293b, #064e3b);
    padding: 20px;
}
[data-testid="stSidebar"] * { color: #f1f5f9; }
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] h2 { color: #ecfdf5; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: #f1f5f9;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(16, 185, 129, 0.2);
    border-color: #10b981;
}
[data-testid="stTabs"] {
    background: white;
    border-radius: 12px;
    padding: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.stTabs [role="tab"] {
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    color: #64748b;
    transition: all 0.3s ease;
}
.stTabs [role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
}
.stAlert { border-radius: 10px; border: none; font-weight: 500; }
.stSuccess { background: linear-gradient(135deg, #d1fae5, #a7f3d0); color: #065f46; }
.stWarning { background: linear-gradient(135deg, #fef3c7, #fde68a); color: #92400e; }
.stError { background: linear-gradient(135deg, #fee2e2, #fecaca); color: #991b1b; }
.stInfo { background: linear-gradient(135deg, #dbeafe, #bfdbfe); color: #1e40af; }
[data-testid="stFileUploader"] {
    border-radius: 10px;
    border: 2px dashed #d1fae5;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
}
[data-testid="stFileUploader"]:hover { border-color: #10b981; background: #f0fdf4; }
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.stContainer, .stExpander { animation: fadeIn 0.5s ease; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 10px; }
::-webkit-scrollbar-thumb { background: #65a57a; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #4da363; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. БАЗА ДАННЫХ
# ============================================================
def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY, name TEXT, location TEXT, room TEXT,
        date_added TEXT, quantity REAL, unit TEXT,
        threshold INTEGER DEFAULT 1, photos_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
        number TEXT, date_added TEXT,
        service_interval_days INTEGER DEFAULT 0,
        service_interval_hours INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment_aggregates (
        id INTEGER PRIMARY KEY AUTOINCREMENT, equipment_name TEXT,
        aggregate_name TEXT, aggregate_number TEXT, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
        date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
        quantity REAL, unit TEXT, description TEXT, photo TEXT,
        user TEXT, date TEXT, status TEXT DEFAULT 'pending',
        seen INTEGER DEFAULT 0, admin_comment TEXT,
        suggested_item_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS consumption (
        id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT,
        quantity REAL, unit TEXT, object_name TEXT, user TEXT,
        date TEXT, equipment_name TEXT, equipment_number TEXT,
        photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS item_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT,
        photo_path TEXT, date_added TEXT, is_main INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE,
        password TEXT, full_name TEXT, role TEXT DEFAULT 'employee',
        status TEXT DEFAULT 'pending', created_at TEXT,
        approved_by TEXT)''')
    
    # === ИСПРАВЛЕННАЯ ТАБЛИЦА maintenance ===
    # Проверяем, есть ли колонка to_type в существующей таблице
    c.execute("PRAGMA table_info(maintenance)")
    columns = [col[1] for col in c.fetchall()]
    if 'to_type' not in columns:
        # Если колонки нет – пересоздаём таблицу
        c.execute("DROP TABLE IF EXISTS maintenance")
        c.execute('''CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_name TEXT,
            maintenance_date TEXT,
            next_maintenance_date TEXT,
            description TEXT,
            maintenance_type TEXT DEFAULT 'TO',
            to_type TEXT DEFAULT 'TO-1',
            created_by TEXT,
            created_at TEXT
        )''')
    else:
        # Если колонка есть – просто создаём таблицу (если её почему-то нет)
        c.execute('''CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_name TEXT,
            maintenance_date TEXT,
            next_maintenance_date TEXT,
            description TEXT,
            maintenance_type TEXT DEFAULT 'TO',
            to_type TEXT DEFAULT 'TO-1',
            created_by TEXT,
            created_at TEXT
        )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS equipment_to_intervals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_name TEXT,
        to_type TEXT DEFAULT 'TO-1',
        interval_days INTEGER DEFAULT 0,
        interval_hours INTEGER DEFAULT 0,
        created_by TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_name TEXT,
        username TEXT,
        assigned_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_name TEXT,
        record_date TEXT,
        value REAL,
        usage_type TEXT DEFAULT 'motohours',
        created_by TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS service_kits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kit_name TEXT,
        equipment_name TEXT,
        description TEXT,
        created_by TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS service_kit_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kit_id INTEGER,
        item_id TEXT,
        quantity REAL
    )''')
    c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,full_name,role,status,created_at) VALUES (?,?,?,?,?,?)",
                  ("admin","1209","Администратор","admin","active",now_local()))
    else:
        c.execute("UPDATE users SET role='admin', status='active' WHERE username='admin'")
    try:
        c.execute("ALTER TABLE equipment_aggregates DROP COLUMN aggregate_type")
    except:
        pass
    conn.commit()
    conn.close()

init_db()
# ============================================================
# 3. ФУНКЦИИ БАЗЫ ДАННЫХ
# ============================================================
def get_room_names():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT name FROM rooms ORDER BY name")
    res = [row[0] for row in c.fetchall()]
    conn.close()
    return res

def add_room(name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?,?)", (name, now_local()))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def get_equipment():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment ORDER BY name")
    res = c.fetchall()
    conn.close()
    return res

def add_equipment(name, number=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment (name, number, date_added) VALUES (?,?,?)",
                  (name, number, now_local()))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def search_items(query):
    if not query:
        return get_all_items()
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    words = query.strip().split()
    conditions = []
    params = []
    for word in words:
        like_word = f"%{word}%"
        conditions.append("(name LIKE ? OR location LIKE ? OR room LIKE ?)")
        params.extend([like_word, like_word, like_word])
    where_clause = " AND ".join(conditions)
    sql = f"SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items WHERE {where_clause} ORDER BY date_added DESC"
    c.execute(sql, params)
    res = c.fetchall()
    conn.close()
    return res

def search_equipment_extended(query):
    if not query:
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        results = []
        c.execute("SELECT name, number FROM equipment ORDER BY name")
        for row in c.fetchall():
            eq_name, eq_num = row[0], row[1] or ""
            display = f"{eq_name}" + (f" (№{eq_num})" if eq_num else "")
            results.append({"display": display, "eq_name": eq_name, "eq_number": eq_num,
                            "agg_name": None, "agg_number": None})
        c.execute('''SELECT e.name, e.number, a.aggregate_name, a.aggregate_number
                     FROM equipment_aggregates a JOIN equipment e ON a.equipment_name = e.name
                     ORDER BY e.name, a.aggregate_name''')
        for row in c.fetchall():
            eq_name, eq_num, agg_name, agg_num = row[0], row[1] or "", row[2], row[3] or ""
            display = f"{eq_name}" + (f" (№{eq_num})" if eq_num else "") + f" 🔧 Агрегат: {agg_name}" + (f" (№{agg_num})" if agg_num else "")
            results.append({"display": display, "eq_name": eq_name, "eq_number": eq_num,
                            "agg_name": agg_name, "agg_number": agg_num})
        conn.close()
        seen = set()
        unique = []
        for r in results:
            key = (r['eq_name'], r['eq_number'], r['agg_name'], r['agg_number'])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    words = query.strip().split()
    results = []
    eq_conditions = []
    eq_params = []
    for word in words:
        like_word = f"%{word}%"
        eq_conditions.append("(name LIKE ? OR number LIKE ?)")
        eq_params.extend([like_word, like_word])
    eq_where = " AND ".join(eq_conditions)
    c.execute(f"SELECT name, number FROM equipment WHERE {eq_where} ORDER BY name", eq_params)
    for row in c.fetchall():
        eq_name, eq_num = row[0], row[1] or ""
        display = f"{eq_name}" + (f" (№{eq_num})" if eq_num else "")
        results.append({"display": display, "eq_name": eq_name, "eq_number": eq_num,
                        "agg_name": None, "agg_number": None})
    agg_conditions = []
    agg_params = []
    for word in words:
        like_word = f"%{word}%"
        agg_conditions.append("(a.aggregate_name LIKE ? OR a.aggregate_number LIKE ? OR e.name LIKE ? OR e.number LIKE ?)")
        agg_params.extend([like_word, like_word, like_word, like_word])
    agg_where = " AND ".join(agg_conditions)
    c.execute(f'''SELECT e.name, e.number, a.aggregate_name, a.aggregate_number
                 FROM equipment_aggregates a JOIN equipment e ON a.equipment_name = e.name
                 WHERE {agg_where}
                 ORDER BY e.name, a.aggregate_name''', agg_params)
    for row in c.fetchall():
        eq_name, eq_num, agg_name, agg_num = row[0], row[1] or "", row[2], row[3] or ""
        display = f"{eq_name}" + (f" (№{eq_num})" if eq_num else "") + f" 🔧 Агрегат: {agg_name}" + (f" (№{agg_num})" if agg_num else "")
        results.append({"display": display, "eq_name": eq_name, "eq_number": eq_num,
                        "agg_name": agg_name, "agg_number": agg_num})
    conn.close()
    seen = set()
    unique = []
    for r in results:
        key = (r['eq_name'], r['eq_number'], r['agg_name'], r['agg_number'])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items ORDER BY date_added DESC")
    res = c.fetchall()
    conn.close()
    return res

def add_item(name, location, room, quantity, unit):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, location, room, date_added, quantity, unit, threshold) VALUES (?,?,?,?,?,?,?,?)",
              (item_id, name, location, room, now_local(), quantity, unit, 1))
    conn.commit()
    conn.close()
    return item_id

def update_item(item_id, name, location, room, quantity, unit, threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET name=?, location=?, room=?, quantity=?, unit=?, threshold=? WHERE id=?",
              (name, location, room, quantity, unit, threshold, item_id))
    conn.commit()
    conn.close()

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity=? WHERE id=?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def move_item(item_id, new_location, new_room):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET location=?, room=? WHERE id=?", (new_location, new_room, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT photo_path FROM item_photos WHERE item_id=?", (item_id,))
    for photo in c.fetchall():
        if os.path.exists(photo[0]):
            try: os.remove(photo[0])
            except: pass
    c.execute("DELETE FROM item_photos WHERE item_id=?", (item_id,))
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_low_stock():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items WHERE quantity <= threshold ORDER BY quantity ASC")
    res = c.fetchall()
    conn.close()
    return res

def add_item_photo(item_id, photo_path, is_main=False):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if is_main:
        c.execute("UPDATE item_photos SET is_main=0 WHERE item_id=?", (item_id,))
    c.execute("INSERT INTO item_photos (item_id, photo_path, date_added, is_main) VALUES (?,?,?,?)",
              (item_id, photo_path, now_local(), 1 if is_main else 0))
    c.execute("UPDATE items SET photos_count = photos_count + 1 WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_item_photos(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, photo_path, is_main FROM item_photos WHERE item_id=? ORDER BY is_main DESC, date_added DESC", (item_id,))
    res = c.fetchall()
    conn.close()
    return res

def delete_item_photo(photo_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_id, photo_path FROM item_photos WHERE id=?", (photo_id,))
    row = c.fetchone()
    if row:
        item_id, photo_path = row
        if os.path.exists(photo_path):
            try: os.remove(photo_path)
            except: pass
        c.execute("DELETE FROM item_photos WHERE id=?", (photo_id,))
        c.execute("UPDATE items SET photos_count = photos_count - 1 WHERE id=?", (item_id,))
        c.execute("SELECT id FROM item_photos WHERE item_id=? LIMIT 1", (item_id,))
        first = c.fetchone()
        if first:
            c.execute("UPDATE item_photos SET is_main=1 WHERE id=?", (first[0],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def set_main_photo(photo_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_id FROM item_photos WHERE id=?", (photo_id,))
    row = c.fetchone()
    if row:
        item_id = row[0]
        c.execute("UPDATE item_photos SET is_main=0 WHERE item_id=?", (item_id,))
        c.execute("UPDATE item_photos SET is_main=1 WHERE id=?", (photo_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def rotate_photo(path, degrees):
    try:
        img = Image.open(path)
        img = img.rotate(degrees, expand=True)
        img.save(path, quality=95)
        return True
    except:
        return False

def take_item(item_id, quantity, eq_name, eq_number, photo_path=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    if not row or quantity > row[0]:
        conn.close()
        return False, "Недостаточно товара"
    new_q = row[0] - quantity
    c.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item_id))
    user_login = st.session_state.user.get("username", "Пользователь")
    c.execute("""INSERT INTO consumption (item_id, quantity, unit, object_name, user, date, equipment_name, equipment_number, photo)
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (item_id, quantity, row[1], f"{eq_name} (№{eq_number})",
               user_login, now_local(), eq_name, eq_number, photo_path))
    conn.commit()
    conn.close()
    return True, f"✅ Взято {quantity} {row[1]} на {eq_name}"

def get_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM consumption ORDER BY date DESC LIMIT 100")
    res = c.fetchall()
    conn.close()
    return res

def add_request(name, quantity, unit, description, photo_path, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO requests (name, quantity, unit, description, photo, user, date) VALUES (?,?,?,?,?,?,?)",
              (name, quantity, unit, description, photo_path, user, now_local()))
    conn.commit()
    conn.close()

def get_requests(status=None, user=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if status and user:
        c.execute("SELECT * FROM requests WHERE status=? AND user=? ORDER BY date DESC", (status, user))
    elif status:
        c.execute("SELECT * FROM requests WHERE status=? ORDER BY date DESC", (status,))
    elif user:
        c.execute("SELECT * FROM requests WHERE user=? ORDER BY date DESC", (user,))
    else:
        c.execute("SELECT * FROM requests ORDER BY date DESC")
    res = c.fetchall()
    conn.close()
    return res

def update_request_status(req_id, status, comment="", suggested_id=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if suggested_id:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0, suggested_item_id=? WHERE id=?",
                  (status, comment, suggested_id, req_id))
    else:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0 WHERE id=?",
                  (status, comment, req_id))
    conn.commit()
    conn.close()

def delete_request(req_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

def mark_request_seen(req_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET seen=1 WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

def return_request(req_id, reason=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    comment = f"Отклонено: {reason}" if reason else "Отклонено сотрудником"
    c.execute("UPDATE requests SET status='returned', admin_comment=?, seen=0 WHERE id=?", (comment, req_id))
    conn.commit()
    conn.close()

def unpack_request(req):
    return {
        'id': req[0], 'name': req[1] or "", 'quantity': req[2] or 0,
        'unit': req[3] or "", 'description': req[4] or "", 'photo': req[5] or "",
        'user': req[6] or "", 'date': req[7] or "", 'status': req[8] or "pending",
        'seen': req[9] or 0, 'admin_comment': req[10] or "", 'suggested_item_id': req[11] or None
    }

def get_stats():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    stats = {}
    c.execute("SELECT COUNT(*) FROM items")
    stats['items'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM items WHERE quantity <= threshold")
    stats['low'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests WHERE status='pending'")
    stats['pending'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests WHERE status='in_work'")
    stats['in_work'] = c.fetchone()[0]
    conn.close()
    return stats

# ============================================================
# ФУНКЦИИ ДЛЯ ТО, МОТОЧАСОВ, КОМПЛЕКТОВ
# ============================================================
def get_equipment_assignments(username=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if username:
        c.execute("SELECT equipment_name FROM equipment_assignments WHERE username=?", (username,))
    else:
        c.execute("SELECT equipment_name, username FROM equipment_assignments")
    res = c.fetchall()
    conn.close()
    return res

def assign_equipment(equipment_name, username):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment_assignments (equipment_name, username, assigned_date) VALUES (?,?,?)",
                  (equipment_name, username, now_local()))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def remove_assignment(assignment_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM equipment_assignments WHERE id=?", (assignment_id,))
    conn.commit()
    conn.close()

def add_equipment_usage(equipment_name, value, usage_type, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO equipment_usage (equipment_name, record_date, value, usage_type, created_by, created_at) VALUES (?,?,?,?,?,?)",
              (equipment_name, now_local(), value, usage_type, user, now_local()))
    conn.commit()
    conn.close()

def get_equipment_usage(equipment_name=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if equipment_name:
        c.execute("SELECT * FROM equipment_usage WHERE equipment_name=? ORDER BY record_date DESC", (equipment_name,))
    else:
        c.execute("SELECT * FROM equipment_usage ORDER BY record_date DESC")
    res = c.fetchall()
    conn.close()
    return res

def get_last_usage(equipment_name, usage_type='motohours'):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT value FROM equipment_usage WHERE equipment_name=? AND usage_type=? ORDER BY record_date DESC LIMIT 1",
              (equipment_name, usage_type))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def delete_usage(usage_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM equipment_usage WHERE id=?", (usage_id,))
    conn.commit()
    conn.close()

def create_service_kit(kit_name, equipment_name, description, items, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO service_kits (kit_name, equipment_name, description, created_by, created_at) VALUES (?,?,?,?,?)",
              (kit_name, equipment_name, description, user, now_local()))
    kit_id = c.lastrowid
    for item_id, qty in items:
        c.execute("INSERT INTO service_kit_items (kit_id, item_id, quantity) VALUES (?,?,?)", (kit_id, item_id, qty))
    conn.commit()
    conn.close()
    return kit_id

def get_service_kits(equipment_name=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if equipment_name:
        c.execute("SELECT * FROM service_kits WHERE equipment_name=?", (equipment_name,))
    else:
        c.execute("SELECT * FROM service_kits")
    kits = c.fetchall()
    result = []
    for kit in kits:
        c.execute("SELECT item_id, quantity FROM service_kit_items WHERE kit_id=?", (kit[0],))
        items = c.fetchall()
        result.append((kit, items))
    conn.close()
    return result

def delete_service_kit(kit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM service_kit_items WHERE kit_id=?", (kit_id,))
    c.execute("DELETE FROM service_kits WHERE id=?", (kit_id,))
    conn.commit()
    conn.close()

def get_maintenance(equipment_name=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if equipment_name:
        c.execute("SELECT * FROM maintenance WHERE equipment_name=? ORDER BY maintenance_date DESC", (equipment_name,))
    else:
        c.execute("SELECT * FROM maintenance ORDER BY maintenance_date DESC")
    res = c.fetchall()
    conn.close()
    return res

def add_maintenance(equipment_name, maintenance_date, next_date, description, maint_type, to_type, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO maintenance (equipment_name, maintenance_date, next_maintenance_date, description, maintenance_type, to_type, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)",
              (equipment_name, maintenance_date, next_date, description, maint_type, to_type, user, now_local()))
    conn.commit()
    conn.close()

def delete_maintenance(maint_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM maintenance WHERE id=?", (maint_id,))
    conn.commit()
    conn.close()

def get_last_maintenance(equipment_name, to_type=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if to_type:
        c.execute("SELECT maintenance_date, next_maintenance_date FROM maintenance WHERE equipment_name=? AND to_type=? ORDER BY maintenance_date DESC LIMIT 1", (equipment_name, to_type))
    else:
        c.execute("SELECT maintenance_date, next_maintenance_date FROM maintenance WHERE equipment_name=? ORDER BY maintenance_date DESC LIMIT 1", (equipment_name,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)

def get_to_status():
    equipment_list = get_equipment()
    alerts = []
    today = datetime.now().date()
    for eq in equipment_list:
        eq_name = eq[1]
        intervals = get_to_intervals(eq_name)
        if not intervals:
            continue
        for interval in intervals:
            int_id, _, to_type, int_days, int_hours, created_by, _ = interval
            last_date, next_date = get_last_maintenance(eq_name, to_type)
            if next_date:
                next_dt = datetime.strptime(next_date[:10], "%Y-%m-%d").date()
                days_left = (next_dt - today).days
                if days_left < 0:
                    alerts.append((eq_name, "overdue", f"{to_type}: просрочено на {-days_left} дн."))
                elif days_left <= 7:
                    alerts.append((eq_name, "soon", f"{to_type}: через {days_left} дн."))
            elif last_date and int_days > 0:
                last_dt = datetime.strptime(last_date[:10], "%Y-%m-%d").date()
                next_dt = last_dt + timedelta(days=int_days)
                days_left = (next_dt - today).days
                if days_left < 0:
                    alerts.append((eq_name, "overdue", f"{to_type}: просрочено на {-days_left} дн."))
                elif days_left <= 7:
                    alerts.append((eq_name, "soon", f"{to_type}: через {days_left} дн."))
            if int_hours > 0:
                last_motohours = get_last_usage(eq_name, 'motohours')
                if last_motohours:
                    current_hours = get_last_usage(eq_name, 'motohours')
                    next_hours = last_motohours + int_hours
                    hours_left = next_hours - current_hours
                    if hours_left <= 0:
                        alerts.append((eq_name, "overdue", f"{to_type}: просрочено по моточасам на {-hours_left} ч."))
                    elif hours_left <= 50:
                        alerts.append((eq_name, "soon", f"{to_type}: через {hours_left} моточасов"))
    return alerts

def get_to_intervals(equipment_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment_to_intervals WHERE equipment_name=? ORDER BY to_type", (equipment_name,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_to_interval(equipment_name, to_type, interval_days, interval_hours, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO equipment_to_intervals (equipment_name, to_type, interval_days, interval_hours, created_by, created_at) VALUES (?,?,?,?,?,?)",
              (equipment_name, to_type, interval_days, interval_hours, user, now_local()))
    conn.commit()
    conn.close()

def delete_to_interval(interval_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM equipment_to_intervals WHERE id=?", (interval_id,))
    conn.commit()
    conn.close()
# ============================================================
# 4. ПОЛЬЗОВАТЕЛИ
# ============================================================
def add_user(username, code, full_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, full_name, role, status, created_at) VALUES (?,?,?,?,?,?)",
                  (username, code, full_name, "employee", "pending", now_local()))
        conn.commit()
        conn.close()
        return True, "Пользователь зарегистрирован! Ожидайте одобрения администратора."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Пользователь с таким логином уже существует!"

def get_user_by_code(code):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE password=?", (code,))
    res = c.fetchone()
    conn.close()
    return res

def get_user(username, password):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    res = c.fetchone()
    conn.close()
    return res

def get_all_users():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, role, status, created_at FROM users ORDER BY created_at DESC")
    res = c.fetchall()
    conn.close()
    return res

def update_user_status(user_id, status):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=? AND role != 'admin'", (user_id,))
    conn.commit()
    conn.close()

def get_pending_users():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, created_at FROM users WHERE status='pending'")
    res = c.fetchall()
    conn.close()
    return res

def get_user_full_name(username):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT full_name FROM users WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    if res and res[0]:
        return res[0]
    return username

# ============================================================
# ФУНКЦИИ ДЛЯ ТО, МОТОЧАСОВ, КОМПЛЕКТОВ
# ============================================================
def get_equipment_assignments(username=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if username:
        c.execute("SELECT equipment_name FROM equipment_assignments WHERE username=?", (username,))
    else:
        c.execute("SELECT equipment_name, username FROM equipment_assignments")
    res = c.fetchall()
    conn.close()
    return res

def assign_equipment(equipment_name, username):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment_assignments (equipment_name, username, assigned_date) VALUES (?,?,?)",
                  (equipment_name, username, now_local()))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def remove_assignment(assignment_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM equipment_assignments WHERE id=?", (assignment_id,))
    conn.commit()
    conn.close()

def add_equipment_usage(equipment_name, value, usage_type, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO equipment_usage (equipment_name, record_date, value, usage_type, created_by, created_at) VALUES (?,?,?,?,?,?)",
              (equipment_name, now_local(), value, usage_type, user, now_local()))
    conn.commit()
    conn.close()

def get_equipment_usage(equipment_name=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if equipment_name:
        c.execute("SELECT * FROM equipment_usage WHERE equipment_name=? ORDER BY record_date DESC", (equipment_name,))
    else:
        c.execute("SELECT * FROM equipment_usage ORDER BY record_date DESC")
    res = c.fetchall()
    conn.close()
    return res

def get_last_usage(equipment_name, usage_type='motohours'):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT value FROM equipment_usage WHERE equipment_name=? AND usage_type=? ORDER BY record_date DESC LIMIT 1",
              (equipment_name, usage_type))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def delete_usage(usage_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM equipment_usage WHERE id=?", (usage_id,))
    conn.commit()
    conn.close()

def create_service_kit(kit_name, equipment_name, description, items, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO service_kits (kit_name, equipment_name, description, created_by, created_at) VALUES (?,?,?,?,?)",
              (kit_name, equipment_name, description, user, now_local()))
    kit_id = c.lastrowid
    for item_id, qty in items:
        c.execute("INSERT INTO service_kit_items (kit_id, item_id, quantity) VALUES (?,?,?)", (kit_id, item_id, qty))
    conn.commit()
    conn.close()
    return kit_id

def get_service_kits(equipment_name=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if equipment_name:
        c.execute("SELECT * FROM service_kits WHERE equipment_name=?", (equipment_name,))
    else:
        c.execute("SELECT * FROM service_kits")
    kits = c.fetchall()
    result = []
    for kit in kits:
        c.execute("SELECT item_id, quantity FROM service_kit_items WHERE kit_id=?", (kit[0],))
        items = c.fetchall()
        result.append((kit, items))
    conn.close()
    return result

def delete_service_kit(kit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM service_kit_items WHERE kit_id=?", (kit_id,))
    c.execute("DELETE FROM service_kits WHERE id=?", (kit_id,))
    conn.commit()
    conn.close()

def get_maintenance(equipment_name=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if equipment_name:
        c.execute("SELECT * FROM maintenance WHERE equipment_name=? ORDER BY maintenance_date DESC", (equipment_name,))
    else:
        c.execute("SELECT * FROM maintenance ORDER BY maintenance_date DESC")
    res = c.fetchall()
    conn.close()
    return res

def add_maintenance(equipment_name, maintenance_date, next_date, description, maint_type, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO maintenance (equipment_name, maintenance_date, next_maintenance_date, description, maintenance_type, created_by, created_at) VALUES (?,?,?,?,?,?,?)",
              (equipment_name, maintenance_date, next_date, description, maint_type, user, now_local()))
    conn.commit()
    conn.close()

def delete_maintenance(maint_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM maintenance WHERE id=?", (maint_id,))
    conn.commit()
    conn.close()

def get_last_maintenance(equipment_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT maintenance_date, next_maintenance_date FROM maintenance WHERE equipment_name=? ORDER BY maintenance_date DESC LIMIT 1", (equipment_name,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)

def get_to_status():
    equipment_list = get_equipment()
    alerts = []
    today = datetime.now().date()
    for eq in equipment_list:
        eq_name = eq[1]
        service_days = eq[4] if len(eq) > 4 else 0
        service_hours = eq[5] if len(eq) > 5 else 0
        last_date, next_date = get_last_maintenance(eq_name)
        last_motohours = get_last_usage(eq_name, 'motohours')
        status = "ok"
        message = ""
        if next_date:
            next_dt = datetime.strptime(next_date[:10], "%Y-%m-%d").date()
            days_left = (next_dt - today).days
            if days_left < 0:
                status = "overdue"
                message = f"Просрочено ТО на {-days_left} дн."
            elif days_left <= 7:
                status = "soon"
                message = f"ТО через {days_left} дн."
        if service_hours > 0 and last_motohours > 0:
            next_hours = last_motohours + service_hours
            hours_left = next_hours - get_last_usage(eq_name, 'motohours')
            if hours_left <= 0:
                status = "overdue" if status != "overdue" else status
                message += f" | Просрочено по моточасам на {-hours_left} ч."
            elif hours_left <= 50:
                if status != "overdue":
                    status = "soon"
                message += f" | ТО через {hours_left} моточасов"
        if status != "ok":
            alerts.append((eq_name, status, message))
    return alerts

# ============================================================
# 5. УВЕДОМЛЕНИЯ И СПИСОК ПОКУПОК
# ============================================================
def get_notifications():
    notifications = []
    current_role = st.session_state.user.get("role", "employee") if st.session_state.user else "employee"
    if current_role == "admin":
        for req in get_requests(status='pending'):
            r = unpack_request(req)
            nid = f"pending_{r['id']}"
            if nid not in st.session_state.dismissed_notifications:
                photo_path = r.get('photo', '')
                notifications.append({
                    'id': nid, 'type': 'request', 'status': 'Новая заявка', 'status_color': '🔵',
                    'icon': '📝', 'title': r['name'], 'description': r.get('description', ''),
                    'text': f'От: {r["user"]} | {r["quantity"]} {r["unit"]}', 'date': r['date'],
                    'request_id': r['id'], 'user': r['user'],
                    'photo': photo_path if photo_path and os.path.exists(photo_path) else None,
                    'actions': ['approve', 'reject', 'work'], 'is_read': r.get('seen', 0) == 1
                })
        for req in get_requests(status='returned'):
            r = unpack_request(req)
            nid = f"returned_{r['id']}"
            if nid not in st.session_state.dismissed_notifications:
                photo_path = r.get('photo', '')
                notifications.append({
                    'id': nid, 'type': 'returned', 'status': 'Возврат', 'status_color': '🟣',
                    'icon': '🔄', 'title': r['name'], 'description': r.get('description', ''),
                    'text': f'От: {r["user"]} | Причина: {r["admin_comment"][:50] if r["admin_comment"] else "Не указана"}',
                    'date': r['date'], 'request_id': r['id'], 'user': r['user'],
                    'photo': photo_path if photo_path and os.path.exists(photo_path) else None,
                    'actions': ['review'], 'is_read': r.get('seen', 0) == 1
                })
        for item in get_low_stock():
            nid = f"low_{item[0]}"
            if nid not in st.session_state.dismissed_notifications:
                if item[6] == 0:
                    status = "🚨 КРИТИЧНО! Нет в наличии"
                    status_color = "🔴"
                elif item[6] <= item[7] / 2:
                    status = "⚠️ Очень мало!"
                    status_color = "🟠"
                else:
                    status = "⚠️ Заканчивается"
                    status_color = "🟡"
                photos = get_item_photos(item[0])
                photo_path = None
                if photos:
                    main_photo = next((p for p in photos if p[2] == 1), photos[0])
                    if os.path.exists(main_photo[1]):
                        photo_path = main_photo[1]
                notifications.append({
                    'id': nid, 'type': 'low_stock', 'status': status, 'status_color': status_color,
                    'icon': '⚠️', 'title': item[1],
                    'description': f'Осталось {item[6]} {item[5]} из {item[7]} (порог)',
                    'text': f'Осталось {item[6]} {item[5]} (порог: {item[7]}) | 📍 {item[2]}',
                    'date': item[4], 'item_id': item[0], 'photo': photo_path,
                    'actions': ['restock'], 'is_read': False
                })
    else:
        user_name = st.session_state.user.get("username", "")
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            nid = f"{r['status']}_{r['id']}"
            if nid not in st.session_state.dismissed_notifications:
                status_map = {
                    'pending': ('⏳', 'На рассмотрении', '🟡'),
                    'in_work': ('🔧', 'В работе', '🔵'),
                    'approved': ('✅', 'Выполнено', '🟢'),
                    'rejected': ('❌', 'Отклонено', '🔴'),
                    'suggested': ('💡', 'Предложен товар', '🟣'),
                    'returned': ('🔄', 'Возвращено', '🟠')
                }
                icon, status_text, color = status_map.get(r['status'], ('📋', r['status'], '⚪'))
                photo_path = r.get('photo', '')
                extra_text = ""
                if r['status'] == 'suggested' and r['suggested_item_id']:
                    extra_text = " | 💡 Есть предложение со склада!"
                notifications.append({
                    'id': nid, 'type': 'request', 'status': status_text, 'status_color': color,
                    'icon': icon, 'title': r['name'], 'description': r.get('description', ''),
                    'text': f'Статус: {status_text}{extra_text}', 'date': r['date'],
                    'request_id': r['id'],
                    'photo': photo_path if photo_path and os.path.exists(photo_path) else None,
                    'actions': ['view'], 'is_read': r.get('seen', 0) == 1
                })
    return sorted(notifications, key=lambda x: x['date'], reverse=True)

def get_shopping_list():
    shopping = []
    for req in get_requests(status='in_work'):
        r = unpack_request(req)
        shopping.append({'type': 'in_work', 'icon': '🔧', 'name': r['name'],
            'qty': float(r['quantity'] or 0), 'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    for req in get_requests(status='pending'):
        r = unpack_request(req)
        shopping.append({'type': 'pending', 'icon': '📝', 'name': r['name'],
            'qty': float(r['quantity'] or 0), 'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    for item in get_low_stock():
        shopping.append({'type': 'low_stock', 'icon': '⚠️', 'name': item[1],
            'qty': float(item[6] or 0), 'unit': item[5], 'room': item[3], 'id': item[0]})
    for req in get_requests(status='approved'):
        r = unpack_request(req)
        shopping.append({'type': 'approved', 'icon': '✅', 'name': r['name'],
            'qty': float(r['quantity'] or 0), 'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    return shopping

def get_unread_counts():
    notifs = get_notifications()
    unread_requests = len([n for n in notifs if n.get('type') in ['request', 'returned'] and not n.get('is_read', False)])
    unread_low_stock = len([n for n in notifs if n.get('type') == 'low_stock' and not n.get('is_read', False)])
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM consumption WHERE date > datetime('now', '-7 days')")
    new_consumptions = c.fetchone()[0]
    conn.close()
    return {'unread_requests': unread_requests, 'unread_low_stock': unread_low_stock, 'unread_consumptions': new_consumptions}

# ============================================================
# 6. ВХОД В СИСТЕМУ
# ============================================================
def login_page():
    st.markdown("<h1 style='text-align:center;'>📦 Управление складом</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Вход по коду", "📝 Регистрация"])
    with tab1:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            access_code = st.text_input("Введите 4-значный код доступа", type="password", placeholder="Например: 1234", max_chars=4)
            if st.button("🔓 Войти", use_container_width=True):
                if access_code and len(access_code) == 4:
                    user = get_user_by_code(access_code)
                    if user:
                        user_id, user_username, user_full_name, user_role, user_status = user[0], user[1], user[2], user[3], user[4]
                        if user_status == "blocked":
                            st.error("❌ Ваш аккаунт заблокирован.")
                        elif user_status == "pending":
                            st.warning("⏳ Ожидайте одобрения.")
                        else:
                            if user_username == "admin":
                                user_role = "admin"
                            st.session_state.user = {"id": user_id, "username": user_username, "full_name": user_full_name, "role": user_role, "status": user_status}
                            st.rerun()
                    else:
                        st.error("❌ Неверный код!")
                else:
                    st.warning("⚠️ Введите 4-значный код")
    with tab2:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("### 📝 Регистрация нового сотрудника")
            with st.form("register_form"):
                reg_username = st.text_input("Придумайте логин*", placeholder="Например: ivanov")
                reg_full_name = st.text_input("Ваше полное имя*", placeholder="Иванов Иван")
                reg_code = st.text_input("Придумайте 4-значный код доступа*", type="password", placeholder="1234", max_chars=4)
                reg_code_confirm = st.text_input("Подтвердите код*", type="password", placeholder="1234", max_chars=4)
                if st.form_submit_button("📝 Зарегистрироваться"):
                    if not reg_username or not reg_full_name or not reg_code:
                        st.error("❌ Заполните все поля!")
                    elif reg_code != reg_code_confirm:
                        st.error("❌ Коды не совпадают!")
                    elif len(reg_code) != 4 or not reg_code.isdigit():
                        st.error("❌ Код должен быть из 4 цифр!")
                    else:
                        success, msg = add_user(reg_username, reg_code, reg_full_name)
                        if success:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")

if st.session_state.user is None:
    login_page()
    st.stop()

user = st.session_state.user
role = user.get("role", "employee")
user_name = user.get("username", "Пользователь")
user_full_name = user.get("full_name", "")
if user_name == "admin" and role != "admin":
    role = "admin"
    user["role"] = "admin"
    st.session_state.user = user

# ============================================================
# 7. БОКОВАЯ ПАНЕЛЬ
# ============================================================
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    if user_full_name:
        st.caption(f"Имя: {user_full_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    if user.get('status') == "blocked":
        st.error("🚫 Аккаунт заблокирован")
    notifs = get_notifications()
    if notifs:
        pending_count = len([n for n in notifs if n.get('icon') == '📝'])
        low_stock_count = len([n for n in notifs if n.get('icon') == '⚠️'])
        returned_count = len([n for n in notifs if n.get('icon') == '🔄'])
        button_text = f"🔔 Уведомлений: {len(notifs)}"
        if pending_count > 0: button_text += f" 📝{pending_count}"
        if low_stock_count > 0 and role == "admin": button_text += f" ⚠️{low_stock_count}"
        if returned_count > 0 and role == "admin": button_text += f" 🔄{returned_count}"
        if st.button(button_text, use_container_width=True):
            st.session_state.active_tab = 0
            st.rerun()
    else:
        if st.button("✅ Нет уведомлений", use_container_width=True):
            pass
    # уведомления о ТО
    to_alerts = get_to_status()
    if to_alerts:
        st.divider()
        st.markdown("### 🔧 ТО")
        for eq_name, status, msg in to_alerts:
            if status == "overdue":
                st.error(f"🔴 {eq_name}: {msg}")
            else:
                st.warning(f"🟡 {eq_name}: {msg}")
    if role == "admin":
        shopping = get_shopping_list()
        if shopping:
            low_stock_shopping = len([s for s in shopping if s.get('type') == 'low_stock'])
            pending_shopping = len([s for s in shopping if s.get('type') == 'pending'])
            in_work_shopping = len([s for s in shopping if s.get('type') == 'in_work'])
            button_text = f"🛒 К покупке: {len(shopping)}"
            if low_stock_shopping > 0: button_text += f" ⚠️{low_stock_shopping}"
            if pending_shopping > 0: button_text += f" 📝{pending_shopping}"
            if in_work_shopping > 0: button_text += f" 🔧{in_work_shopping}"
            if st.button(button_text, use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    st.divider()
    if role == "admin":
        with st.form("quick_add", clear_on_submit=True):
            st.markdown("### ➕ Новый товар")
            name = st.text_input("Название*", key="quick_name")
            location = st.text_input("Место*", key="quick_location")
            rooms = get_room_names()
            room = st.selectbox("Помещение*", rooms if rooms else ["Нет помещений"], key="quick_room")
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Кол-во", min_value=0.0, value=1.0, key="quick_qty")
            with col2:
                unit = st.selectbox("Ед.", ["шт","л","кг","м","комплект"], key="quick_unit")
            st.markdown("---")
            st.markdown("📸 **Фото товара**")
            uploaded_photo = st.file_uploader("Выберите фото", type=["jpg","jpeg","png"], key="quick_photo")
            is_main = st.checkbox("⭐ Сделать главным", value=True, key="quick_main")
            if st.form_submit_button("💾 Сохранить", use_container_width=True):
                if not name:
                    st.error("❌ Введите название товара!")
                elif not location:
                    st.error("❌ Введите место хранения!")
                elif room == "Нет помещений":
                    st.error("❌ Выберите помещение!")
                else:
                    item_id = add_item(name, location, room, qty, unit)
                    if uploaded_photo:
                        ext = uploaded_photo.name.split('.')[-1]
                        photo_path = f"images/items/{item_id}_{now_local_file()}.{ext}"
                        with open(photo_path, "wb") as f:
                            f.write(uploaded_photo.getbuffer())
                        add_item_photo(item_id, photo_path, is_main)
                    st.success(f"✅ Товар '{name}' добавлен!")
                    st.rerun()

# ============================================================
# 8. ОСНОВНОЙ ИНТЕРФЕЙС
# ============================================================
greeting = f"Добро пожаловать, {user_name}!"
st.title(f"📦 {greeting}")
counts = get_unread_counts()

if role == "admin":
    request_label = "📝 Заявки"
    if counts['unread_requests'] > 0: request_label += f" 🔴{counts['unread_requests']}"
    low_stock_label = "📋 Товары"
    if counts['unread_low_stock'] > 0: low_stock_label += f" ⚠️{counts['unread_low_stock']}"
    consumption_label = "📤 Списания"
    if counts['unread_consumptions'] > 0: consumption_label += f" 🆕{counts['unread_consumptions']}"
    tabs = st.tabs([request_label, "🔧 ТО и ремонты", low_stock_label, consumption_label, "🛒 Покупки", "🚜 Парк", "👥 Пользователи", "⚙️ Управление", "📊 Отчёты"])
else:
    request_label = "📝 Заявки"
    if counts['unread_requests'] > 0: request_label += f" 🔴{counts['unread_requests']}"
    consumption_label = "📤 Списания"
    if counts['unread_consumptions'] > 0: consumption_label += f" 🆕{counts['unread_consumptions']}"
    tabs = st.tabs([request_label, "🔧 ТО и ремонты", "📋 Товары", consumption_label, "🛒 Покупки", "🚜 Парк", "⚙️ Управление"])

# ============================================================
# 8.1 ЗАЯВКИ
# ============================================================
with tabs[0]:
    st.markdown("## 📝 Заявки")
    current_user_role = st.session_state.user.get("role", "employee")
    current_username = st.session_state.user.get("username", "")
    if current_user_role != "admin":
        with st.form("new_request", clear_on_submit=True):
            st.subheader("➕ Новая заявка")
            name = st.text_input("Название*")
            c1, c2 = st.columns(2)
            with c1: qty = st.number_input("Кол-во", min_value=0.1, value=1.0)
            with c2: unit = st.selectbox("Ед.", ["шт","л","кг","м","комплект"])
            desc = st.text_area("Описание")
            photo = st.file_uploader("Фото", type=["jpg","jpeg","png"], key="request_photo")
            submitted = st.form_submit_button("📤 Отправить")
            if submitted and name:
                photo_path = ""
                if photo is not None:
                    if not os.path.exists("images"): os.makedirs("images")
                    ext = photo.name.split('.')[-1]
                    photo_path = f"images/req_{uuid.uuid4()}.{ext}"
                    with open(photo_path, "wb") as f: f.write(photo.getbuffer())
                add_request(name, qty, unit, desc, photo_path, current_username)
                st.markdown("""
                <div style="background: linear-gradient(135deg, #d1fae5, #a7f3d0); border: 2px solid #10b981; border-radius: 15px; padding: 25px; text-align: center; animation: fadeIn 0.5s ease; margin: 20px 0;">
                    <div style="font-size: 50px; margin-bottom: 15px;">✅</div>
                    <div style="font-size: 22px; font-weight: 700; color: #065f46; margin-bottom: 10px;">Заявка успешно отправлена!</div>
                    <div style="font-size: 16px; color: #047857;">📋 Следите за статусом в разделе «Мои заявки»</div>
                    <div style="margin-top: 15px; font-size: 14px; color: #059669;">⏳ Страница обновится через 6 секунд...</div>
                </div>
                <style>@keyframes fadeIn { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }</style>
                """, unsafe_allow_html=True)
                time.sleep(6)
                st.rerun()
        st.divider()
        st.subheader("📋 Мои заявки")
        my_requests = get_requests(user=current_username)
        if my_requests:
            for req in my_requests:
                r = unpack_request(req)
                status_text = {'pending':'⏳ На рассмотрении','in_work':'🔧 В работе','approved':'✅ Выполнено','rejected':'❌ Отклонено','suggested':'💡 Предложен товар','returned':'🔄 Возвращено'}
                with st.expander(f"{status_text.get(r['status'], r['status'])} | {r['name']} — {r['quantity']} {r['unit']}"):
                    col1, col2 = st.columns([2,1])
                    with col1:
                        if r['description']: st.write(f"📝 Описание: {r['description']}")
                        if r['admin_comment']: st.write(f"💬 Комментарий: {r['admin_comment']}")
                        st.caption(f"📅 {r['date']}")
                    with col2:
                        if r['photo'] and os.path.exists(r['photo']): st.image(r['photo'], width=200)
                        else: st.caption("📷 Нет фото")
                    if r['status'] == 'rejected':
                        st.divider()
                        if st.button("🗑️ Удалить заявку", key=f"del_req_emp_{r['id']}", use_container_width=True):
                            delete_request(r['id'])
                            st.success("🗑️ Заявка удалена!")
                            st.rerun()
                    if r['status'] == 'suggested' and r['suggested_item_id']:
                        st.divider()
                        st.markdown("**💡 Предложенный товар со склада:**")
                        conn = sqlite3.connect('storage.db')
                        c = conn.cursor()
                        c.execute("SELECT * FROM items WHERE id=?", (r['suggested_item_id'],))
                        item = c.fetchone()
                        conn.close()
                        if item:
                            col1, col2 = st.columns([2,1])
                            with col1: st.write(f"📦 {item[1]} — {item[6]} {item[5]} | {item[3]}")
                            with col2:
                                photos = get_item_photos(item[0])
                                if photos:
                                    main_photo = next((p for p in photos if p[2]==1), photos[0])
                                    if os.path.exists(main_photo[1]): st.image(main_photo[1], width=100)
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Подходит", key=f"ok_{r['id']}"): mark_request_seen(r['id']); st.rerun()
                        with col2:
                            if st.button("❌ Не подходит", key=f"no_{r['id']}"): st.session_state[f"ret_{r['id']}"] = True
                        if st.session_state.get(f"ret_{r['id']}"):
                            reason = st.text_area("Причина возврата", key=f"reason_{r['id']}")
                            if st.button("📤 Отправить на пересмотр", key=f"send_{r['id']}"):
                                return_request(r['id'], reason)
                                st.session_state[f"ret_{r['id']}"] = False
                                st.rerun()
        else:
            st.info("У вас нет заявок")
    else:
        statuses = {"⏳ Новые":"pending","🔧 В работе":"in_work","🔄 Возвраты":"returned","💡 Предложенные":"suggested","✅ Готовые":"approved","❌ Отклоненные":"rejected"}
        subtabs = st.tabs(list(statuses.keys()))
        for tab, (label, status) in zip(subtabs, statuses.items()):
            with tab:
                reqs = get_requests(status=status)
                if reqs:
                    for req in reqs:
                        r = unpack_request(req)
                        with st.expander(f"{r['name']} — {r['quantity']} {r['unit']} | от {r['user']} | {r['date'][:10]}"):
                            col1, col2 = st.columns([2,1])
                            with col1:
                                if r['description']: st.write(f"📝 Описание: {r['description']}")
                                if r['admin_comment']: st.write(f"💬 Комментарий: {r['admin_comment']}")
                                if r['suggested_item_id']: st.write(f"💡 Предложен товар ID: {r['suggested_item_id']}")
                            with col2:
                                if r['photo'] and os.path.exists(r['photo']): st.image(r['photo'], width=200)
                                else: st.caption("📷 Нет фото")
                            st.divider()
                            if status in ['pending','returned']:
                                c1,c2,c3 = st.columns(3)
                                with c1:
                                    if st.button("✅ Одобрить", key=f"app_{r['id']}"): update_request_status(r['id'],"approved"); st.rerun()
                                with c2:
                                    if st.button("💡 Со склада", key=f"sug_btn_{r['id']}"): st.session_state[f"sug_mode_{r['id']}"] = True
                                with c3:
                                    if st.button("❌ Отклонить", key=f"rej_btn_{r['id']}"): update_request_status(r['id'],"rejected"); st.rerun()
                                if st.session_state.get(f"sug_mode_{r['id']}"):
                                    sq = st.text_input("Поиск товара на складе", key=f"sq_{r['id']}")
                                    if sq:
                                        found = search_items(sq)
                                        if found:
                                            for item in found:
                                                col1,col2 = st.columns([2,1])
                                                with col1: st.write(f"📦 {item[1]} — {item[6]} {item[5]} | {item[3]}")
                                                with col2:
                                                    if st.button("📤 Предложить", key=f"sel_{r['id']}_{item[0]}"):
                                                        update_request_status(r['id'],"suggested",f"Предложен: {item[1]}",item[0])
                                                        st.session_state[f"sug_mode_{r['id']}"] = False
                                                        st.rerun()
                                    if st.button("❌ Закрыть", key=f"close_{r['id']}"): st.session_state[f"sug_mode_{r['id']}"] = False; st.rerun()
                            elif status == 'in_work':
                                c1,c2 = st.columns(2)
                                with c1:
                                    if st.button("✅ Выполнено", key=f"done_{r['id']}"): update_request_status(r['id'],"approved"); st.rerun()
                                with c2:
                                    if st.button("🗑️ Удалить", key=f"del_req_{r['id']}"): delete_request(r['id']); st.rerun()
                            elif status == 'approved':
                                col1,col2 = st.columns(2)
                                with col1:
                                    if st.button("📦 Создать товар", key=f"create_{r['id']}"): st.session_state[f"create_mode_{r['id']}"] = True
                                with col2:
                                    if st.button("🗑️ Удалить", key=f"del_approved_{r['id']}"): delete_request(r['id']); st.success("🗑️ Заявка удалена!"); st.rerun()
                                if st.session_state.get(f"create_mode_{r['id']}"):
                                    rooms = get_room_names()
                                    if rooms:
                                        room = st.selectbox("Помещение", rooms, key=f"cr_{r['id']}")
                                        loc = st.text_input("Место", key=f"cl_{r['id']}")
                                        c1,c2 = st.columns(2)
                                        with c1:
                                            if st.button("💾 Сохранить", key=f"cs_{r['id']}") and loc:
                                                item_id = add_item(r['name'], loc, room, r['quantity'], r['unit'])
                                                delete_request(r['id'])
                                                st.success(f"✅ Товар '{r['name']}' создан!")
                                                st.rerun()
                                        with c2:
                                            if st.button("❌ Отмена", key=f"cancel_create_{r['id']}"): st.session_state[f"create_mode_{r['id']}"] = False; st.rerun()
                            elif status == 'rejected':
                                col1,col2 = st.columns(2)
                                with col1:
                                    if st.button("🔄 Вернуть на рассмотрение", key=f"return_to_pending_{r['id']}"): update_request_status(r['id'],"pending",""); st.rerun()
                                with col2:
                                    if st.button("🗑️ Удалить", key=f"del_rejected_{r['id']}"): delete_request(r['id']); st.success("🗑️ Заявка удалена!"); st.rerun()
                            elif status == 'suggested':
                                if st.button("🗑️ Удалить", key=f"del_suggested_{r['id']}"): delete_request(r['id']); st.success("🗑️ Заявка удалена!"); st.rerun()
                else:
                    st.info(f"Нет заявок со статусом '{label}'")

# ============================================================
# 8.2 ТО И РЕМОНТЫ (ИНДЕКС 1)
# ============================================================
with tabs[1]:
    st.markdown("## 🔧 Техническое обслуживание и ремонты")
    equipment_list = get_equipment()
    if not equipment_list:
        st.info("🚜 Парк техники пуст. Добавьте технику в разделе «Парк».")
    else:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 План ТО", "📋 Журнал работ", "⏱️ Моточасы / Пробег", "📦 Комплекты ТО", "📊 Аналитика"])
        
        # ==================== ПЛАН ТО ====================
        with tab1:
            st.subheader("📅 План технического обслуживания")
            
            # --- НАСТРОЙКА ИНТЕРВАЛОВ (только админ) ---
            if role == "admin":
                st.divider()
                st.subheader("⚙️ Настройка интервалов ТО")
                selected_eq = st.selectbox("Выберите технику для настройки", [eq[1] for eq in equipment_list], key="to_interval_eq")
                existing_intervals = get_to_intervals(selected_eq)
                
                if existing_intervals:
                    st.write("**Существующие интервалы:**")
                    for interval in existing_intervals:
                        col1, col2, col3 = st.columns([2,2,1])
                        with col1: st.write(f"**{interval[2]}** — {interval[3]} дн. / {interval[4]} м/ч")
                        with col2: st.caption(f"Создал: {interval[5]}")
                        with col3:
                            if st.button("🗑️", key=f"del_to_int_{interval[0]}"):
                                delete_to_interval(interval[0])
                                st.success("Интервал удалён!")
                                st.rerun()
                
                with st.form("add_to_interval"):
                    st.write("**➕ Добавить тип ТО**")
                    to_type = st.text_input("Название (напр. ТО-1, ТО-2)", value="ТО-1")
                    col1, col2 = st.columns(2)
                    with col1: days = st.number_input("Интервал (дни)", min_value=0, value=0)
                    with col2: hours = st.number_input("Интервал (моточасы)", min_value=0, value=0)
                    if st.form_submit_button("💾 Сохранить интервал"):
                        if to_type:
                            add_to_interval(selected_eq, to_type, days, hours, user_name)
                            st.success("✅ Интервал добавлен!")
                            st.rerun()
            
            st.divider()
            
            # --- СВОДНАЯ ТАБЛИЦА ПЛАНА ТО ---
            st.subheader("Сводная таблица по всем видам ТО")
            plan_data = []
            today = datetime.now().date()
            for eq in equipment_list:
                eq_name = eq[1]
                intervals = get_to_intervals(eq_name)
                if not intervals:
                    plan_data.append({
                        "Техника": eq_name,
                        "Тип ТО": "—",
                        "Последнее ТО": "—",
                        "След. ТО (дата)": "—",
                        "Осталось дней": "—",
                        "След. ТО (мот.)": "—",
                        "Осталось часов": "—",
                        "Статус": "⚪ Нет данных"
                    })
                else:
                    for interval in intervals:
                        int_id, _, to_type, int_days, int_hours, created_by, _ = interval
                        conn = sqlite3.connect('storage.db')
                        c = conn.cursor()
                        c.execute("SELECT maintenance_date, next_maintenance_date FROM maintenance WHERE equipment_name=? AND to_type=? ORDER BY maintenance_date DESC LIMIT 1",
                                  (eq_name, to_type))
                        last_to = c.fetchone()
                        conn.close()
                        last_date = last_to[0] if last_to else None
                        next_date = last_to[1] if last_to and last_to[1] else None
                        if not next_date and last_date and int_days > 0:
                            last_dt = datetime.strptime(last_date[:10], "%Y-%m-%d").date()
                            next_date = (last_dt + timedelta(days=int_days)).strftime("%Y-%m-%d")
                        if next_date:
                            next_dt = datetime.strptime(next_date[:10], "%Y-%m-%d").date()
                            days_left = (next_dt - today).days
                            if days_left < 0:
                                day_status = "🔴"
                            elif days_left <= 7:
                                day_status = "🟡"
                            else:
                                day_status = "🟢"
                        else:
                            days_left = "—"
                            day_status = "⚪"
                        last_motohours = get_last_usage(eq_name, 'motohours')
                        if int_hours > 0 and last_motohours:
                            current_hours = get_last_usage(eq_name, 'motohours')
                            next_hours = last_motohours + int_hours
                            hours_left = next_hours - current_hours
                            if hours_left <= 0:
                                hour_status = "🔴"
                            elif hours_left <= 50:
                                hour_status = "🟡"
                            else:
                                hour_status = "🟢"
                        else:
                            hours_left = "—"
                            hour_status = "⚪"
                            next_hours = "—"
                        if "🔴" in [day_status, hour_status]:
                            overall = "🔴 Требует ТО"
                        elif "🟡" in [day_status, hour_status]:
                            overall = "🟡 Скоро"
                        elif "🟢" in [day_status, hour_status]:
                            overall = "🟢 ОК"
                        else:
                            overall = "⚪ Нет данных"
                        plan_data.append({
                            "Техника": eq_name,
                            "Тип ТО": to_type,
                            "Последнее ТО": last_date[:10] if last_date else "—",
                            "След. ТО (дата)": next_date[:10] if next_date else "—",
                            "Осталось дней": days_left,
                            "След. ТО (мот.)": f"{next_hours} м/ч" if int_hours > 0 else "—",
                            "Осталось часов": hours_left if isinstance(hours_left, (int, float)) else "—",
                            "Статус": overall
                        })
            df_plan = pd.DataFrame(plan_data)
            st.dataframe(df_plan, use_container_width=True, hide_index=True)
            
            buffer_plan = io.BytesIO()
            with pd.ExcelWriter(buffer_plan, engine='openpyxl') as writer:
                df_plan.to_excel(writer, sheet_name='План ТО', index=False)
            st.download_button(
                label="📥 Скачать план ТО (Excel)",
                data=buffer_plan.getvalue(),
                file_name=f"план_ТО_{now_local_file()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_plan_to"
            )
        
        # ==================== ЖУРНАЛ РАБОТ ====================
        with tab2:
            st.subheader("📋 Журнал проведённых работ")
            col1, col2 = st.columns([3, 1])
            with col1:
                filter_eq = st.selectbox("Фильтр по технике", ["Все"] + [eq[1] for eq in equipment_list], key="maint_filter")
            maint_records = get_maintenance() if filter_eq == "Все" else get_maintenance(filter_eq)
            if maint_records:
                df_journal = pd.DataFrame(maint_records, columns=[
                    "ID", "Техника", "Дата", "След. ТО", "Описание", "Тип", "Кто", "Создано"
                ])
                buffer_journal = io.BytesIO()
                with pd.ExcelWriter(buffer_journal, engine='openpyxl') as writer:
                    df_journal.to_excel(writer, sheet_name='Журнал ТО', index=False)
                st.download_button(
                    label="📥 Скачать журнал (Excel)",
                    data=buffer_journal.getvalue(),
                    file_name=f"журнал_ТО_{now_local_file()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_journal"
                )
                
                for rec in maint_records:
                    rec_id, eq_name, m_date, next_m_date, desc, m_type, created_by, created_at = rec
                    with st.expander(f"{'🔧' if m_type == 'ТО' else '🛠️'} {eq_name} — {m_date[:10]} | {desc[:50]}"):
                        st.write(f"**Тип:** {m_type}")
                        st.write(f"**Дата:** {m_date[:10]}")
                        st.write(f"**Следующее ТО:** {next_m_date[:10] if next_m_date else 'не указано'}")
                        st.write(f"**Описание:** {desc}")
                        st.caption(f"Запись: {created_by} | {created_at}")
                        if role == "admin":
                            if st.button("🗑️ Удалить", key=f"del_maint_{rec_id}"):
                                delete_maintenance(rec_id)
                                st.success("Удалено!")
                                st.rerun()
            else:
                st.info("Записей не найдено.")
            
            if role == "admin":
                st.divider()
                st.subheader("➕ Добавить запись")
                with st.form("add_maint"):
                    col1, col2 = st.columns(2)
                    with col1:
                        eq_name = st.selectbox("Техника*", [eq[1] for eq in equipment_list])
                        m_type = st.selectbox("Тип работ", ["ТО", "Ремонт"])
                        m_date = st.date_input("Дата проведения*", value=datetime.now().date())
                    with col2:
                        next_m_date = st.date_input("Дата следующего ТО (опционально)", value=None)
                        kit_option = st.checkbox("Использовать комплект ТО")
                    to_type = "ТО-1"
                    if m_type == "ТО":
                        intervals = get_to_intervals(eq_name)
                        if intervals:
                            to_options = [i[2] for i in intervals]
                            to_type = st.selectbox("Тип ТО", to_options)
                    desc = st.text_area("Описание работ*")
                    
                    if kit_option:
                        kits = get_service_kits(eq_name)
                        if kits:
                            kit_names = [f"{k[0][1]} (ID:{k[0][0]})" for k in kits]
                            selected_kit = st.selectbox("Выберите комплект", kit_names)
                            kit = kits[kit_names.index(selected_kit)]
                            st.write("**Состав комплекта:**")
                            for item_id, qty in kit[1]:
                                conn = sqlite3.connect('storage.db')
                                c = conn.cursor()
                                c.execute("SELECT name, quantity FROM items WHERE id=?", (item_id,))
                                item = c.fetchone()
                                conn.close()
                                if item:
                                    st.write(f"- {item[0]} x{qty} (на складе: {item[1]})")
                    
                    if st.form_submit_button("💾 Сохранить"):
                        if desc:
                            conn = sqlite3.connect('storage.db')
                            c = conn.cursor()
                            c.execute("INSERT INTO maintenance (equipment_name, maintenance_date, next_maintenance_date, description, maintenance_type, to_type, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)",
                                      (eq_name, m_date.strftime("%Y-%m-%d"),
                                       next_m_date.strftime("%Y-%m-%d") if next_m_date else "",
                                       desc, m_type, to_type, user_name, now_local()))
                            conn.commit()
                            conn.close()
                            if kit_option and kits:
                                for item_id, qty in kit[1]:
                                    conn = sqlite3.connect('storage.db')
                                    c = conn.cursor()
                                    c.execute("UPDATE items SET quantity = quantity - ? WHERE id=?", (qty, item_id))
                                    conn.commit()
                                    conn.close()
                            st.success("✅ Запись добавлена!")
                            st.rerun()
                        else:
                            st.error("❌ Заполните описание!")
        
        # ==================== МОТОЧАСЫ / ПРОБЕГ ====================
        with tab3:
            st.subheader("⏱️ Учёт моточасов и пробега")
            with st.form("add_usage"):
                col1, col2 = st.columns(2)
                with col1:
                    eq_name = st.selectbox("Техника", [eq[1] for eq in equipment_list])
                    usage_type = st.selectbox("Тип", ["motohours", "mileage"])
                with col2:
                    value = st.number_input("Текущее значение", min_value=0.0, step=1.0)
                if st.form_submit_button("📝 Записать"):
                    add_equipment_usage(eq_name, value, usage_type, user_name)
                    st.success("✅ Показания сохранены!")
                    alerts = get_to_status()
                    for alert_eq, status, msg in alerts:
                        if alert_eq == eq_name and status != "ok":
                            st.warning(f"⚠️ {msg}")
                    st.rerun()
            
            st.divider()
            usage_records = get_equipment_usage()
            if usage_records:
                df_usage = pd.DataFrame(usage_records, columns=["ID","Техника","Дата","Значение","Тип","Кто","Создано"])
                buffer_usage = io.BytesIO()
                with pd.ExcelWriter(buffer_usage, engine='openpyxl') as writer:
                    df_usage[["Техника","Дата","Значение","Тип","Кто"]].to_excel(writer, sheet_name='Моточасы', index=False)
                st.download_button(
                    label="📥 Скачать данные (Excel)",
                    data=buffer_usage.getvalue(),
                    file_name=f"моточасы_{now_local_file()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_usage"
                )
                st.dataframe(df_usage[["Техника","Дата","Значение","Тип","Кто"]], use_container_width=True)
                if role == "admin":
                    st.subheader("🗑️ Удаление записей")
                    del_id = st.number_input("ID записи для удаления", min_value=1, step=1)
                    if st.button("Удалить"):
                        delete_usage(del_id)
                        st.success("Удалено!")
                        st.rerun()
            else:
                st.info("Записей о наработке нет.")
        
        # ==================== КОМПЛЕКТЫ ТО ====================
        with tab4:
            st.subheader("📦 Комплекты для ТО")
            if role == "admin":
                with st.form("create_kit"):
                    st.write("**Создать новый комплект**")
                    kit_name = st.text_input("Название комплекта*")
                    eq_for_kit = st.selectbox("Для техники", [eq[1] for eq in equipment_list])
                    kit_desc = st.text_area("Описание")
                    all_items = get_all_items()
                    item_options = {f"{it[1]} (ост. {it[6]})": it[0] for it in all_items}
                    selected_items = st.multiselect("Выберите товары", list(item_options.keys()))
                    quantities = {}
                    for item_str in selected_items:
                        qty = st.number_input(f"Количество для '{item_str}'", min_value=0.1, value=1.0, step=1.0)
                        quantities[item_str] = qty
                    if st.form_submit_button("💾 Создать комплект"):
                        if kit_name and selected_items:
                            items = [(item_options[it], quantities[it]) for it in selected_items]
                            create_service_kit(kit_name, eq_for_kit, kit_desc, items, user_name)
                            st.success("✅ Комплект создан!")
                            st.rerun()
                        else:
                            st.error("❌ Укажите название и выберите товары!")
            
            kits = get_service_kits()
            if kits:
                for kit, items in kits:
                    with st.expander(f"📦 {kit[1]} (ID:{kit[0]}) — для {kit[2]}"):
                        st.write(f"**Описание:** {kit[3]}")
                        st.write("**Состав:**")
                        for item_id, qty in items:
                            conn = sqlite3.connect('storage.db')
                            c = conn.cursor()
                            c.execute("SELECT name FROM items WHERE id=?", (item_id,))
                            item = c.fetchone()
                            conn.close()
                            if item:
                                st.write(f"- {item[0]} x{qty}")
                        if role == "admin":
                            if st.button("🗑️ Удалить комплект", key=f"del_kit_{kit[0]}"):
                                delete_service_kit(kit[0])
                                st.success("Комплект удалён!")
                                st.rerun()
            else:
                st.info("Нет созданных комплектов.")
        
        # ==================== АНАЛИТИКА ====================
        with tab5:
            st.subheader("📊 Аналитика обслуживания")
            maint_all = get_maintenance()
            if maint_all:
                df_maint = pd.DataFrame(maint_all, columns=["ID","Техника","Дата","След.ТО","Описание","Тип","Кто","Создано"])
                df_maint['Дата'] = pd.to_datetime(df_maint['Дата'])
                df_maint['Месяц'] = df_maint['Дата'].dt.to_period('M').astype(str)
                repairs = df_maint[df_maint['Тип'] == 'Ремонт']
                if not repairs.empty:
                    monthly = repairs.groupby('Месяц').size()
                    st.bar_chart(monthly)
                else:
                    st.info("Нет данных о ремонтах.")

# ============================================================
# 8.3 ТОВАРЫ (ИНДЕКС 2)
# ============================================================
with tabs[2]:
    st.markdown("## 📋 Все товары")
    # ... скопируйте сюда весь код раздела товаров из вашего старого блока 8.2 ТОВАРЫ ...

# ============================================================
# 8.4 СПИСАНИЯ (ИНДЕКС 3)
# ============================================================
with tabs[3]:
    st.markdown("## 📤 Списания")
    # ... скопируйте сюда весь код раздела списаний ...

# ============================================================
# 8.5 ПОКУПКИ (ИНДЕКС 4)
# ============================================================
with tabs[4]:
    st.markdown("## 🛒 Список покупок")
    # ... скопируйте сюда весь код раздела покупок ...

# ============================================================
# 8.6 ПАРК ТЕХНИКИ (ИНДЕКС 5)
# ============================================================
with tabs[5]:
    st.markdown("## 🚜 Парк техники")
    # ... скопируйте сюда весь код раздела парка ...

# ============================================================
# 8.7 ПОЛЬЗОВАТЕЛИ (ИНДЕКС 6 – только админ)
# ============================================================
if role == "admin":
    with tabs[6]:
        st.markdown("## 👥 Управление пользователями")
        # ... скопируйте сюда весь код раздела пользователей ...

# ============================================================
# 8.8 УПРАВЛЕНИЕ (ИНДЕКС 7 – админ, ИНДЕКС 6 – сотрудник)
# ============================================================
if role == "admin":
    with tabs[7]:
        st.markdown("## ⚙️ Управление")
        # ... скопируйте сюда весь код раздела управления (помещения, оформление, бэкапы) ...
else:
    with tabs[6]:
        st.markdown("## ⚙️ Управление")
        st.info("ℹ️ Для управления настройками обратитесь к администратору.")

# ============================================================
# 8.9 ОТЧЁТЫ (ИНДЕКС 8 – только админ)
# ============================================================
if role == "admin":
    with tabs[8]:
        st.markdown("## 📊 Отчёты и аналитика")
        conn = sqlite3.connect('storage.db')
        query = """
        SELECT c.date, c.item_id, i.name, c.quantity, c.unit, c.user, c.equipment_name
        FROM consumption c
        LEFT JOIN items i ON c.item_id = i.id
        ORDER BY c.date
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        if df.empty:
            st.info("Нет данных о списаниях для построения отчётов.")
        else:
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.to_period('M').astype(str)
            df['year'] = df['date'].dt.year
            st.subheader("📅 Расход товара по месяцам")
            items_list = sorted(df['name'].dropna().unique())
            selected_item = st.selectbox("Выберите товар", items_list)
            item_data = df[df['name'] == selected_item]
            if not item_data.empty:
                monthly = item_data.groupby('month')['quantity'].sum().reset_index()
                monthly.columns = ['Месяц', 'Количество']
                st.bar_chart(monthly.set_index('Месяц'))
            else:
                st.info("Нет данных по выбранному товару")
            st.divider()
            st.subheader("🏆 ТОП-10 самых расходуемых товаров")
            top_items = df.groupby('name')['quantity'].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top_items)
            st.divider()
            st.subheader("👥 Списания по сотрудникам")
            user_stats = df.groupby('user')['quantity'].sum().sort_values(ascending=False)
            col1, col2 = st.columns([2, 1])
            with col1: st.bar_chart(user_stats)
            with col2: st.dataframe(user_stats.reset_index().rename(columns={'user':'Сотрудник','quantity':'Единиц'}))
            st.divider()
            st.subheader("📥 Экспорт данных")
            export_df = df.groupby(['name','user','month']).agg(
                Количество=('quantity','sum'),
                Единица=('unit','first')
            ).reset_index()
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, sheet_name='Сводка', index=False)
                df[['date','name','quantity','unit','user','equipment_name']].to_excel(
                    writer, sheet_name='Все записи', index=False
                )
            st.download_button(
                label="📥 Скачать полный отчёт (Excel)",
                data=buffer.getvalue(),
                file_name=f"отчёт_склад_{now_local_file()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    with tabs[5]:
        st.markdown("## ⚙️ Управление")
        st.info("ℹ️ Для управления настройками обратитесь к администратору.")
