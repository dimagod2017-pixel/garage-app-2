import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import pandas as pd
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- СОЗДАЕМ ПАПКИ ДЛЯ ФОТО ---
if not os.path.exists("images"):
    os.makedirs("images")
if not os.path.exists("images/items"):
    os.makedirs("images/items")
if not os.path.exists("images/take"):
    os.makedirs("images/take")

# --- НАСТРОЙКА YANDEX ПОЧТЫ ---
EMAIL_SENDER = "Yvedomlenie-scald.sad@yandex.ru"
EMAIL_PASSWORD = "ТВОЙ_ПАРОЛЬ_ОТ_ПОЧТЫ"
EMAIL_RECIPIENT = "Yvedomlenie-scald.sad@yandex.ru"
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 587

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

# --- ПАРОЛИ И РОЛИ ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown("<h1 style='text-align:center;'>🌿 Мой Склад</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Введите пароль", type="password")
        if st.button("🔓 Войти", use_container_width=True):
            if password in USERS:
                st.session_state.user = USERS[password]
                st.rerun()
            else:
                st.error("❌ Неверный пароль!")

if st.session_state.user is None:
    login_page()
    st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "dismissed_notifications" not in st.session_state:
    st.session_state.dismissed_notifications = []

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
conn_init = sqlite3.connect('storage.db')
c_init = conn_init.cursor()

c_init.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, location TEXT, room TEXT,
                  date_added TEXT, quantity REAL, unit TEXT, threshold INTEGER DEFAULT 1)''')

c_init.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, number TEXT, date_added TEXT)''')

c_init.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT)''')

c_init.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity REAL, unit TEXT,
                  description TEXT, photo TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending',
                  seen INTEGER DEFAULT 0, admin_comment TEXT, suggested_item_id TEXT)''')

c_init.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, quantity REAL, unit TEXT,
                  object_name TEXT, user TEXT, date TEXT)''')

# ДОБАВЛЯЕМ ТАБЛИЦУ ФОТО
c_init.execute('''CREATE TABLE IF NOT EXISTS item_photos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  item_id TEXT,
                  photo_path TEXT,
                  date_added TEXT,
                  is_main INTEGER DEFAULT 0)''')

# ДОБАВЛЯЕМ НЕДОСТАЮЩИЕ КОЛОНКИ
try:
    c_init.execute("ALTER TABLE items ADD COLUMN photos_count INTEGER DEFAULT 0")
except:
    pass

try:
    c_init.execute("ALTER TABLE consumption ADD COLUMN equipment_name TEXT")
except:
    pass

try:
    c_init.execute("ALTER TABLE consumption ADD COLUMN equipment_number TEXT")
except:
    pass

try:
    c_init.execute("ALTER TABLE consumption ADD COLUMN photo TEXT")
except:
    pass

conn_init.commit()
conn_init.close()

# ===== ФУНКЦИИ =====

def add_room(name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?,?)", 
                  (name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_room_names():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT name FROM rooms ORDER BY name")
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names

def add_equipment(name, number=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment (name, number, date_added) VALUES (?,?,?)",
                  (name, number, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_equipment():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def get_equipment_for_search(query=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if query:
        ql = f"%{query}%"
        c.execute("SELECT * FROM equipment WHERE name LIKE ? OR number LIKE ? ORDER BY name", (ql, ql))
    else:
        c.execute("SELECT * FROM equipment ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items ORDER BY date_added DESC")
    results = c.fetchall()
    conn.close()
    return results

def search_items(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    ql = f"%{query}%"
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items WHERE name LIKE ? OR location LIKE ? OR room LIKE ?", (ql, ql, ql))
    results = c.fetchall()
    conn.close()
    return results

def add_item(name, location, room, quantity, unit):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, location, room, date_added, quantity, unit, threshold) VALUES (?,?,?,?,?,?,?,?)",
              (item_id, name, location, room, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, 1))
    conn.commit()
    conn.close()
    return item_id

def update_item(item_id, name, location, room, quantity, unit, threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""UPDATE items 
                 SET name=?, location=?, room=?, quantity=?, unit=?, threshold=? 
                 WHERE id=?""", (name, location, room, quantity, unit, threshold, item_id))
    conn.commit()
    conn.close()

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
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
    photos = c.fetchall()
    for photo in photos:
        if os.path.exists(photo[0]):
            try: os.remove(photo[0])
            except: pass
    c.execute("DELETE FROM item_photos WHERE item_id=?", (item_id,))
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def get_low_stock_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items WHERE quantity <= threshold ORDER BY quantity ASC")
    results = c.fetchall()
    conn.close()
    return results

# ===== ФУНКЦИИ ДЛЯ ФОТО =====

def add_item_photo(item_id, photo_path, is_main=False):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if is_main:
        c.execute("UPDATE item_photos SET is_main=0 WHERE item_id=?", (item_id,))
    c.execute("""INSERT INTO item_photos (item_id, photo_path, date_added, is_main) 
                 VALUES (?,?,?,?)""",
              (item_id, photo_path, datetime.now().strftime("%Y-%m-%d %H:%M"), 1 if is_main else 0))
    c.execute("UPDATE items SET photos_count = photos_count + 1 WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_item_photos(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, photo_path, is_main FROM item_photos WHERE item_id=? ORDER BY is_main DESC, date_added DESC", (item_id,))
    results = c.fetchall()
    conn.close()
    return results

def delete_item_photo(photo_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_id, photo_path FROM item_photos WHERE id=?", (photo_id,))
    result = c.fetchone()
    if result:
        item_id, photo_path = result
        if os.path.exists(photo_path):
            try: os.remove(photo_path)
            except: pass
        c.execute("DELETE FROM item_photos WHERE id=?", (photo_id,))
        c.execute("UPDATE items SET photos_count = photos_count - 1 WHERE id=?", (item_id,))
        c.execute("SELECT id, photo_path FROM item_photos WHERE item_id=? LIMIT 1", (item_id,))
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
    result = c.fetchone()
    if result:
        item_id = result[0]
        c.execute("UPDATE item_photos SET is_main=0 WHERE item_id=?", (item_id,))
        c.execute("UPDATE item_photos SET is_main=1 WHERE id=?", (photo_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def rotate_photo(photo_path, degrees):
    try:
        if not os.path.exists(photo_path):
            return False, "Файл не найден"
        img = Image.open(photo_path)
        rotated = img.rotate(degrees, expand=True)
        rotated.save(photo_path, quality=95)
        return True, f"✅ Фото повернуто на {degrees}°"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

def rotate_photo_left(photo_path):
    return rotate_photo(photo_path, 90)

def rotate_photo_right(photo_path):
    return rotate_photo(photo_path, -90)

def rotate_photo_180(photo_path):
    return rotate_photo(photo_path, 180)

# ===== ФУНКЦИИ ДЛЯ СПИСАНИЙ =====

def consume_item(item_id, quantity, object_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id = ?", (item_id,))
    result = c.fetchone()
    if not result or quantity > result[0]:
        conn.close()
        return False
    new_q = result[0] - quantity
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_q, item_id))
    c.execute("INSERT INTO consumption (item_id, quantity, unit, object_name, user, date) VALUES (?,?,?,?,?,?)",
              (item_id, quantity, result[1], object_name, user_name, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return True

def take_item(item_id, quantity, equipment_name, equipment_number, photo_path=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id=?", (item_id,))
    result = c.fetchone()
    if not result or quantity > result[0]:
        conn.close()
        return False, "Недостаточно товара на складе!"
    new_q = result[0] - quantity
    c.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item_id))
    c.execute("""INSERT INTO consumption 
                 (item_id, quantity, unit, object_name, user, date, equipment_name, equipment_number, photo) 
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (item_id, quantity, result[1], f"{equipment_name} (№{equipment_number})", 
               user_name, datetime.now().strftime("%Y-%m-%d %H:%M"), 
               equipment_name, equipment_number, photo_path))
    conn.commit()
    conn.close()
    return True, f"✅ {quantity} {result[1]} взято на {equipment_name}"

def get_all_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c JOIN items i ON c.item_id = i.id 
                 ORDER BY c.date DESC LIMIT 200""")
    results = c.fetchall()
    conn.close()
    return results

# ===== ФУНКЦИИ ДЛЯ ЗАЯВОК =====

def add_request(name, quantity, unit, description, photo_path, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO requests (name, quantity, unit, description, photo, user, date) VALUES (?,?,?,?,?,?,?)",
              (name, quantity, unit, description, photo_path, user, datetime.now().strftime("%Y-%m-%d %H:%M")))
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
    results = c.fetchall()
    conn.close()
    return results

def update_request_status(request_id, status, comment="", suggested_item_id=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if suggested_item_id:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0, suggested_item_id=? WHERE id=?",
                  (status, comment, suggested_item_id, request_id))
    else:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0 WHERE id=?",
                  (status, comment, request_id))
    conn.commit()
    conn.close()

def return_request(request_id, reason=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    comment = f"Отклонено: {reason}" if reason else "Отклонено сотрудником"
    c.execute("UPDATE requests SET status='returned', admin_comment=?, seen=0 WHERE id=?", (comment, request_id))
    conn.commit()
    conn.close()

def mark_request_seen(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET seen=1 WHERE id=?", (request_id,))
    conn.commit()
    conn.close()

def delete_request(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE id=?", (request_id,))
    conn.commit()
    conn.close()

def create_item_from_request(request_id, name, location, room, quantity, unit):
    item_id = add_item(name, location, room, quantity, unit)
    delete_request(request_id)
    return item_id

def unpack_request(req):
    return {
        'id': req[0], 'name': req[1] if len(req) > 1 else "",
        'quantity': req[2] if len(req) > 2 else 0, 'unit': req[3] if len(req) > 3 else "",
        'description': req[4] if len(req) > 4 else "", 'photo': req[5] if len(req) > 5 else "",
        'user': req[6] if len(req) > 6 else "", 'date': req[7] if len(req) > 7 else "",
        'status': req[8] if len(req) > 8 else "pending", 'seen': req[9] if len(req) > 9 else 0,
        'admin_comment': req[10] if len(req) > 10 else "", 'suggested_item_id': req[11] if len(req) > 11 else None
    }

def show_item_card_mini(item):
    name = item[1] if len(item) > 1 else "Без названия"
    location = item[2] if len(item) > 2 else ""
    room = item[3] if len(item) > 3 else ""
    unit = item[5] if len(item) > 5 else "шт"
    quantity = item[6] if len(item) > 6 else 0
    st.markdown(f"**{name}** — {quantity} {unit} | {room}")
    st.caption(f"📍 {location}")

def get_all_notifications():
    notifications = []
    
    if role == "admin":
        for req in get_requests(status='pending'):
            r = unpack_request(req)
            notif_id = f"pending_{r['id']}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'pending', 'icon': '📝',
                    'title': f'Новая заявка: {r["name"]}',
                    'text': f'От: {r["user"]} | {r["quantity"]} {r["unit"]}',
                    'date': r['date'], 'request_id': r['id']
                })
        
        for req in get_requests(status='returned'):
            r = unpack_request(req)
            notif_id = f"returned_{r['id']}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'returned', 'icon': '🔄',
                    'title': f'Возврат: {r["name"]}',
                    'text': r['admin_comment'][:100] if r['admin_comment'] else 'Без комментария',
                    'date': r['date'], 'request_id': r['id']
                })
        
        for item in get_low_stock_items():
            item_id = item[0]
            name = item[1]
            quantity = item[6] if len(item) > 6 else 0
            unit = item[5] if len(item) > 5 else "шт"
            threshold = item[7] if len(item) > 7 else 1
            date_added = item[4] if len(item) > 4 else ""
            
            notif_id = f"low_{item_id}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'low_stock', 'icon': '⚠️',
                    'title': f'Заканчивается: {name}',
                    'text': f'Осталось {quantity} {unit} (порог: {threshold})',
                    'date': date_added, 'item_id': item_id
                })
    
    else:
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            notif_id = f"{r['status']}_{r['id']}"
            if notif_id not in st.session_state.dismissed_notifications:
                icons = {'pending':'⏳','in_work':'🔧','approved':'✅','rejected':'❌','suggested':'💡','returned':'🔄'}
                notifications.append({
                    'id': notif_id, 'type': r['status'], 'icon': icons.get(r['status'],'📋'),
                    'title': r['name'],
                    'text': f'Статус: {r["status"]}',
                    'date': r['date'], 'request_id': r['id']
                })
    
    return sorted(notifications, key=lambda x: x['date'], reverse=True)

def get_shopping_list():
    shopping = []
    
    for req in get_requests(status='in_work'):
        r = unpack_request(req)
        shopping.append({'type': 'in_work', 'icon': '🔧', 'name': r['name'], 'qty': float(r['quantity'] or 0), 
                        'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    
    for req in get_requests(status='pending'):
        r = unpack_request(req)
        shopping.append({'type': 'pending', 'icon': '📝', 'name': r['name'], 'qty': float(r['quantity'] or 0), 
                        'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    
    for item in get_low_stock_items():
        item_id = item[0]
        name = item[1]
        location = item[2] if len(item) > 2 else ""
        room = item[3] if len(item) > 3 else ""
        quantity = item[6] if len(item) > 6 else 0
        unit = item[5] if len(item) > 5 else "шт"
        threshold = item[7] if len(item) > 7 else 1
        
        shopping.append({
            'type': 'low_stock', 
            'icon': '⚠️', 
            'name': name, 
            'qty': float(quantity), 
            'unit': unit, 
            'threshold': threshold, 
            'room': room, 
            'id': item_id
        })
    
    for req in get_requests(status='approved'):
        r = unpack_request(req)
        shopping.append({'type': 'approved', 'icon': '✅', 'name': r['name'], 'qty': float(r['quantity'] or 0), 
                        'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    
    return shopping

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

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    
    notifs = get_all_notifications()
    if notifs:
        if st.sidebar.button(f"🔔 Уведомлений: {len(notifs)}", use_container_width=True):
            st.session_state.active_tab = 0
            st.rerun()
    
    if role == "admin":
        shopping = len(get_shopping_list())
        if shopping:
            if st.sidebar.button(f"🛒 К покупке: {shopping}", use_container_width=True):
                st.session_state.active_tab = 6
                st.rerun()
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    
    st.divider()
    
    if role == "admin":
        with st.form("quick_add", clear_on_submit=True):
            name = st.text_input("Название*")
            loc = st.text_input("Место*")
            rooms = get_room_names()
            room = st.selectbox("Помещение*", rooms if rooms else ["Нет помещений"])
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Кол-во", min_value=0.0, value=1.0)
            with col2:
                unit = st.selectbox("Ед.", ["шт", "л", "кг", "м", "комплект"])
            if st.form_submit_button("💾 Сохранить") and name and loc and room != "Нет помещений":
                add_item(name, loc, room, qty, unit)
                st.success(f"✅ {name} добавлен!")
                st.rerun()

# --- ЗАГОЛОВОК ---
st.title("🏭 SmartStock Pro")

# --- ВКЛАДКИ ---
tabs = st.tabs(["🔔 Уведомления", "📊 Дашборд", "🔍 Поиск", "📋 Товары", "📝 Заявки", "📤 Списания", "🛒 Покупки", "🚜 Парк", "⚙️ Управление"])

# Уведомления
with tabs[0]:
    st.markdown("## 📬 Уведомления")
    notifs = get_all_notifications()
    if notifs:
        if st.button("🗑️ Очистить все"):
            for n in notifs:
                st.session_state.dismissed_notifications.append(n['id'])
            st.rerun()
        for n in notifs:
            with st.expander(f"{n['icon']} {n['title']}", expanded=True):
                st.write(n['text'])
                if n.get('request_id') and role == 'admin' and n['icon'] == '📝':
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("🔧 В работу", key=f"w_{n['id']}"):
                            update_request_status(n['request_id'], "in_work")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    with col2:
                        if st.button("✅ Одобрить", key=f"a_{n['id']}"):
                            update_request_status(n['request_id'], "approved")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    with col3:
                        if st.button("❌ Отклонить", key=f"r_{n['id']}"):
                            update_request_status(n['request_id'], "rejected")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                if st.button("🗑️ Скрыть", key=f"d_{n['id']}"):
                    st.session_state.dismissed_notifications.append(n['id'])
                    st.rerun()
    else:
        st.success("✅ Нет уведомлений!")

# Дашборд
with tabs[1]:
    st.markdown("## 📊 Панель управления")
    stats = get_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Товаров", stats['items'])
    with col2:
        st.metric("⚠️ Заканчиваются", stats['low'])
    with col3:
        st.metric("📝 Заявок", stats['pending'])
    with col4:
        st.metric("🔧 В работе", stats['in_work'])

# Поиск
with tabs[2]:
    st.markdown("## 🔍 Поиск товаров")
    search = st.text_input("Поиск по названию, месту, помещению")
    
    if search:
        items = search_items(search)
        if items:
            st.success(f"Найдено: {len(items)}")
    else:
        items = get_all_items()
    
    if items:
        for item in items:
            qty = item[6] if len(item) > 6 else 0
            threshold = item[7] if len(item) > 7 else 1
            
            with st.expander(f"{'🔴' if qty <= threshold else '🟢'} {item[1]} — {qty} {item[5]} | {item[3]}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"📍 Место: {item[2]}")
                    st.write(f"🏠 Помещение: {item[3]}")
                    st.write(f"📦 Количество: {qty} {item[5]}")
                    st.write(f"⚠️ Порог: {threshold}")
                    st.write(f"📅 Добавлен: {item[4][:10] if item[4] else 'Н/Д'}")
                    
                    if qty <= threshold:
                        st.warning(f"⚠️ Осталось мало!")
                
                with col2:
                    photos = get_item_photos(item[0])
                    if photos:
                        main_photo = None
                        for p in photos:
                            if p[2] == 1:
                                main_photo = p
                                break
                        if main_photo and os.path.exists(main_photo[1]):
                            st.image(main_photo[1], caption=item[1], use_container_width=True)
                        else:
                            st.caption("📷 Нет фото")
                    else:
                        st.caption("📷 Нет фото")
    else:
        st.info("Ничего не найдено")

# Товары
with tabs[3]:
    st.markdown("## 📋 Все товары")
    
    all_items = get_all_items()
    total = len(all_items)
    low = len([i for i in all_items if i[6] <= i[7] and i[6] > 0])
    zero = len([i for i in all_items if i[6] == 0])
    with_photo = len([i for i in all_items if len(i) > 8 and i[8] and int(i[8]) > 0])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Всего", total)
    with col2:
        st.metric("⚠️ Заканчиваются", low, delta="критично" if low > 0 else None)
    with col3:
        st.metric("🚫 Нет в наличии", zero)
    with col4:
        st.metric("📸 С фото", with_photo)
    
    st.divider()
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("🔍 Поиск по названию, месту или помещению", placeholder="Введите запрос...")
    with col2:
        show_filter = st.selectbox("Фильтр", ["Все", "Заканчиваются", "Нет в наличии", "В наличии"])
    with col3:
        sort_by = st.selectbox("Сортировка", ["По дате (новые)", "По дате (старые)", "По названию", "По количеству"])
    
    if search:
        items = search_items(search)
    else:
        items = get_all_items()
    
    if show_filter == "Заканчиваются":
        items = [i for i in items if i[6] <= i[7] and i[6] > 0]
    elif show_filter == "Нет в наличии":
        items = [i for i in items if i[6] == 0]
    elif show_filter == "В наличии":
        items = [i for i in items if i[6] > 0]
    
    if sort_by == "По дате (новые)":
        items.sort(key=lambda x: x[4] if len(x) > 4 else "", reverse=True)
    elif sort_by == "По дате (старые)":
        items.sort(key=lambda x: x[4] if len(x) > 4 else "")
    elif sort_by == "По названию":
        items.sort(key=lambda x: x[1] if len(x) > 1 else "")
    elif sort_by == "По количеству":
        items.sort(key=lambda x: x[6] if len(x) > 6 else 0)
    
    if items:
        st.success(f"Найдено товаров: {len(items)}")
        
        items_per_page = 10
        total_pages = (len(items) - 1) // items_per_page + 1
        page = 1
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox("Страница", range(1, total_pages + 1), key="page_select")
        
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(items))
        page_items = items[start_idx:end_idx]
        
        for item in page_items:
            item_id = item[0]
            name = item[1]
            location = item[2] if len(item) > 2 else ""
            room = item[3] if len(item) > 3 else ""
            date_added = item[4] if len(item) > 4 else ""
            unit = item[5] if len(item) > 5 else "шт"
            quantity = float(item[6]) if len(item) > 6 else 0
            threshold = int(item[7]) if len(item) > 7 else 1
            photos_count = int(item[8]) if len(item) > 8 and item[8] else 0
            
            if quantity == 0:
                status_icon = "🚫"
                status_text = "Нет в наличии"
            elif quantity <= threshold:
                status_icon = "⚠️"
                status_text = f"Заканчивается (порог: {threshold})"
            else:
                status_icon = "✅"
                status_text = f"В наличии: {quantity} {unit}"
            
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"### {status_icon} {name}")
                    st.caption(f"📍 {location} | 🏠 {room} | 📅 {date_added[:10] if date_added else 'Н/Д'} | 📸 {photos_count}")
                with col2:
                    st.markdown(f"### {quantity}")
                    st.caption(unit)
                
                col1, col2 = st.columns([2, 1.5])
                
                with col1:
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
                
                with col2:
                    st.markdown("#### 📸 Фото")
                    
                    try:
                        photos = get_item_photos(item_id)
                    except:
                        photos = []
                    
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
                                col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
                                with col_nav1:
                                    if st.button("◀", key=f"prev_{item_id}", use_container_width=True):
                                        st.session_state[photo_key] = (current_idx - 1) % len(photos)
                                        st.rerun()
                                with col_nav2:
                                    st.caption(f"{current_idx + 1} / {len(photos)}")
                                with col_nav3:
                                    if st.button("▶", key=f"next_{item_id}", use_container_width=True):
                                        st.session_state[photo_key] = (current_idx + 1) % len(photos)
                                        st.rerun()
                            
                            st.image(current_photo[1], use_container_width=True)
                            if current_photo[2] == 1:
                                st.caption("⭐ Главное фото")
                    else:
                        st.info("📷 Нет фото")
                    
                    if role == "admin":
                        with st.expander("⚙️ Настройки фото", expanded=False):
                            st.markdown("**Управление фотографиями**")
                            
                            if photos and len(photos) > 0:
                                if current_idx < len(photos):
                                    current_photo = photos[current_idx]
                                    if os.path.exists(current_photo[1]):
                                        st.caption("🔄 Поворот:")
                                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                                        with col_r1:
                                            if st.button("↺ 90°", key=f"rot_l_{item_id}", use_container_width=True):
                                                try:
                                                    success, msg = rotate_photo_left(current_photo[1])
                                                    if success:
                                                        st.rerun()
                                                except:
                                                    pass
                                        with col_r2:
                                            if st.button("↻ 90°", key=f"rot_r_{item_id}", use_container_width=True):
                                                try:
                                                    success, msg = rotate_photo_right(current_photo[1])
                                                    if success:
                                                        st.rerun()
                                                except:
                                                    pass
                                        with col_r3:
                                            if st.button("180°", key=f"rot_180_{item_id}", use_container_width=True):
                                                try:
                                                    success, msg = rotate_photo_180(current_photo[1])
                                                    if success:
                                                        st.rerun()
                                                except:
                                                    pass
                                        with col_r4:
                                            if st.button("↺", key=f"rot_reset_{item_id}", use_container_width=True):
                                                try:
                                                    success, msg = rotate_photo(current_photo[1], 0)
                                                    if success:
                                                        st.rerun()
                                                except:
                                                    pass
                                        
                                        st.divider()
                                        
                                        if current_photo[2] != 1:
                                            if st.button("⭐ Сделать главным", key=f"set_main_{item_id}", use_container_width=True):
                                                try:
                                                    set_main_photo(current_photo[0])
                                                    st.rerun()
                                                except:
                                                    pass
                                        
                                        if st.button("🗑️ Удалить это фото", key=f"del_photo_{item_id}", use_container_width=True):
                                            try:
                                                delete_item_photo(current_photo[0])
                                                st.session_state[photo_key] = 0
                                                st.rerun()
                                            except:
                                                pass
                            else:
                                st.info("Нет фото для управления")
                            
                            st.divider()
                            st.caption("📤 Добавить фото:")
                            uploaded_photos = st.file_uploader(
                                "Выберите фотографии",
                                type=["jpg", "jpeg", "png"],
                                accept_multiple_files=True,
                                key=f"upload_{item_id}"
                            )
                            
                            if uploaded_photos:
                                col1, col2 = st.columns(2)
                                with col1:
                                    is_main = st.checkbox("⭐ Сделать главным", key=f"is_main_{item_id}")
                                with col2:
                                    if st.button("📤 Загрузить", key=f"save_{item_id}", use_container_width=True):
                                        if not os.path.exists("images/items"):
                                            os.makedirs("images/items")
                                        for idx, uploaded_photo in enumerate(uploaded_photos):
                                            ext = uploaded_photo.name.split('.')[-1]
                                            photo_path = f"images/items/{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}.{ext}"
                                            with open(photo_path, "wb") as f:
                                                f.write(uploaded_photo.getbuffer())
                                            add_item_photo(item_id, photo_path, is_main=(idx == 0 and is_main))
                                        st.success(f"✅ Загружено {len(uploaded_photos)} фото!")
                                        st.rerun()
                
                st.divider()
    
    else:
        st.info("📭 Склад пуст. Добавьте товары через боковую панель.")

# Заявки
with tabs[4]:
    st.markdown("## 📝 Заявки")
    
    if role == "employee":
        with st.form("req_form", clear_on_submit=True):
            st.subheader("➕ Новая заявка")
            name = st.text_input("Название*")
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Кол-во", min_value=0.1, value=1.0)
            with col2:
                unit = st.selectbox("Ед.", ["шт", "л", "кг", "м", "комплект"])
            desc = st.text_area("Описание")
            photo = st.file_uploader("Фото", type=["jpg","jpeg","png"])
            if st.form_submit_button("📤 Отправить") and name:
                photo_path = ""
                if photo:
                    ext = photo.name.split('.')[-1]
                    photo_path = f"images/req_{uuid.uuid4()}.{ext}"
                    with open(photo_path, "wb") as f:
                        f.write(photo.getbuffer())
                add_request(name, qty, unit, desc, photo_path, user_name)
                st.success("✅ Отправлено!")
                st.rerun()
        
        st.subheader("📋 Мои заявки")
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            status_text = {'pending': '⏳ На рассмотрении', 'in_work': '🔧 В работе', 
                          'approved': '✅ Выполнено', 'rejected': '❌ Отклонено',
                          'suggested': '💡 Предложено', 'returned': '🔄 Возвращено'}
            with st.expander(f"{status_text.get(r['status'], r['status'])} | {r['name']} — {r['quantity']} {r['unit']}"):
                if r['description']:
                    st.write(f"📝 Описание: {r['description']}")
                if r['admin_comment']:
                    st.write(f"💬 Комментарий: {r['admin_comment']}")
                if r['photo'] and os.path.exists(r['photo']):
                    st.image(r['photo'], caption="Фото заявки", width=200)
                st.caption(f"📅 {r['date']}")
                
                if r['status'] == 'suggested' and r['suggested_item_id']:
                    st.markdown("---")
                    st.markdown("**💡 Предложенный товар со склада:**")
                    conn = sqlite3.connect('storage.db')
                    c = conn.cursor()
                    c.execute("SELECT * FROM items WHERE id=?", (r['suggested_item_id'],))
                    item = c.fetchone()
                    conn.close()
                    if item:
                        st.write(f"📦 {item[1]} — {item[6]} {item[5]} | {item[3]} | {item[2]}")
                        if len(item) > 8 and item[8] and os.path.exists(item[8]):
                            st.image(item[8], width=200)
                        
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
    
    elif role == "admin":
        subtabs = st.tabs(["⏳ Новые", "🔧 В работе", "🔄 Возвраты", "💡 Предложенные", "✅ Готовые", "❌ Отклоненные"])
        for tab, status in zip(subtabs, ["pending", "in_work", "returned", "suggested", "approved", "rejected"]):
            with tab:
                requests_list = get_requests(status=status)
                if requests_list:
                    for req in requests_list:
                        r = unpack_request(req)
                        with st.expander(f"{r['name']} — {r['quantity']} {r['unit']} | от {r['user']} | {r['date'][:10]}"):
                            if r['description']:
                                st.write(f"📝 Описание: {r['description']}")
                            if r['admin_comment']:
                                st.write(f"💬 Комментарий: {r['admin_comment']}")
                            if r['photo'] and os.path.exists(r['photo']):
                                st.image(r['photo'], caption="Фото заявки", width=200)
                            if r['suggested_item_id']:
                                conn = sqlite3.connect('storage.db')
                                c = conn.cursor()
                                c.execute("SELECT * FROM items WHERE id=?", (r['suggested_item_id'],))
                                item = c.fetchone()
                                conn.close()
                                if item:
                                    st.write(f"💡 Предложен товар: {item[1]} — {item[6]} {item[5]} | {item[3]}")
                            
                            st.markdown("---")
                            
                            if status in ['pending', 'returned']:
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("✅ Одобрить", key=f"app_{r['id']}"):
                                        update_request_status(r['id'], "approved")
                                        st.rerun()
                                with col2:
                                    if st.button("💡 Со склада", key=f"sug_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = True
                                with col3:
                                    if st.button("❌ Отклонить", key=f"rej_{r['id']}"):
                                        update_request_status(r['id'], "rejected")
                                        st.rerun()
                                
                                if st.session_state.get(f"sug_{r['id']}"):
                                    sq = st.text_input("Поиск товара на складе", key=f"sq_{r['id']}")
                                    if sq:
                                        found = search_items(sq)
                                        if found:
                                            for item in found:
                                                st.write(f"📦 {item[1]} — {item[6]} {item[5]} | {item[3]}")
                                                if st.button("📤 Предложить", key=f"sel_{r['id']}_{item[0]}"):
                                                    update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                                    st.session_state[f"sug_{r['id']}"] = False
                                                    st.rerun()
                                    if st.button("❌ Закрыть", key=f"close_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = False
                                        st.rerun()
                            
                            elif status == 'in_work':
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ Выполнено", key=f"done_{r['id']}"):
                                        update_request_status(r['id'], "approved")
                                        st.rerun()
                                with col2:
                                    if st.button("💡 Со склада", key=f"sug_w_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = True
                                
                                if st.session_state.get(f"sug_{r['id']}"):
                                    sq = st.text_input("Поиск товара", key=f"sq_w_{r['id']}")
                                    if sq:
                                        found = search_items(sq)
                                        if found:
                                            for item in found:
                                                st.write(f"📦 {item[1]} — {item[6]} {item[5]} | {item[3]}")
                                                if st.button("📤 Предложить", key=f"sel_w_{r['id']}_{item[0]}"):
                                                    update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                                    st.session_state[f"sug_{r['id']}"] = False
                                                    st.rerun()
                                    if st.button("❌ Закрыть", key=f"close_w_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = False
                                        st.rerun()
                            
                            elif status == 'approved':
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("📦 Создать товар", key=f"create_{r['id']}"):
                                        rooms = get_room_names()
                                        if rooms:
                                            room = st.selectbox("Помещение", rooms, key=f"room_{r['id']}")
                                            loc = st.text_input("Место", key=f"loc_{r['id']}")
                                            if st.button("💾 Сохранить", key=f"save_{r['id']}") and loc:
                                                create_item_from_request(r['id'], r['name'], loc, room, r['quantity'], r['unit'])
                                                st.success(f"✅ Товар '{r['name']}' создан!")
                                                st.rerun()
                                with col2:
                                    if st.button("🗑️ Удалить", key=f"del_{r['id']}"):
                                        delete_request(r['id'])
                                        st.rerun()
                                with col3:
                                    if st.button("📋 В работу", key=f"back_{r['id']}"):
                                        update_request_status(r['id'], "in_work")
                                        st.rerun()
                else:
                    st.info(f"Нет заявок со статусом '{status}'")

# Списания
with tabs[5]:
    st.markdown("## 📤 Списания")
    if role == "admin":
        with st.form("consume"):
            items = get_all_items()
            if items:
                opts = {f"{i[1]} ({i[6]} {i[5]})": i[0] for i in items}
                sel = st.selectbox("Товар", list(opts.keys()))
                qty = st.number_input("Кол-во", min_value=0.1)
                obj = st.text_input("На что*")
                if st.form_submit_button("✅ Списать") and obj:
                    if consume_item(opts[sel], qty, obj):
                        st.success("✅ Списано!")
                        st.rerun()
                    else:
                        st.error("Недостаточно!")
    
    cons = get_all_consumption()
    if cons:
        for c in cons:
            st.write(f"📤 {c[9]} — {c[2]} {c[3]} → {c[4]} | {c[5]}")

# Список покупок
with tabs[6]:
    st.markdown("## 🛒 Список покупок")
    
    shopping = []
    for req in get_requests(status='in_work'):
        r = unpack_request(req)
        shopping.append({'type': 'in_work', 'icon': '🔧', 'name': r['name'], 'qty': float(r['quantity'] or 0), 
                        'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    for req in get_requests(status='pending'):
        r = unpack_request(req)
        shopping.append({'type': 'pending', 'icon': '📝', 'name': r['name'], 'qty': float(r['quantity'] or 0), 
                        'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    for item in get_low_stock_items():
        shopping.append({'type': 'low', 'icon': '⚠️', 'name': item[1], 'qty': float(item[6] or 0), 
                        'unit': item[5], 'threshold': item[7], 'room': item[3], 'id': item[0]})
    for req in get_requests(status='approved'):
        r = unpack_request(req)
        shopping.append({'type': 'approved', 'icon': '✅', 'name': r['name'], 'qty': float(r['quantity'] or 0), 
                        'unit': r['unit'], 'user': r['user'], 'id': r['id']})
    
    if shopping:
        in_work = len([i for i in shopping if i['type'] == 'in_work'])
        pending = len([i for i in shopping if i['type'] == 'pending'])
        low = len([i for i in shopping if i['type'] == 'low'])
        approved = len([i for i in shopping if i['type'] == 'approved'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔧 В работе", in_work)
        with col2:
            st.metric("📝 Новые", pending)
        with col3:
            st.metric("⚠️ Заканчиваются", low)
        with col4:
            st.metric("✅ К закупке", approved)
        
        st.divider()
        
        for item in shopping:
            key_prefix = f"{item['type']}_{item['id']}"
            
            with st.expander(f"{item['icon']} {item['name']} — {item['qty']} {item['unit']}"):
                if item['type'] == 'in_work':
                    st.write(f"От: {item['user']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Выполнено", key=f"done_{key_prefix}"):
                            update_request_status(item['id'], "approved")
                            st.rerun()
                    with col2:
                        if st.button("📦 Создать", key=f"create_{key_prefix}"):
                            rooms = get_room_names()
                            if rooms:
                                room = st.selectbox("Помещение", rooms, key=f"room_{key_prefix}")
                                loc = st.text_input("Место", key=f"loc_{key_prefix}")
                                if st.button("💾 Сохранить", key=f"save_{key_prefix}") and loc:
                                    create_item_from_request(item['id'], item['name'], loc, room, item['qty'], item['unit'])
                                    st.rerun()
                
                elif item['type'] == 'pending':
                    st.write(f"От: {item['user']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔧 В работу", key=f"work_{key_prefix}"):
                            update_request_status(item['id'], "in_work")
                            st.rerun()
                    with col2:
                        if st.button("✅ Одобрить", key=f"app_{key_prefix}"):
                            update_request_status(item['id'], "approved")
                            st.rerun()
                
                elif item['type'] == 'low':
                    st.write(f"📍 {item['room']} (порог: {item['threshold']})")
                    new_qty = st.number_input("Новое кол-во", value=float(item['qty']), key=f"qty_{key_prefix}")
                    if st.button("💾 Обновить", key=f"upd_{key_prefix}"):
                        update_quantity(item['id'], new_qty)
                        st.rerun()
                
                elif item['type'] == 'approved':
                    st.write(f"От: {item['user']}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📦 Создать", key=f"ca_{key_prefix}"):
                            rooms = get_room_names()
                            if rooms:
                                room = st.selectbox("Помещение", rooms, key=f"ra_{key_prefix}")
                                loc = st.text_input("Место", key=f"la_{key_prefix}")
                                if st.button("💾 Сохранить", key=f"sa_{key_prefix}") and loc:
                                    create_item_from_request(item['id'], item['name'], loc, room, item['qty'], item['unit'])
                                    st.rerun()
                    with col2:
                        if st.button("🗑️ Удалить", key=f"del_{key_prefix}"):
                            delete_request(item['id'])
                            st.rerun()
                    with col3:
                        if st.button("📋 В работу", key=f"back_{key_prefix}"):
                            update_request_status(item['id'], "in_work")
                            st.rerun()
    else:
        st.success("✅ Список покупок пуст!")

# Парк
with tabs[7]:
    st.markdown("## 🚜 Парк техники")
    if role == "admin":
        with st.form("add_eq"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Название*")
            with col2:
                num = st.text_input("Номер")
            if st.form_submit_button("Добавить") and name:
                add_equipment(name, num)
                st.rerun()
    
    for eq in get_equipment():
        with st.expander(f"🚜 {eq[1]}" + (f" (№{eq[2]})" if eq[2] else "")):
            conn = sqlite3.connect('storage.db')
            c = conn.cursor()
            c.execute("SELECT * FROM items WHERE equipment_id=?", (eq[0],))
            for item in c.fetchall():
                st.write(f"  {'🔴' if item[6] <= item[7] else '🟢'} {item[1]} — {item[6]} {item[5]}")
            conn.close()

# Управление
with tabs[8]:
    st.markdown("## ⚙️ Управление")
    if role == "admin":
        tab_a, tab_b = st.tabs(["🏠 Помещения", "💾 Бэкапы"])
        with tab_a:
            with st.form("add_room"):
                name = st.text_input("Название*")
                if st.form_submit_button("Добавить") and name:
                    add_room(name)
                    st.rerun()
        with tab_b:
            if st.button("💾 Создать бэкап"):
                import shutil
                if not os.path.exists("backups"):
                    os.makedirs("backups")
                fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2('storage.db', f"backups/{fname}")
                st.success(f"✅ Бэкап создан: {fname}")
                st.success(f"✅ Бэкап создан: {fname}")
