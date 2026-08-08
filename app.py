import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from PIL import Image
import shutil

# ============================================================
# 1. НАСТРОЙКА И ПЕРЕМЕННЫЕ
# ============================================================

# Настройка часового пояса (Москва, UTC+3)
UTC_OFFSET = 3

def now_local():
    """Возвращает текущую дату и время по московскому времени"""
    return (datetime.utcnow() + timedelta(hours=UTC_OFFSET)).strftime("%Y-%m-%d %H:%M")

def now_local_file():
    """Возвращает дату/время для имени файла (без пробелов и двоеточий)"""
    return now_local().replace(" ", "_").replace(":", "")

# Создаём папки
for folder in ["images", "images/items", "images/take", "backups"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Инициализация сессии
if "user" not in st.session_state:
    st.session_state.user = None
if "dismissed_notifications" not in st.session_state:
    st.session_state.dismissed_notifications = []

st.set_page_config(page_title="Мой Склад", page_icon="📦", layout="wide")

# ============================================================
# 🎨 КРАСИВЫЙ ДИЗАЙН (CSS)
# ============================================================

st.markdown("""
<style>
/* ========== ЗАГОЛОВКИ ========== */
h1 {
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

h2 {
    color: #1e293b;
    font-weight: 700;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}

h3 {
    color: #334155;
    font-weight: 600;
}

/* ========== КАРТОЧКИ И КОНТЕЙНЕРЫ ========== */
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
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}

/* ========== МЕТРИКИ ========== */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8fafc, #ffffff);
    border-radius: 12px;
    padding: 15px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    transition: all 0.3s ease;
}

[data-testid="stMetric"]:hover {
    box-shadow: 0 6px 12px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}

[data-testid="stMetric"] label {
    font-weight: 600;
    color: #64748b;
}

[data-testid="stMetric"] div {
    font-weight: 700;
    color: #1e293b;
}

/* ========== КНОПКИ ========== */
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
    box-shadow: 0 6px 15px rgba(0,0,0,0.15);
}

.stButton > button:active {
    transform: translateY(0);
}

/* Основная кнопка */
.stButton > button:not([kind="secondary"]):not([kind="tertiary"]) {
    background: linear-gradient(135deg, #2563eb, #3b82f6);
    color: white;
}

/* ========== ФОРМЫ ВВОДА ========== */
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
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
    background: white;
}

/* ========== EXPANDER (СВОРАЧИВАЕМЫЕ БЛОКИ) ========== */
.streamlit-expanderHeader {
    background: linear-gradient(135deg, #f8fafc, #ffffff);
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    font-weight: 600;
    color: #1e293b;
    padding: 12px 15px;
    transition: all 0.3s ease;
}

.streamlit-expanderHeader:hover {
    background: linear-gradient(135deg, #eff6ff, #f8fafc);
    border-color: #2563eb;
}

[data-testid="stExpander"] {
    border-radius: 10px;
    margin: 8px 0;
    border: 1px solid #e2e8f0;
    overflow: hidden;
}

/* ========== БОКОВАЯ ПАНЕЛЬ ========== */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e293b, #334155);
    padding: 20px;
}

[data-testid="stSidebar"] * {
    color: #f1f5f9;
}

[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h2 {
    color: #f8fafc;
}

[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: #f1f5f9;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.2);
}

/* ========== ТАБЫ (ВКЛАДКИ) ========== */
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
    background: linear-gradient(135deg, #2563eb, #3b82f6);
    color: white;
}

/* ========== УВЕДОМЛЕНИЯ ========== */
.stAlert {
    border-radius: 10px;
    border: none;
    font-weight: 500;
}

.stSuccess {
    background: linear-gradient(135deg, #d1fae5, #a7f3d0);
    color: #065f46;
}

.stWarning {
    background: linear-gradient(135deg, #fef3c7, #fde68a);
    color: #92400e;
}

.stError {
    background: linear-gradient(135deg, #fee2e2, #fecaca);
    color: #991b1b;
}

.stInfo {
    background: linear-gradient(135deg, #dbeafe, #bfdbfe);
    color: #1e40af;
}

/* ========== ЗАГРУЗКА ФАЙЛОВ ========== */
[data-testid="stFileUploader"] {
    border-radius: 10px;
    border: 2px dashed #e2e8f0;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
}

[data-testid="stFileUploader"]:hover {
    border-color: #2563eb;
    background: #f8fafc;
}

/* ========== АНИМАЦИИ ========== */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.stContainer, .stExpander {
    animation: fadeIn 0.5s ease;
}

/* ========== КАСТОМНЫЙ СКРОЛЛБАР ========== */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: #94a3b8;
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: #64748b;
}

/* ========== СКРЫТЬ ФУТЕР ========== */
footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. БАЗА ДАННЫХ
# ============================================================

def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        name TEXT,
        location TEXT,
        room TEXT,
        date_added TEXT,
        quantity REAL,
        unit TEXT,
        threshold INTEGER DEFAULT 1,
        photos_count INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        number TEXT,
        date_added TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        date_added TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        quantity REAL,
        unit TEXT,
        description TEXT,
        photo TEXT,
        user TEXT,
        date TEXT,
        status TEXT DEFAULT 'pending',
        seen INTEGER DEFAULT 0,
        admin_comment TEXT,
        suggested_item_id TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS consumption (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT,
        quantity REAL,
        unit TEXT,
        object_name TEXT,
        user TEXT,
        date TEXT,
        equipment_name TEXT,
        equipment_number TEXT,
        photo TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS item_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT,
        photo_path TEXT,
        date_added TEXT,
        is_main INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'employee',
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        approved_by TEXT
    )''')
    
    # Добавляем админа по умолчанию (пароль 1209)
    c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO users (username, password, full_name, role, status, created_at) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  ("admin", "1209", "Администратор", "admin", "active", now_local()))
    else:
        c.execute("UPDATE users SET role='admin', status='active' WHERE username='admin'")
    
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
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result

def add_room(name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?, ?)", 
                  (name, now_local()))
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
    result = c.fetchall()
    conn.close()
    return result

def add_equipment(name, number=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment (name, number, date_added) VALUES (?, ?, ?)",
                  (name, number, now_local()))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def search_equipment(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    q = f"%{query}%"
    c.execute("SELECT * FROM equipment WHERE name LIKE ? OR number LIKE ? ORDER BY name", (q, q))
    result = c.fetchall()
    conn.close()
    return result

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items ORDER BY date_added DESC")
    result = c.fetchall()
    conn.close()
    return result

def search_items(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    q = f"%{query}%"
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items WHERE name LIKE ? OR location LIKE ? OR room LIKE ?", (q, q, q))
    result = c.fetchall()
    conn.close()
    return result

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
    result = c.fetchall()
    conn.close()
    return result

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
    result = c.fetchall()
    conn.close()
    return result

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
    """Списание товара. Сохраняет username (логин) пользователя."""
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
    result = c.fetchall()
    conn.close()
    return result

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
    result = c.fetchall()
    conn.close()
    return result

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
# 4. ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# ============================================================

def add_user(username, code, full_name):
    """Добавить нового пользователя. username - логин, code - 4-значный код доступа, full_name - полное имя"""
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
    """Получить пользователя по 4-значному коду"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE password=?", (code,))
    result = c.fetchone()
    conn.close()
    return result

def get_user(username, password):
    """Получить пользователя по логину и паролю"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    result = c.fetchone()
    conn.close()
    return result

def get_all_users():
    """Получить всех пользователей"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, role, status, created_at FROM users ORDER BY created_at DESC")
    result = c.fetchall()
    conn.close()
    return result

def update_user_status(user_id, status):
    """Обновить статус пользователя"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Удалить пользователя"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=? AND role != 'admin'", (user_id,))
    conn.commit()
    conn.close()

def get_pending_users():
    """Получить пользователей, ожидающих подтверждения"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, created_at FROM users WHERE status='pending'")
    result = c.fetchall()
    conn.close()
    return result

def get_user_full_name(username):
    """Получить полное имя пользователя по логину"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT full_name FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0]:
        return result[0]
    return username

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
# 6. ВХОД В СИСТЕМУ (ПО 4-ЗНАЧНОМУ КОДУ)
# ============================================================

def login_page():
    st.markdown("<h1 style='text-align:center;'>📦 Управление складом</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Вход по коду", "📝 Регистрация"])
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            access_code = st.text_input(
                "Введите 4-значный код доступа", 
                type="password",
                placeholder="Например: 1234",
                max_chars=4
            )
            
            if st.button("🔓 Войти", use_container_width=True):
                if access_code and len(access_code) == 4:
                    user = get_user_by_code(access_code)
                    if user:
                        user_id = user[0]
                        user_username = user[1]
                        user_full_name = user[2]
                        user_role = user[3]
                        user_status = user[4]
                        
                        if user_status == "blocked":
                            st.error("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
                        elif user_status == "pending":
                            st.warning("⏳ Ваш аккаунт ожидает одобрения администратора.")
                        else:
                            if user_username == "admin":
                                user_role = "admin"
                            
                            st.session_state.user = {
                                "id": user_id,
                                "username": user_username,
                                "full_name": user_full_name,
                                "role": user_role,
                                "status": user_status
                            }
                            st.rerun()
                    else:
                        st.error("❌ Неверный код доступа!")
                else:
                    st.warning("⚠️ Введите 4-значный код!")
    
    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 📝 Регистрация нового сотрудника")
            
            with st.form("register_form"):
                reg_username = st.text_input(
                    "Придумайте логин*", 
                    placeholder="Например: ivanov",
                    help="Будет отображаться в системе"
                )
                reg_full_name = st.text_input(
                    "Ваше полное имя*", 
                    placeholder="Например: Иванов Иван Иванович",
                    help="Будет отображаться в списаниях"
                )
                reg_code = st.text_input(
                    "Придумайте 4-значный код доступа*", 
                    type="password",
                    placeholder="Например: 1234",
                    max_chars=4,
                    help="Код должен состоять из 4 цифр"
                )
                reg_code_confirm = st.text_input(
                    "Подтвердите код доступа*", 
                    type="password",
                    placeholder="Повторите код",
                    max_chars=4
                )
                
                if st.form_submit_button("📝 Зарегистрироваться", use_container_width=True):
                    if not reg_username or not reg_full_name or not reg_code:
                        st.error("❌ Заполните все обязательные поля!")
                    elif reg_code != reg_code_confirm:
                        st.error("❌ Коды не совпадают!")
                    elif len(reg_code) != 4:
                        st.error("❌ Код должен состоять из 4 цифр!")
                    elif not reg_code.isdigit():
                        st.error("❌ Код должен содержать только цифры!")
                    else:
                        success, msg = add_user(reg_username, reg_code, reg_full_name)
                        if success:
                            st.success(f"✅ {msg}")
                            st.info("📧 После одобрения администратором вы сможете войти в систему.")
                        else:
                            st.error(f"❌ {msg}")

if st.session_state.user is None:
    login_page()
    st.stop()

# ============================================================
# ПОЛУЧАЕМ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ ИЗ СЕССИИ
# ============================================================

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
        if pending_count > 0:
            button_text += f" 📝{pending_count}"
        if low_stock_count > 0 and role == "admin":
            button_text += f" ⚠️{low_stock_count}"
        if returned_count > 0 and role == "admin":
            button_text += f" 🔄{returned_count}"
        
        if st.button(button_text, use_container_width=True):
            st.session_state.active_tab = 0
            st.rerun()
    else:
        if st.button("✅ Нет уведомлений", use_container_width=True):
            pass
    
    if role == "admin":
        shopping = get_shopping_list()
        if shopping:
            low_stock_shopping = len([s for s in shopping if s.get('type') == 'low_stock'])
            pending_shopping = len([s for s in shopping if s.get('type') == 'pending'])
            in_work_shopping = len([s for s in shopping if s.get('type') == 'in_work'])
            
            button_text = f"🛒 К покупке: {len(shopping)}"
            if low_stock_shopping > 0:
                button_text += f" ⚠️{low_stock_shopping}"
            if pending_shopping > 0:
                button_text += f" 📝{pending_shopping}"
            if in_work_shopping > 0:
                button_text += f" 🔧{in_work_shopping}"
            
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
                unit = st.selectbox("Ед.", ["шт", "л", "кг", "м", "комплект"], key="quick_unit")
            
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

# Персонализированное приветствие
greeting = f"Добро пожаловать, {user_name}!"
st.title(f"📦 {greeting}")

counts = get_unread_counts()

if role == "admin":
    request_label = "📝 Заявки"
    if counts['unread_requests'] > 0:
        request_label += f" 🔴{counts['unread_requests']}"
    
    low_stock_label = "📋 Товары"
    if counts['unread_low_stock'] > 0:
        low_stock_label += f" ⚠️{counts['unread_low_stock']}"
    
    consumption_label = "📤 Списания"
    if counts['unread_consumptions'] > 0:
        consumption_label += f" 🆕{counts['unread_consumptions']}"
    
    tabs = st.tabs([
        request_label, low_stock_label, consumption_label,
        "🛒 Покупки", "🚜 Парк", "👥 Пользователи", "⚙️ Управление"
    ])
else:
    request_label = "📝 Заявки"
    if counts['unread_requests'] > 0:
        request_label += f" 🔴{counts['unread_requests']}"
    
    consumption_label = "📤 Списания"
    if counts['unread_consumptions'] > 0:
        consumption_label += f" 🆕{counts['unread_consumptions']}"
    
    tabs = st.tabs([
        request_label, "📋 Товары", consumption_label,
        "🛒 Покупки", "🚜 Парк", "⚙️ Управление"
    ])

# ============================================================
# 8.1 ЗАЯВКИ (ИНДЕКС 0)
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
            with c1:
                qty = st.number_input("Кол-во", min_value=0.1, value=1.0)
            with c2:
                unit = st.selectbox("Ед.", ["шт", "л", "кг", "м", "комплект"])
            desc = st.text_area("Описание")
            photo = st.file_uploader("Фото", type=["jpg","jpeg","png"], key="request_photo")
            
            submitted = st.form_submit_button("📤 Отправить")
            
            if submitted and name:
                photo_path = ""
                if photo is not None:
                    if not os.path.exists("images"):
                        os.makedirs("images")
                    ext = photo.name.split('.')[-1]
                    photo_path = f"images/req_{uuid.uuid4()}.{ext}"
                    with open(photo_path, "wb") as f:
                        f.write(photo.getbuffer())
                add_request(name, qty, unit, desc, photo_path, current_username)
                st.success("✅ Заявка отправлена!")
                st.rerun()
        
        st.divider()
        st.subheader("📋 Мои заявки")
        my_requests = get_requests(user=current_username)
        
        if my_requests:
            for req in my_requests:
                r = unpack_request(req)
                status_text = {
                    'pending': '⏳ На рассмотрении', 'in_work': '🔧 В работе',
                    'approved': '✅ Выполнено', 'rejected': '❌ Отклонено',
                    'suggested': '💡 Предложен товар', 'returned': '🔄 Возвращено'
                }
                with st.expander(f"{status_text.get(r['status'], r['status'])} | {r['name']} — {r['quantity']} {r['unit']}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if r['description']:
                            st.write(f"📝 Описание: {r['description']}")
                        if r['admin_comment']:
                            st.write(f"💬 Комментарий: {r['admin_comment']}")
                        st.caption(f"📅 {r['date']}")
                    with col2:
                        if r['photo'] and os.path.exists(r['photo']):
                            st.image(r['photo'], width=200)
                        else:
                            st.caption("📷 Нет фото")
                    
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
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.write(f"📦 {item[1]} — {item[6]} {item[5]} | {item[3]}")
                            with col2:
                                photos = get_item_photos(item[0])
                                if photos:
                                    main_photo = next((p for p in photos if p[2] == 1), photos[0])
                                    if os.path.exists(main_photo[1]):
                                        st.image(main_photo[1], width=100)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Подходит", key=f"ok_{r['id']}"):
                                mark_request_seen(r['id'])
                                st.rerun()
                        with col2:
                            if st.button("❌ Не подходит", key=f"no_{r['id']}"):
                                st.session_state[f"ret_{r['id']}"] = True
                        
                        if st.session_state.get(f"ret_{r['id']}"):
                            reason = st.text_area("Причина возврата", key=f"reason_{r['id']}")
                            if st.button("📤 Отправить на пересмотр", key=f"send_{r['id']}"):
                                return_request(r['id'], reason)
                                st.session_state[f"ret_{r['id']}"] = False
                                st.rerun()
        else:
            st.info("У вас нет заявок")
    
    else:
        statuses = {
            "⏳ Новые": "pending", "🔧 В работе": "in_work",
            "🔄 Возвраты": "returned", "💡 Предложенные": "suggested",
            "✅ Готовые": "approved", "❌ Отклоненные": "rejected"
        }
        subtabs = st.tabs(list(statuses.keys()))
        
        for tab, (label, status) in zip(subtabs, statuses.items()):
            with tab:
                reqs = get_requests(status=status)
                if reqs:
                    for req in reqs:
                        r = unpack_request(req)
                        with st.expander(f"{r['name']} — {r['quantity']} {r['unit']} | от {r['user']} | {r['date'][:10]}"):
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                if r['description']:
                                    st.write(f"📝 Описание: {r['description']}")
                                if r['admin_comment']:
                                    st.write(f"💬 Комментарий: {r['admin_comment']}")
                                if r['suggested_item_id']:
                                    st.write(f"💡 Предложен товар ID: {r['suggested_item_id']}")
                            with col2:
                                if r['photo'] and os.path.exists(r['photo']):
                                    st.image(r['photo'], width=200)
                                else:
                                    st.caption("📷 Нет фото")
                            
                            st.divider()
                            
                            if status in ['pending', 'returned']:
                                c1, c2, c3 = st.columns(3)
                                with c1:
                                    if st.button("✅ Одобрить", key=f"app_{r['id']}"):
                                        update_request_status(r['id'], "approved")
                                        st.rerun()
                                with c2:
                                    if st.button("💡 Со склада", key=f"sug_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = True
                                with c3:
                                    if st.button("❌ Отклонить", key=f"rej_{r['id']}"):
                                        update_request_status(r['id'], "rejected")
                                        st.rerun()
                                
                                if st.session_state.get(f"sug_{r['id']}"):
                                    sq = st.text_input("Поиск товара на складе", key=f"sq_{r['id']}")
                                    if sq:
                                        found = search_items(sq)
                                        if found:
                                            for item in found:
                                                col1, col2 = st.columns([2, 1])
                                                with col1:
                                                    st.write(f"📦 {item[1]} — {item[6]} {item[5]} | {item[3]}")
                                                with col2:
                                                    if st.button("📤 Предложить", key=f"sel_{r['id']}_{item[0]}"):
                                                        update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                                        st.session_state[f"sug_{r['id']}"] = False
                                                        st.rerun()
                                    if st.button("❌ Закрыть", key=f"close_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = False
                                        st.rerun()
                            
                            elif status == 'in_work':
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.button("✅ Выполнено", key=f"done_{r['id']}"):
                                        update_request_status(r['id'], "approved")
                                        st.rerun()
                                with c2:
                                    if st.button("🗑️ Удалить", key=f"del_req_{r['id']}"):
                                        delete_request(r['id'])
                                        st.rerun()
                            
                            elif status == 'approved':
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("📦 Создать товар", key=f"create_{r['id']}"):
                                        st.session_state[f"create_mode_{r['id']}"] = True
                                with col2:
                                    if st.button("🗑️ Удалить", key=f"del_approved_{r['id']}"):
                                        delete_request(r['id'])
                                        st.success("🗑️ Заявка удалена!")
                                        st.rerun()
                                
                                if st.session_state.get(f"create_mode_{r['id']}"):
                                    rooms = get_room_names()
                                    if rooms:
                                        room = st.selectbox("Помещение", rooms, key=f"cr_{r['id']}")
                                        loc = st.text_input("Место", key=f"cl_{r['id']}")
                                        c1, c2 = st.columns(2)
                                        with c1:
                                            if st.button("💾 Сохранить", key=f"cs_{r['id']}") and loc:
                                                item_id = add_item(r['name'], loc, room, r['quantity'], r['unit'])
                                                delete_request(r['id'])
                                                st.success(f"✅ Товар '{r['name']}' создан!")
                                                st.rerun()
                                        with c2:
                                            if st.button("❌ Отмена", key=f"cancel_create_{r['id']}"):
                                                st.session_state[f"create_mode_{r['id']}"] = False
                                                st.rerun()
                            
                            elif status == 'rejected':
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("🔄 Вернуть на рассмотрение", key=f"return_to_pending_{r['id']}"):
                                        update_request_status(r['id'], "pending", "")
                                        st.rerun()
                                with col2:
                                    if st.button("🗑️ Удалить", key=f"del_rejected_{r['id']}"):
                                        delete_request(r['id'])
                                        st.success("🗑️ Заявка удалена!")
                                        st.rerun()
                            
                            elif status == 'suggested':
                                if st.button("🗑️ Удалить", key=f"del_suggested_{r['id']}"):
                                    delete_request(r['id'])
                                    st.success("🗑️ Заявка удалена!")
                                    st.rerun()
                else:
                    st.info(f"Нет заявок со статусом '{label}'")

# ============================================================
# 8.2 ТОВАРЫ (ИНДЕКС 1)
# ============================================================

with tabs[1]:
    st.markdown("## 📋 Все товары")
    
    all_items = get_all_items()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Всего", len(all_items))
    with col2:
        st.metric("⚠️ Заканчиваются", len([i for i in all_items if i[6] <= i[7] and i[6] > 0]))
    with col3:
        st.metric("🚫 Нет в наличии", len([i for i in all_items if i[6] == 0]))
    with col4:
        st.metric("📸 С фото", len([i for i in all_items if i[8] and int(i[8]) > 0]))
    
    st.divider()
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("🔍 Поиск", placeholder="Введите запрос...", key="items_search")
    with col2:
        filter_type = st.selectbox("Фильтр", ["Все", "Заканчиваются", "Нет в наличии", "В наличии"])
    with col3:
        sort_by = st.selectbox("Сортировка", ["По дате (новые)", "По дате (старые)", "По названию", "По количеству"])
    
    items = search_items(search) if search else get_all_items()
    
    if filter_type == "Заканчиваются":
        items = [i for i in items if i[6] <= i[7] and i[6] > 0]
    elif filter_type == "Нет в наличии":
        items = [i for i in items if i[6] == 0]
    elif filter_type == "В наличии":
        items = [i for i in items if i[6] > 0]
    
    if sort_by == "По дате (новые)":
        items.sort(key=lambda x: x[4] or "", reverse=True)
    elif sort_by == "По дате (старые)":
        items.sort(key=lambda x: x[4] or "")
    elif sort_by == "По названию":
        items.sort(key=lambda x: x[1] or "")
    elif sort_by == "По количеству":
        items.sort(key=lambda x: x[6] or 0)
    
    if items:
        st.success(f"Найдено товаров: {len(items)}")
        
        per_page = 10
        total_pages = (len(items) - 1) // per_page + 1
        page = st.selectbox("Страница", range(1, total_pages + 1), key="items_page") if total_pages > 1 else 1
        
        start = (page - 1) * per_page
        end = min(start + per_page, len(items))
        
        for idx, item in enumerate(items[start:end]):
            item_id = item[0]
            name = item[1]
            location = item[2] if len(item) > 2 else ""
            room = item[3] if len(item) > 3 else ""
            date_added = item[4] if len(item) > 4 else ""
            unit = item[5] if len(item) > 5 else "шт"
            quantity = float(item[6]) if len(item) > 6 else 0
            threshold = int(item[7]) if len(item) > 7 else 1
            
            if quantity == 0:
                status_icon, status_text = "🚫", "Нет в наличии"
            elif quantity <= threshold:
                status_icon, status_text = "⚠️", f"Заканчивается (порог: {threshold})"
            else:
                status_icon, status_text = "✅", f"В наличии: {quantity} {unit}"
            
            uid = f"{item_id}_{idx}"
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {status_icon} {name}")
                    st.caption(f"📍 {location} | 🏠 {room} | 📅 {date_added[:10] if date_added else 'Н/Д'}")
                with col2:
                    st.markdown(f"### {quantity}")
                    st.caption(unit)
                
                st.divider()
                
                col_left, col_right = st.columns([2, 2])
                
                with col_left:
                    st.markdown(f"**📦 Название:** {name}")
                    st.markdown(f"**📍 Место:** {location}")
                    st.markdown(f"**🏠 Помещение:** {room}")
                    st.markdown(f"**📊 Количество:** {quantity} {unit}")
                    st.markdown(f"**⚠️ Порог:** {threshold}")
                    
                    if quantity == 0:
                        st.error(status_text)
                    elif quantity <= threshold:
                        st.warning(status_text)
                    else:
                        st.success(status_text)
                
                with col_right:
                    photos = get_item_photos(item_id)
                    
                    if photos:
                        photo_key = f"photo_idx_{item_id}"
                        if photo_key not in st.session_state:
                            st.session_state[photo_key] = 0
                        
                        current_idx = st.session_state[photo_key]
                        if current_idx >= len(photos):
                            current_idx = 0
                            st.session_state[photo_key] = 0
                        
                        current_photo = photos[current_idx]
                        
                        if os.path.exists(current_photo[1]):
                            if len(photos) > 1:
                                c1, c2, c3 = st.columns([1, 2, 1])
                                with c1:
                                    if st.button("◀", key=f"prev_{uid}"):
                                        st.session_state[photo_key] = (current_idx - 1) % len(photos)
                                        st.rerun()
                                with c2:
                                    st.caption(f"{current_idx + 1} / {len(photos)}")
                                with c3:
                                    if st.button("▶", key=f"next_{uid}"):
                                        st.session_state[photo_key] = (current_idx + 1) % len(photos)
                                        st.rerun()
                            
                            st.image(current_photo[1], use_container_width=True)
                            if current_photo[2] == 1:
                                st.caption("⭐ Главное фото")
                            else:
                                st.caption("📸 Обычное фото")
                            
                            if role == "admin":
                                st.divider()
                                st.markdown("**⚙️ Управление фото**")
                                
                                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                                
                                with col_btn1:
                                    if st.button("↺ Влево", key=f"rot_l_{uid}", use_container_width=True):
                                        if rotate_photo(current_photo[1], 90):
                                            st.rerun()
                                
                                with col_btn2:
                                    if st.button("↻ Вправо", key=f"rot_r_{uid}", use_container_width=True):
                                        if rotate_photo(current_photo[1], -90):
                                            st.rerun()
                                
                                with col_btn3:
                                    if current_photo[2] != 1:
                                        if st.button("⭐ Главное", key=f"main_{uid}", use_container_width=True):
                                            set_main_photo(current_photo[0])
                                            st.rerun()
                                    else:
                                        st.button("⭐ Главное", key=f"main_disabled_{uid}", disabled=True, use_container_width=True)
                                
                                with col_btn4:
                                    if st.button("🗑️ Удалить", key=f"del_photo_{uid}", use_container_width=True):
                                        delete_item_photo(current_photo[0])
                                        st.session_state[photo_key] = 0
                                        st.rerun()
                                
                                if len(photos) > 1:
                                    st.markdown("**📸 Все фото товара:**")
                                    cols = st.columns(min(4, len(photos)))
                                    for i, p in enumerate(photos):
                                        with cols[i % 4]:
                                            if os.path.exists(p[1]):
                                                st.image(p[1], use_container_width=True)
                                                label = "⭐" if p[2] == 1 else f"{i+1}"
                                                if st.button(label, key=f"goto_{uid}_{p[0]}", use_container_width=True):
                                                    st.session_state[photo_key] = i
                                                    st.rerun()
                                
                                st.markdown("**📤 Добавить фото:**")
                                uploaded = st.file_uploader(
                                    "Выберите фотографии (можно несколько)",
                                    type=["jpg", "jpeg", "png"],
                                    accept_multiple_files=True,
                                    key=f"upload_{uid}"
                                )
                                
                                if uploaded:
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        is_main_new = st.checkbox("⭐ Сделать первое фото главным", key=f"is_main_{uid}")
                                    with col2:
                                        if st.button("📤 Загрузить", key=f"save_{uid}", use_container_width=True):
                                            for i, uf in enumerate(uploaded):
                                                ext = uf.name.split('.')[-1]
                                                path = f"images/items/{item_id}_{now_local_file()}_{i}.{ext}"
                                                with open(path, "wb") as f:
                                                    f.write(uf.getbuffer())
                                                add_item_photo(item_id, path, is_main=(i == 0 and is_main_new))
                                            st.success(f"✅ Загружено {len(uploaded)} фото!")
                                            st.rerun()
                    else:
                        st.info("📷 Нет фото")
                        
                        if role == "admin":
                            st.markdown("**📤 Добавить фото:**")
                            uploaded = st.file_uploader(
                                "Выберите фотографии (можно несколько)",
                                type=["jpg", "jpeg", "png"],
                                accept_multiple_files=True,
                                key=f"upload_empty_{uid}"
                            )
                            
                            if uploaded:
                                col1, col2 = st.columns(2)
                                with col1:
                                    is_main_new = st.checkbox("⭐ Сделать первое фото главным", key=f"is_main_empty_{uid}")
                                with col2:
                                    if st.button("📤 Загрузить", key=f"save_empty_{uid}", use_container_width=True):
                                        for i, uf in enumerate(uploaded):
                                            ext = uf.name.split('.')[-1]
                                            path = f"images/items/{item_id}_{now_local_file()}_{i}.{ext}"
                                            with open(path, "wb") as f:
                                                f.write(uf.getbuffer())
                                            add_item_photo(item_id, path, is_main=(i == 0 and is_main_new))
                                        st.success(f"✅ Загружено {len(uploaded)} фото!")
                                        st.rerun()
                
                st.divider()
                
                if role != "admin":
                    with st.expander("📤 Взять товар", expanded=False):
                        if quantity > 0:
                            st.markdown(f"**Доступно: {quantity} {unit}**")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                take_qty = st.number_input(
                                    "Количество", 
                                    min_value=0.1, 
                                    max_value=float(quantity), 
                                    value=min(1.0, float(quantity)),
                                    key=f"tq_{uid}"
                                )
                            with col2:
                                eq_search = st.text_input(
                                    "Поиск техники (название или номер)", 
                                    key=f"eqs_{uid}",
                                    placeholder="Введите название..."
                                )
                            
                            eq_list = search_equipment(eq_search) if eq_search else get_equipment()
                            
                            if eq_list:
                                eq_options = {f"{e[1]}" + (f" (№{e[2]})" if e[2] else ""): e for e in eq_list}
                                selected = st.selectbox(
                                    "Выберите технику", 
                                    list(eq_options.keys()), 
                                    key=f"eq_sel_{uid}"
                                )
                                eq = eq_options[selected]
                                
                                take_photo = st.file_uploader(
                                    "📸 Фото (опционально)", 
                                    type=["jpg","jpeg","png"], 
                                    key=f"tp_{uid}"
                                )
                                
                                if st.button("✅ Подтвердить взятие", key=f"confirm_{uid}", use_container_width=True):
                                    photo_path = ""
                                    if take_photo:
                                        if not os.path.exists("images/take"):
                                            os.makedirs("images/take")
                                        ext = take_photo.name.split('.')[-1]
                                        photo_path = f"images/take/take_{item_id}_{now_local_file()}.{ext}"
                                        with open(photo_path, "wb") as f:
                                            f.write(take_photo.getbuffer())
                                    
                                    success, msg = take_item(
                                        item_id, take_qty, eq[1], 
                                        eq[2] if len(eq) > 2 else "", photo_path
                                    )
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            else:
                                st.warning("⚠️ Нет добавленной техники. Добавьте технику в разделе 'Парк'")
                        else:
                            st.warning("🚫 Товара нет в наличии")
                
                else:
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                    
                    with col_btn1:
                        if st.button("✏️ Редактировать", key=f"edit_btn_{uid}", use_container_width=True):
                            st.session_state[f"edit_mode_{uid}"] = not st.session_state.get(f"edit_mode_{uid}", False)
                    
                    with col_btn2:
                        if st.button("📤 Списать", key=f"take_btn_{uid}", use_container_width=True):
                            st.session_state[f"take_mode_{uid}"] = not st.session_state.get(f"take_mode_{uid}", False)
                    
                    with col_btn3:
                        if st.button("📦 Переместить", key=f"move_btn_{uid}", use_container_width=True):
                            st.session_state[f"move_mode_{uid}"] = not st.session_state.get(f"move_mode_{uid}", False)
                    
                    with col_btn4:
                        if st.button("🗑️ Удалить", key=f"del_btn_{uid}", use_container_width=True):
                            st.session_state[f"del_mode_{uid}"] = not st.session_state.get(f"del_mode_{uid}", False)
                    
                    if st.session_state.get(f"edit_mode_{uid}", False):
                        with st.container():
                            st.markdown("---")
                            st.markdown("#### ✏️ Редактирование товара")
                            with st.form(key=f"edit_form_{uid}"):
                                edit_name = st.text_input("Название*", value=name, key=f"en_{uid}")
                                edit_loc = st.text_input("Место*", value=location, key=f"el_{uid}")
                                rooms = get_room_names()
                                edit_room = st.selectbox("Помещение", rooms if rooms else ["Нет"], 
                                                        index=rooms.index(room) if room in rooms else 0,
                                                        key=f"er_{uid}")
                                c1, c2 = st.columns(2)
                                with c1:
                                    edit_qty = st.number_input("Количество", value=float(quantity), key=f"eq_{uid}")
                                with c2:
                                    edit_unit = st.selectbox("Ед.", ["шт","л","кг","м","комплект"], 
                                                            index=["шт","л","кг","м","комплект"].index(unit) if unit in ["шт","л","кг","м","комплект"] else 0,
                                                            key=f"eu_{uid}")
                                edit_threshold = st.number_input("Порог", value=int(threshold), key=f"et_{uid}")
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.form_submit_button("💾 Сохранить изменения"):
                                        if edit_name and edit_loc and edit_room != "Нет":
                                            update_item(item_id, edit_name, edit_loc, edit_room, edit_qty, edit_unit, edit_threshold)
                                            st.success("✅ Товар обновлён!")
                                            st.session_state[f"edit_mode_{uid}"] = False
                                            st.rerun()
                                with c2:
                                    if st.form_submit_button("❌ Отмена"):
                                        st.session_state[f"edit_mode_{uid}"] = False
                                        st.rerun()
                    
                    if st.session_state.get(f"take_mode_{uid}", False):
                        with st.container():
                            st.markdown("---")
                            st.markdown("#### 📤 Списание товара")
                            with st.form(key=f"take_form_{uid}"):
                                if quantity > 0:
                                    take_qty = st.number_input(
                                        "Количество", min_value=0.1, max_value=float(quantity), 
                                        value=1.0, key=f"tq_admin_{uid}"
                                    )
                                    eq_search = st.text_input("Поиск техники", key=f"eqs_admin_{uid}")
                                    eq_list = search_equipment(eq_search) if eq_search else get_equipment()
                                    if eq_list:
                                        eq_options = {f"{e[1]}" + (f" (№{e[2]})" if e[2] else ""): e for e in eq_list}
                                        selected = st.selectbox("Выберите технику", list(eq_options.keys()), key=f"eq_sel_admin_{uid}")
                                        eq = eq_options[selected]
                                        take_photo = st.file_uploader("📸 Фото", type=["jpg","jpeg","png"], key=f"tp_admin_{uid}")
                                        c1, c2 = st.columns(2)
                                        with c1:
                                            if st.form_submit_button("✅ Подтвердить списание"):
                                                photo_path = ""
                                                if take_photo:
                                                    ext = take_photo.name.split('.')[-1]
                                                    photo_path = f"images/take/take_{item_id}_{now_local_file()}.{ext}"
                                                    with open(photo_path, "wb") as f:
                                                        f.write(take_photo.getbuffer())
                                                success, msg = take_item(item_id, take_qty, eq[1], eq[2] if len(eq) > 2 else "", photo_path)
                                                if success:
                                                    st.success(msg)
                                                    st.session_state[f"take_mode_{uid}"] = False
                                                    st.rerun()
                                                else:
                                                    st.error(msg)
                                        with c2:
                                            if st.form_submit_button("❌ Отмена"):
                                                st.session_state[f"take_mode_{uid}"] = False
                                                st.rerun()
                                    else:
                                        st.warning("⚠️ Нет техники. Добавьте в 'Парк'")
                                else:
                                    st.warning("🚫 Товара нет в наличии")
                    
                    if st.session_state.get(f"move_mode_{uid}", False):
                        with st.container():
                            st.markdown("---")
                            st.markdown("#### 📦 Перемещение товара")
                            with st.form(key=f"move_form_{uid}"):
                                new_loc = st.text_input("Новое место*", value=location, key=f"ml_{uid}")
                                rooms = get_room_names()
                                new_room = st.selectbox("Новое помещение", rooms if rooms else ["Нет"],
                                                       index=rooms.index(room) if room in rooms else 0, key=f"mr_{uid}")
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.form_submit_button("📦 Переместить"):
                                        if new_loc and new_room != "Нет":
                                            move_item(item_id, new_loc, new_room)
                                            st.success(f"✅ Перемещено в {new_loc} ({new_room})")
                                            st.session_state[f"move_mode_{uid}"] = False
                                            st.rerun()
                                with c2:
                                    if st.form_submit_button("❌ Отмена"):
                                        st.session_state[f"move_mode_{uid}"] = False
                                        st.rerun()
                    
                    if st.session_state.get(f"del_mode_{uid}", False):
                        with st.container():
                            st.markdown("---")
                            st.markdown("#### 🗑️ Удаление товара")
                            st.warning(f"⚠️ Вы уверены, что хотите удалить товар '{name}'?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Да, удалить", key=f"del_confirm_{uid}", use_container_width=True):
                                    delete_item(item_id)
                                    st.success(f"🗑️ Товар '{name}' удалён")
                                    st.session_state[f"del_mode_{uid}"] = False
                                    st.rerun()
                            with col2:
                                if st.button("❌ Отмена", key=f"del_cancel_{uid}", use_container_width=True):
                                    st.session_state[f"del_mode_{uid}"] = False
                                    st.rerun()
                
                st.divider()
    else:
        st.info("📭 Склад пуст. Добавьте товары через боковую панель.")

# ============================================================
# 8.3 СПИСАНИЯ (ИНДЕКС 2)
# ============================================================

with tabs[2]:
    st.markdown("## 📤 Списания")
    
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""
        SELECT c.*, i.name 
        FROM consumption c 
        LEFT JOIN items i ON c.item_id = i.id 
        ORDER BY c.date DESC 
        LIMIT 500
    """)
    cons = c.fetchall()
    conn.close()
    
    if cons:
        total_items = len(cons)
        total_quantity = sum([row[2] for row in cons if row[2] is not None])
        unique_users = len(set([row[5] for row in cons if row[5]]))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Всего списаний", total_items)
        with col2:
            st.metric("📊 Всего единиц", f"{total_quantity:.1f}")
        with col3:
            st.metric("👥 Сотрудников", unique_users)
        
        st.divider()
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            search_consumption = st.text_input(
                "🔍 Поиск по названию, сотруднику или технике", 
                placeholder="Введите запрос...", 
                key="consumption_search_final_v4"
            )
        with col2:
            dates = sorted(set([row[6][:10] for row in cons if row[6]]), reverse=True)
            date_filter = st.selectbox("📅 Фильтр по дате", ["Все"] + dates, key="consumption_date_final_v4")
        with col3:
            if st.button("🔄 Обновить", key="refresh_consumption_final_v4", use_container_width=True):
                st.rerun()
        
        filtered_cons = cons
        
        if search_consumption:
            search_lower = search_consumption.lower()
            filtered_cons = [
                row for row in filtered_cons 
                if (row[-1] and search_lower in str(row[-1]).lower()) or
                   (row[5] and search_lower in str(row[5]).lower()) or
                   (row[7] and search_lower in str(row[7]).lower()) or
                   (row[8] and search_lower in str(row[8]).lower())
            ]
        
        if date_filter != "Все":
            filtered_cons = [row for row in filtered_cons if row[6] and row[6][:10] == date_filter]
        
        if filtered_cons:
            grouped_by_date = {}
            for row in filtered_cons:
                date_key = row[6][:10] if row[6] else "Без даты"
                if date_key not in grouped_by_date:
                    grouped_by_date[date_key] = []
                grouped_by_date[date_key].append(row)
            
            sorted_dates = sorted(grouped_by_date.keys(), reverse=True)
            
            for date_key in sorted_dates:
                items = grouped_by_date[date_key]
                
                date_obj = datetime.strptime(date_key, "%Y-%m-%d") if date_key != "Без даты" else None
                date_display = date_obj.strftime("%d.%m.%Y") if date_obj else "Без даты"
                
                with st.expander(f"📅 {date_display} — {len(items)} списаний", expanded=False):
                    items.sort(key=lambda x: x[6] if x[6] else "", reverse=True)
                    
                    for idx, row in enumerate(items):
                        consumption_id = row[0]
                        item_id = row[1]
                        quantity = row[2]
                        unit = row[3]
                        object_name = row[4]
                        user_login = row[5]
                        date = row[6]
                        equipment_name = row[7]
                        equipment_number = row[8]
                        photo = row[9] if len(row) > 9 and row[9] else None
                        item_name = row[-1] if len(row) > 10 and row[-1] else f"Товар (ID: {item_id})"
                        
                        user_full_name_display = get_user_full_name(user_login)
                        if user_full_name_display and user_full_name_display != user_login:
                            display_name = f"{user_full_name_display} ({user_login})"
                        else:
                            display_name = user_login
                        
                        uid = f"cons_final_v4_{consumption_id}"
                        
                        with st.container():
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                st.markdown(f"**📦 {item_name}**")
                                st.markdown(f"**📊 Количество:** {quantity} {unit}")
                                st.markdown(f"**👤 Сотрудник:** {display_name}")
                                st.markdown(f"**🎯 Назначение:** {object_name}")
                                if equipment_name:
                                    equipment_info = equipment_name
                                    if equipment_number:
                                        equipment_info += f" (№{equipment_number})"
                                    st.markdown(f"**🚜 Техника:** {equipment_info}")
                                st.caption(f"🕐 {date[11:16] if len(date) > 11 else ''}")
                            
                            with col2:
                                st.markdown("**📸 Фото**")
                                has_photo = False
                                
                                if photo and os.path.exists(photo):
                                    st.image(photo, width=150)
                                    has_photo = True
                                elif item_id:
                                    item_photos = get_item_photos(item_id)
                                    if item_photos:
                                        main_photo = next((p for p in item_photos if p[2] == 1), item_photos[0])
                                        if os.path.exists(main_photo[1]):
                                            st.image(main_photo[1], width=150)
                                            has_photo = True
                                
                                if not has_photo:
                                    st.caption("📷 Нет фото")
                            
                            with col3:
                                if role == "admin":
                                    st.markdown("**⚙️ Действия**")
                                    
                                    if st.button("↩️ Вернуть", key=f"return_{uid}", use_container_width=True):
                                        try:
                                            db = sqlite3.connect('storage.db')
                                            cur = db.cursor()
                                            cur.execute("SELECT quantity FROM items WHERE id=?", (item_id,))
                                            result = cur.fetchone()
                                            
                                            if result is not None:
                                                current_qty = result[0]
                                                new_qty = current_qty + quantity
                                                cur.execute("UPDATE items SET quantity=? WHERE id=?", (new_qty, item_id))
                                                cur.execute("DELETE FROM consumption WHERE id=?", (consumption_id,))
                                                db.commit()
                                                db.close()
                                                st.success(f"✅ {quantity} {unit} товара '{item_name}' возвращено на склад!")
                                                st.rerun()
                                            else:
                                                db.close()
                                                db2 = sqlite3.connect('storage.db')
                                                cur2 = db2.cursor()
                                                cur2.execute("DELETE FROM consumption WHERE id=?", (consumption_id,))
                                                db2.commit()
                                                db2.close()
                                                st.success("🗑️ Запись удалена (товар не найден на складе)")
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Ошибка: {str(e)}")
                                    
                                    if st.button("🗑️ Удалить", key=f"delete_{uid}", use_container_width=True):
                                        try:
                                            db = sqlite3.connect('storage.db')
                                            cur = db.cursor()
                                            if photo and os.path.exists(photo):
                                                try:
                                                    os.remove(photo)
                                                except:
                                                    pass
                                            cur.execute("DELETE FROM consumption WHERE id=?", (consumption_id,))
                                            db.commit()
                                            db.close()
                                            st.success("🗑️ Запись о списании удалена!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Ошибка: {str(e)}")
                            
                            st.divider()
        else:
            st.info("📭 Нет списаний по выбранным фильтрам")
    else:
        st.info("📭 История списаний пуста")
        st.caption("💡 Списания появляются когда сотрудники берут товары через кнопку 'Взять'")

# ============================================================
# 8.4 ПОКУПКИ (ИНДЕКС 3)
# ============================================================

with tabs[3]:
    st.markdown("## 🛒 Список покупок")
    shopping = get_shopping_list()
    if shopping:
        for item in shopping:
            with st.expander(f"{item['icon']} {item['name']} — {item['qty']} {item['unit']}"):
                if item['type'] in ['in_work', 'pending']:
                    st.write(f"От: {item['user']}" if 'user' in item else "")
                    if st.button("✅ Выполнено", key=f"done_{item['id']}"):
                        update_request_status(item['id'], "approved")
                        st.rerun()
                elif item['type'] == 'low_stock':
                    new_qty = st.number_input("Новое кол-во", value=float(item['qty']), key=f"nq_{item['id']}")
                    if st.button("💾 Обновить", key=f"upd_{item['id']}"):
                        update_quantity(item['id'], new_qty)
                        st.rerun()
    else:
        st.success("✅ Список покупок пуст!")

# ============================================================
# 8.5 ПАРК ТЕХНИКИ (ИНДЕКС 4)
# ============================================================

with tabs[4]:
    st.markdown("## 🚜 Парк техники")
    
    if role == "admin":
        with st.expander("➕ Добавить новую технику", expanded=False):
            with st.form("add_eq"):
                c1, c2 = st.columns(2)
                with c1:
                    name = st.text_input("Название техники*", placeholder="Например: Трактор МТЗ-82")
                with c2:
                    num = st.text_input("Гос. номер", placeholder="Например: А 123 ВС")
                
                st.divider()
                st.markdown("### 🔧 Агрегаты и навесное оборудование")
                st.caption("Добавьте агрегаты, которые закреплены за этой техникой")
                
                num_aggregates = st.number_input("Количество агрегатов", min_value=0, max_value=10, value=0, key="num_agg")
                
                aggregates = []
                for i in range(int(num_aggregates)):
                    st.markdown(f"**Агрегат {i+1}**")
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        agg_name = st.text_input(f"Название агрегата", key=f"agg_name_{i}", placeholder="Например: Плуг ПЛН-3-35")
                    with col_a2:
                        agg_number = st.text_input(f"Инв. номер", key=f"agg_num_{i}", placeholder="Например: 12345")
                    aggregates.append({"name": agg_name, "number": agg_number})
                
                submitted = st.form_submit_button("💾 Сохранить технику", use_container_width=True)
                
                if submitted and name:
                    add_equipment(name, num)
                    
                    if aggregates:
                        conn = sqlite3.connect('storage.db')
                        c = conn.cursor()
                        
                        c.execute('''CREATE TABLE IF NOT EXISTS equipment_aggregates (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            equipment_name TEXT,
                            aggregate_name TEXT,
                            aggregate_number TEXT,
                            date_added TEXT
                        )''')
                        
                        for agg in aggregates:
                            if agg["name"]:
                                c.execute("""INSERT INTO equipment_aggregates 
                                    (equipment_name, aggregate_name, aggregate_number, date_added) 
                                    VALUES (?, ?, ?, ?)""",
                                    (name, agg["name"], agg["number"], now_local()))
                        
                        conn.commit()
                        conn.close()
                    
                    st.success(f"✅ Техника '{name}' добавлена с {len([a for a in aggregates if a['name']])} агрегатами!")
                    st.rerun()
    
    st.divider()
    
    search_eq = st.text_input("🔍 Поиск техники", placeholder="Введите название или номер...", key="eq_search_main")
    
    equipment_list = get_equipment()
    
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    try:
        c.execute("ALTER TABLE equipment_aggregates DROP COLUMN aggregate_type")
    except:
        pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS equipment_aggregates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_name TEXT,
        aggregate_name TEXT,
        aggregate_number TEXT,
        date_added TEXT
    )''')
    
    c.execute("SELECT * FROM equipment_aggregates ORDER BY equipment_name, aggregate_name")
    all_aggregates = c.fetchall()
    conn.close()
    
    aggregates_by_equipment = {}
    for agg in all_aggregates:
        eq_name = agg[1]
        if eq_name not in aggregates_by_equipment:
            aggregates_by_equipment[eq_name] = []
        aggregates_by_equipment[eq_name].append({
            "id": agg[0],
            "name": agg[2],
            "number": agg[3],
            "date": agg[4]
        })
    
    if search_eq:
        search_lower = search_eq.lower()
        equipment_list = [eq for eq in equipment_list 
                         if search_lower in eq[1].lower() or 
                         (eq[2] and search_lower in eq[2].lower())]
    
    if equipment_list:
        total_eq = len(equipment_list)
        total_aggregates = sum([len(aggregates_by_equipment.get(eq[1], [])) for eq in equipment_list])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🚜 Всего техники", total_eq)
        with col2:
            st.metric("🔧 Всего агрегатов", total_aggregates)
        with col3:
            eq_with_agg = len([eq for eq in equipment_list if len(aggregates_by_equipment.get(eq[1], [])) > 0])
            st.metric("📦 Техники с агрегатами", eq_with_agg)
        
        st.divider()
        
        for eq in equipment_list:
            eq_name = eq[1]
            eq_number = eq[2] if len(eq) > 2 else ""
            eq_date = eq[3] if len(eq) > 3 else ""
            
            eq_aggregates = aggregates_by_equipment.get(eq_name, [])
            
            expander_title = f"🚜 {eq_name}"
            if eq_number:
                expander_title += f" (№{eq_number})"
            if eq_aggregates:
                expander_title += f" | 🔧 {len(eq_aggregates)} агрегатов"
            
            with st.expander(expander_title, expanded=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Название:** {eq_name}")
                    if eq_number:
                        st.markdown(f"**Гос. номер:** {eq_number}")
                    st.caption(f"📅 Добавлен: {eq_date[:10] if eq_date else 'Н/Д'}")
                
                with col2:
                    if role == "admin":
                        if st.button("🗑️ Удалить технику", key=f"del_eq_{eq[0]}", use_container_width=True):
                            conn = sqlite3.connect('storage.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM equipment WHERE id=?", (eq[0],))
                            c.execute("DELETE FROM equipment_aggregates WHERE equipment_name=?", (eq_name,))
                            conn.commit()
                            conn.close()
                            st.success(f"🗑️ Техника '{eq_name}' и все её агрегаты удалены!")
                            st.rerun()
                
                st.divider()
                
                if eq_aggregates:
                    st.markdown("### 🔧 Закрепленные агрегаты")
                    
                    for agg in eq_aggregates:
                        with st.container():
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                st.write(f"📦 {agg['name']}")
                            with col2:
                                if agg['number']:
                                    st.write(f"🔢 Инв. №: {agg['number']}")
                            with col3:
                                if role == "admin":
                                    if st.button("🗑️", key=f"del_agg_{agg['id']}", use_container_width=True):
                                        conn = sqlite3.connect('storage.db')
                                        c = conn.cursor()
                                        c.execute("DELETE FROM equipment_aggregates WHERE id=?", (agg['id'],))
                                        conn.commit()
                                        conn.close()
                                        st.success(f"🗑️ Агрегат '{agg['name']}' удален!")
                                        st.rerun()
                            st.divider()
                else:
                    st.info("🔧 Нет закрепленных агрегатов")
                
                if role == "admin":
                    st.markdown("### ➕ Добавить агрегат")
                    with st.form(key=f"add_agg_{eq[0]}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_agg_name = st.text_input("Название агрегата*", key=f"new_agg_name_{eq[0]}")
                        with col2:
                            new_agg_number = st.text_input("Инв. номер", key=f"new_agg_num_{eq[0]}")
                        
                        if st.form_submit_button("💾 Добавить агрегат", use_container_width=True):
                            if new_agg_name:
                                conn = sqlite3.connect('storage.db')
                                c = conn.cursor()
                                c.execute("""INSERT INTO equipment_aggregates 
                                    (equipment_name, aggregate_name, aggregate_number, date_added) 
                                    VALUES (?, ?, ?, ?)""",
                                    (eq_name, new_agg_name, new_agg_number, now_local()))
                                conn.commit()
                                conn.close()
                                st.success(f"✅ Агрегат '{new_agg_name}' добавлен к '{eq_name}'!")
                                st.rerun()
                            else:
                                st.error("❌ Введите название агрегата!")
    else:
        st.info("🚜 Парк техники пуст. Добавьте технику через форму выше.")

# ============================================================
# 8.6 ПОЛЬЗОВАТЕЛИ (ИНДЕКС 5) - ТОЛЬКО ДЛЯ АДМИНА
# ============================================================

if role == "admin":
    with tabs[5]:
        st.markdown("## 👥 Управление пользователями")
        
        pending_users = get_pending_users()
        if pending_users:
            st.markdown("### ⏳ Ожидают подтверждения")
            for user_pending in pending_users:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    with col1:
                        st.markdown(f"**{user_pending[1]}**")
                    with col2:
                        st.caption(f"👤 {user_pending[2]}")
                    with col3:
                        if st.button("✅ Одобрить", key=f"approve_{user_pending[0]}", use_container_width=True):
                            update_user_status(user_pending[0], "active")
                            st.success(f"✅ Пользователь {user_pending[1]} одобрен!")
                            st.rerun()
                    with col4:
                        if st.button("❌ Отклонить", key=f"reject_{user_pending[0]}", use_container_width=True):
                            delete_user(user_pending[0])
                            st.success(f"❌ Пользователь {user_pending[1]} отклонён!")
                            st.rerun()
                    st.divider()
        else:
            st.info("✅ Нет пользователей, ожидающих подтверждения")
        
        st.divider()
        
        st.markdown("### 📋 Все пользователи")
        all_users = get_all_users()
        
        if all_users:
            total = len(all_users)
            active = len([u for u in all_users if u[4] == "active"])
            blocked = len([u for u in all_users if u[4] == "blocked"])
            pending = len([u for u in all_users if u[4] == "pending"])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Всего", total)
            with col2:
                st.metric("✅ Активные", active)
            with col3:
                st.metric("⏳ Ожидают", pending)
            with col4:
                st.metric("🚫 Заблокированы", blocked)
            
            st.divider()
            
            for user_item in all_users:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([1.5, 2, 1.5, 1.5, 1])
                    
                    with col1:
                        st.markdown(f"**{user_item[1]}**")
                        st.caption(user_item[2])
                    
                    with col2:
                        if user_item[3] == "admin":
                            st.caption("🔑 Администратор")
                        else:
                            st.caption("👤 Сотрудник")
                    
                    with col3:
                        status_emoji = {
                            "active": "✅ Активен",
                            "blocked": "🚫 Заблокирован",
                            "pending": "⏳ Ожидает"
                        }
                        st.caption(status_emoji.get(user_item[4], user_item[4]))
                    
                    with col4:
                        st.caption(f"📅 {user_item[5][:10] if user_item[5] else 'Н/Д'}")
                    
                    with col5:
                        if user_item[3] != "admin":
                            if user_item[4] == "active":
                                if st.button("🔒 Заблокировать", key=f"block_{user_item[0]}", use_container_width=True):
                                    update_user_status(user_item[0], "blocked")
                                    st.rerun()
                            elif user_item[4] == "blocked":
                                if st.button("🔓 Разблокировать", key=f"unblock_{user_item[0]}", use_container_width=True):
                                    update_user_status(user_item[0], "active")
                                    st.rerun()
                            if st.button("🗑️ Удалить", key=f"delete_user_{user_item[0]}", use_container_width=True):
                                delete_user(user_item[0])
                                st.rerun()
                    
                    st.divider()
        else:
            st.info("Нет зарегистрированных пользователей")

# ============================================================
# 8.7 УПРАВЛЕНИЕ (ИНДЕКС 6 - ДЛЯ АДМИНА, ИНДЕКС 5 - ДЛЯ СОТРУДНИКА)
# ============================================================

if role == "admin":
    with tabs[6]:
        st.markdown("## ⚙️ Управление")
        tab_a, tab_b = st.tabs(["🏠 Помещения", "💾 Бэкапы"])
        with tab_a:
            with st.form("add_room"):
                name = st.text_input("Название*")
                if st.form_submit_button("Добавить") and name:
                    add_room(name)
                    st.rerun()
            st.markdown("**Существующие помещения:**")
            for room in get_room_names():
                st.write(f"• {room}")
        with tab_b:
            if st.button("💾 Создать бэкап"):
                fname = f"backup_{now_local_file()}.db"
                shutil.copy2('storage.db', f"backups/{fname}")
                st.success(f"✅ Бэкап создан: {fname}")
else:
    with tabs[5]:
        st.markdown("## ⚙️ Управление")
        st.info("ℹ️ Для управления помещениями и бэкапами обратитесь к администратору.")
