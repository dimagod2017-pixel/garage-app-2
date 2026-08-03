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
    st.markdown("""
        <style>
            .login-container {
                max-width: 400px; margin: 100px auto; padding: 2rem;
                background: linear-gradient(135deg, #f5f5f5, #e0e0e0);
                border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); text-align: center;
            }
            .login-title { font-size: 2.5rem; font-weight: bold; color: #2E7D32; margin-bottom: 1rem; }
            .login-icon { font-size: 3rem; margin-bottom: 1rem; }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-icon">🌿</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Мой Склад</div>', unsafe_allow_html=True)
        
        password = st.text_input("Введите пароль", type="password", key="login_password", placeholder="Пароль", label_visibility="collapsed")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔓 Войти", use_container_width=True):
                if password in USERS:
                    st.session_state.user = USERS[password]
                    st.session_state.user["password"] = password
                    st.query_params["user"] = password
                    st.rerun()
                else:
                    st.error("❌ Неверный пароль!")
        with col_b:
            if st.button("🔄 Сброс", use_container_width=True):
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.user is None:
    if "user" in st.query_params:
        saved_user = st.query_params["user"]
        if saved_user in USERS:
            st.session_state.user = USERS[saved_user]
            st.session_state.user["password"] = saved_user
    
    if st.session_state.user is None:
        login_page()
        st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "photo_index" not in st.session_state:
    st.session_state.photo_index = {}
if "show_low_stock" not in st.session_state:
    st.session_state.show_low_stock = False
if "dismissed_notifications" not in st.session_state:
    st.session_state.dismissed_notifications = []

# --- ФУНКЦИИ БД ---
def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, category TEXT, location TEXT, room TEXT,
                  description TEXT, item_photo TEXT, location_photo TEXT, date_added TEXT,
                  quantity REAL, unit TEXT, threshold INTEGER DEFAULT 1, application TEXT,
                  installed_photo TEXT, equipment_id INTEGER, unit_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, number TEXT, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS units
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, equipment_id INTEGER, date_added TEXT,
                  UNIQUE(name, equipment_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, quantity REAL, unit TEXT,
                  object_name TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending', photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity REAL, unit TEXT,
                  description TEXT, photo TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending',
                  seen INTEGER DEFAULT 0, admin_comment TEXT, suggested_item_id TEXT)''')
    
    c.execute("PRAGMA table_info(requests)")
    req_columns = [col[1] for col in c.fetchall()]
    for col_name in ['suggested_item_id', 'admin_comment', 'seen']:
        if col_name not in req_columns:
            try:
                c.execute(f"ALTER TABLE requests ADD COLUMN {col_name} " + ("INTEGER DEFAULT 0" if col_name == 'seen' else "TEXT"))
            except:
                pass
    conn.commit()
    conn.close()

def add_room(name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?,?)", (name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return True
    except:
        return False
    finally:
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

def get_equipment_by_id(eq_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment WHERE id = ?", (eq_id,))
    result = c.fetchone()
    conn.close()
    return result

def search_equipment(query):
    if not query:
        return []
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    results = []
    ql = f"%{query}%"
    c.execute("SELECT 'equipment', id, name, number, date_added, NULL, NULL FROM equipment WHERE name LIKE ? OR number LIKE ?", (ql, ql))
    results.extend(c.fetchall())
    c.execute("SELECT 'unit', e.id, e.name, e.number, e.date_added, u.name, u.id FROM units u JOIN equipment e ON u.equipment_id = e.id WHERE u.name LIKE ? OR e.name LIKE ? OR e.number LIKE ?", (ql, ql, ql))
    results.extend(c.fetchall())
    conn.close()
    return results

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

def consume_item(item_id, quantity, object_name, user="Пользователь", photo_path="", status="pending"):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id = ?", (item_id,))
    result = c.fetchone()
    if not result:
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

def get_all_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c JOIN items i ON c.item_id = i.id ORDER BY c.date DESC LIMIT 200""")
    results = c.fetchall()
    conn.close()
    return results

def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path,
               datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold, application, installed_photo_path, equipment_id, unit_id))
    conn.commit()
    conn.close()
    return item_id

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def update_item_room(item_id, new_room):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET room = ? WHERE id = ?", (new_room, item_id))
    conn.commit()
    conn.close()

def update_item_location(item_id, new_location):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET location = ? WHERE id = ?", (new_location, item_id))
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
    conn.commit()
    conn.close()

def search_items(query, room_filter=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    ql = f"%{query}%"
    base = "SELECT * FROM items WHERE name LIKE ? OR category LIKE ? OR location LIKE ? OR room LIKE ? OR description LIKE ? OR application LIKE ?"
    params = (ql,) * 6
    
    if room_filter and room_filter != "Все помещения":
        c.execute(base + " AND room = ? ORDER BY name ASC", params + (room_filter,))
    else:
        c.execute(base + " ORDER BY name ASC", params)
    
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
        c.execute("SELECT * FROM requests WHERE status = ? AND user = ? ORDER BY date DESC", (status, user))
    elif status:
        c.execute("SELECT * FROM requests WHERE status = ? ORDER BY date DESC", (status,))
    elif user:
        c.execute("SELECT * FROM requests WHERE user = ? ORDER BY date DESC", (user,))
    else:
        c.execute("SELECT * FROM requests ORDER BY date DESC")
    results = c.fetchall()
    conn.close()
    return results

def update_request_status(request_id, status, admin_comment="", suggested_item_id=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if suggested_item_id:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0, suggested_item_id=? WHERE id=?",
                  (status, admin_comment, suggested_item_id, request_id))
    else:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0 WHERE id=?",
                  (status, admin_comment, request_id))
    conn.commit()
    conn.close()

def return_request(request_id, reason=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    comment = f"Сотрудник отклонил предложение. {reason}" if reason else "Сотрудник отклонил предложение."
    c.execute("UPDATE requests SET status='returned', admin_comment=?, seen=0, suggested_item_id=NULL WHERE id=?",
              (comment, request_id))
    conn.commit()
    conn.close()

def mark_request_seen(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET seen = 1 WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

def delete_request(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

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
    st.markdown(f"**{item[1]}** — {item[9]} {item[10]} | {item[4]}")
    if item[6] and os.path.exists(item[6]):
        st.image(item[6], width=100)

def show_photo_carousel(unique_id, photos):
    if not photos:
        return
    if unique_id not in st.session_state.photo_index:
        st.session_state.photo_index[unique_id] = 0
    total = len(photos)
    idx = st.session_state.photo_index[unique_id]
    if total > 0:
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            if st.button("◀", key=f"prev_{unique_id}"):
                st.session_state.photo_index[unique_id] = (idx - 1) % total
                st.rerun()
        with col2:
            if os.path.exists(photos[idx]):
                st.image(photos[idx], use_container_width=True)
        with col3:
            if st.button("▶", key=f"next_{unique_id}"):
                st.session_state.photo_index[unique_id] = (idx + 1) % total
                st.rerun()

def get_all_notifications():
    """Собирает все уведомления"""
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
                    'detail': f'**Описание:** {r["description"] or "Нет описания"}\n**Дата:** {r["date"]}',
                    'date': r['date'], 'request_id': r['id']
                })
        
        for req in get_requests(status='returned'):
            r = unpack_request(req)
            notif_id = f"returned_{r['id']}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'returned', 'icon': '🔄',
                    'title': f'Возврат: {r["name"]}',
                    'text': r['admin_comment'][:100],
                    'detail': f'**Причина:** {r["admin_comment"]}\n**Дата:** {r["date"]}',
                    'date': r['date'], 'request_id': r['id']
                })
        
        for item in get_low_stock_items():
            notif_id = f"low_{item[0]}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'low_stock', 'icon': '⚠️',
                    'title': f'Заканчивается: {item[1]}',
                    'text': f'Осталось {item[9]} {item[10]} (порог: {item[11]})',
                    'detail': f'**Помещение:** {item[4]}\n**Место:** {item[3]}',
                    'date': item[8], 'item_id': item[0]
                })
    
    else:
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            if r['status'] == 'approved' and r['seen'] == 0:
                notif_id = f"approved_{r['id']}"
                if notif_id not in st.session_state.dismissed_notifications:
                    notifications.append({
                        'id': notif_id, 'type': 'approved', 'icon': '✅',
                        'title': f'Заявка выполнена: {r["name"]}',
                        'text': f'Одобрено {r["quantity"]} {r["unit"]}',
                        'detail': f'**Дата:** {r["date"]}',
                        'date': r['date'], 'request_id': r['id']
                    })
            
            if r['status'] == 'suggested' and r['seen'] == 0:
                notif_id = f"suggested_{r['id']}"
                if notif_id not in st.session_state.dismissed_notifications:
                    notifications.append({
                        'id': notif_id, 'type': 'suggested', 'icon': '💡',
                        'title': f'Предложен товар: {r["name"]}',
                        'text': 'Администратор предложил товар со склада',
                        'detail': f'**Дата:** {r["date"]}',
                        'date': r['date'], 'request_id': r['id']
                    })
    
    return sorted(notifications, key=lambda x: x['date'], reverse=True)

init_db()

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    
    notifications = get_all_notifications()
    total_unread = len(notifications)
    
    if total_unread > 0:
        if st.sidebar.button(f"🔔 Уведомлений: {total_unread}", key="side_notif", use_container_width=True):
            st.session_state.active_tab = 0
            st.rerun()
    
    if role == "admin":
        pending = len(get_requests(status='pending'))
        low = len(get_low_stock_items())
        if pending:
            if st.sidebar.button(f"📝 Новые заявки: {pending}", key="side_pending", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
        if low:
            if st.sidebar.button(f"⚠️ Заканчивается: {low}", key="side_low", use_container_width=True):
                st.session_state.active_tab = 1
                st.session_state.show_low_stock = True
                st.rerun()
    else:
        my_reqs = get_requests(user=user_name)
        approved = len([r for r in my_reqs if unpack_request(r)['status'] == 'approved' and unpack_request(r)['seen'] == 0])
        suggested = len([r for r in my_reqs if unpack_request(r)['status'] == 'suggested' and unpack_request(r)['seen'] == 0])
        if approved:
            if st.sidebar.button(f"✅ Одобрено: {approved}", key="side_approved", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
        if suggested:
            if st.sidebar.button(f"💡 Предложено: {suggested}", key="side_suggested", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.query_params.clear()
        st.session_state.user = None
        st.rerun()
    
    st.divider()
    
    if role == "admin":
        st.subheader("➕ Добавить вещь")
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Название*")
            location = st.text_input("Место*")
            rooms = get_room_names()
            room = st.selectbox("Помещение*", rooms if rooms else ["Нет помещений"])
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Кол-во", min_value=0.0, value=1.0)
            with col2:
                unit = st.selectbox("Ед.", ["шт", "л", "кг", "м", "комплект"])
            if st.form_submit_button("💾 Сохранить") and name and location and room != "Нет помещений":
                add_item(name, "", location, room, "", "", "", qty, unit, 1, "", "", None, None)
                st.success(f"✅ {name} добавлен!")
                st.rerun()

# --- ЗАГОЛОВОК ---
st.title("🌿 Мой Склад")

# --- ВКЛАДКИ (Уведомления на первом месте) ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔔 Уведомления", "🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📝 Заявки", "📤 Списания"])

# Вкладка 1: Уведомления (теперь первая)
with tab1:
    st.markdown("## 📬 Лента уведомлений")
    
    notifications = get_all_notifications()
    
    if notifications:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Очистить все", use_container_width=True, type="primary"):
                for n in notifications:
                    st.session_state.dismissed_notifications.append(n['id'])
                st.rerun()
        
        st.divider()
        
        for n in notifications:
            with st.expander(f"{n['icon']} {n['title']}", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {n['icon']} {n['title']}")
                    st.write(n['text'])
                    st.markdown(n['detail'])
                    
                    # Кнопки действий
                    if n['type'] == 'pending' and role == 'admin':
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            if st.button("🔧 Взять в работу", key=f"work_{n['request_id']}"):
                                update_request_status(n['request_id'], "in_work", "Взято в работу администратором")
                                st.session_state.dismissed_notifications.append(n['id'])
                                st.success("✅ Взято в работу!")
                                st.rerun()
                        with col_b:
                            if st.button("✅ Одобрить", key=f"fast_app_{n['request_id']}"):
                                update_request_status(n['request_id'], "approved", "Одобрено")
                                st.session_state.dismissed_notifications.append(n['id'])
                                st.rerun()
                        with col_c:
                            if st.button("❌ Отклонить", key=f"fast_rej_{n['request_id']}"):
                                update_request_status(n['request_id'], "rejected", "Отклонено")
                                st.session_state.dismissed_notifications.append(n['id'])
                                st.rerun()
                    
                    elif n['type'] == 'returned' and role == 'admin':
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Одобрить", key=f"app_ret_{n['request_id']}"):
                                update_request_status(n['request_id'], "approved", "Одобрено повторно")
                                st.session_state.dismissed_notifications.append(n['id'])
                                st.rerun()
                        with col_b:
                            if st.button("💡 Предложить со склада", key=f"sug_ret_{n['request_id']}"):
                                st.session_state[f"sug_notif_{n['request_id']}"] = True
                        
                        if st.session_state.get(f"sug_notif_{n['request_id']}"):
                            sq = st.text_input("Поиск товара", key=f"sq_notif_{n['request_id']}")
                            if sq:
                                for item in search_items(sq):
                                    show_item_card_mini(item)
                                    if st.button("📤 Предложить", key=f"sel_notif_{n['request_id']}_{item[0]}"):
                                        update_request_status(n['request_id'], "suggested", f"Предложен: {item[1]}", item[0])
                                        st.session_state.dismissed_notifications.append(n['id'])
                                        st.session_state[f"sug_notif_{n['request_id']}"] = False
                                        st.rerun()
                    
                    elif n['type'] == 'suggested' and role == 'employee':
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Подходит", key=f"ok_notif_{n['request_id']}"):
                                mark_request_seen(n['request_id'])
                                st.session_state.dismissed_notifications.append(n['id'])
                                st.rerun()
                        with col_b:
                            if st.button("❌ Не подходит", key=f"no_notif_{n['request_id']}"):
                                st.session_state[f"ret_notif_{n['request_id']}"] = True
                        
                        if st.session_state.get(f"ret_notif_{n['request_id']}"):
                            reason = st.text_area("Причина", key=f"reason_notif_{n['request_id']}")
                            if st.button("📤 Отправить", key=f"send_ret_notif_{n['request_id']}"):
                                return_request(n['request_id'], reason)
                                st.session_state.dismissed_notifications.append(n['id'])
                                st.session_state[f"ret_notif_{n['request_id']}"] = False
                                st.rerun()
                    
                    elif n['type'] == 'approved' and role == 'employee':
                        if st.button("✅ Принять", key=f"accept_notif_{n['request_id']}"):
                            mark_request_seen(n['request_id'])
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    
                    elif n['type'] == 'low_stock' and role == 'admin':
                        if st.button("📦 Перейти к товару", key=f"goto_low_{n['item_id']}"):
                            st.session_state.active_tab = 1
                            st.rerun()
                
                with col2:
                    if st.button("🗑️ Скрыть", key=f"dismiss_{n['id']}"):
                        st.session_state.dismissed_notifications.append(n['id'])
                        st.rerun()
                    st.caption(f"📅 {n['date']}")
        
        st.divider()
        if st.button("🗑️ Очистить все уведомления", use_container_width=True):
            for n in notifications:
                st.session_state.dismissed_notifications.append(n['id'])
            st.rerun()
    else:
        st.success("✅ Нет новых уведомлений!")
        st.balloons()

# Вкладка 2: Поиск
with tab2:
    if st.session_state.get("show_low_stock"):
        st.warning("⚠️ Показаны заканчивающиеся товары")
        items = get_low_stock_items()
        st.session_state.show_low_stock = False
    else:
        search_query = st.text_input("🔍 Поиск", key="search_main")
        if search_query:
            items = search_items(search_query)
            if items:
                st.success(f"Найдено: {len(items)}")
        else:
            items = get_all_items()
    
    if items:
        for item in items:
            with st.expander(f"{'🔴' if item[9] <= item[11] else '🟢'} {item[1]} — {item[9]} {item[10]} | {item[4]}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"📍 {item[3]}")
                    if item[9] <= item[11]:
                        st.error(f"⚠️ Осталось {item[9]} {item[10]} (порог: {item[11]})")
                with col2:
                    photos = [p for p in [item[6], item[7], item[13]] if p and os.path.exists(p)]
                    if photos:
                        show_photo_carousel(f"search_{item[0]}", photos)
    else:
        st.info("Ничего не найдено")

# Вкладка 3: Все вещи
with tab3:
    items = get_all_items()
    if items:
        for item in items:
            st.write(f"{'🔴' if item[9] <= item[11] else '🟢'} **{item[1]}** — {item[9]} {item[10]} | {item[4]} | {item[3]}")
    else:
        st.info("Склад пуст")

# Вкладка 4: Парк
with tab4:
    st.markdown("### 🚜 Парк техники")
    if role == "admin":
        with st.form("add_eq"):
            col1, col2 = st.columns(2)
            with col1:
                eq_name = st.text_input("Название*")
            with col2:
                eq_num = st.text_input("Номер")
            if st.form_submit_button("Добавить") and eq_name:
                add_equipment(eq_name, eq_num)
                st.rerun()
    
    for eq in get_equipment():
        with st.expander(f"🚜 {eq[1]}" + (f" (№{eq[2]})" if eq[2] else "")):
            conn = sqlite3.connect('storage.db')
            c = conn.cursor()
            c.execute("SELECT * FROM items WHERE equipment_id = ?", (eq[0],))
            for item in c.fetchall():
                st.write(f"  {'🔴' if item[9] <= item[11] else '🟢'} {item[1]} — {item[9]} {item[10]}")
            conn.close()

# Вкладка 5: Заявки
with tab5:
    st.markdown("### 📝 Заявки на пополнение")
    
    if role == "employee":
        with st.form("req_form", clear_on_submit=True):
            st.subheader("➕ Создать заявку")
            req_name = st.text_input("Название*")
            col1, col2 = st.columns(2)
            with col1:
                req_qty = st.number_input("Количество", min_value=0.1, value=1.0)
            with col2:
                req_unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект"])
            req_desc = st.text_area("Описание")
            req_photo = st.file_uploader("Фото", type=["jpg","jpeg","png"])
            
            if st.form_submit_button("📤 Отправить") and req_name:
                photo_path = ""
                if req_photo:
                    ext = req_photo.name.split('.')[-1]
                    photo_path = f"images/req_{uuid.uuid4()}.{ext}"
                    with open(photo_path, "wb") as f:
                        f.write(req_photo.getbuffer())
                add_request(req_name, req_qty, req_unit, req_desc, photo_path, user_name)
                st.success("✅ Отправлено!")
                st.rerun()
        
        st.divider()
        st.subheader("Мои заявки")
        
        statuses_text = {
            'pending': '⏳ На рассмотрении',
            'approved': '✅ Одобрено',
            'rejected': '❌ Отклонено',
            'suggested': '💡 Предложено со склада',
            'returned': '🔄 Возвращено'
        }
        
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            with st.expander(f"{statuses_text.get(r['status'], r['status'])} | {r['name']} — {r['quantity']} {r['unit']}"):
                if r['status'] == 'suggested' and r['suggested_item_id']:
                    conn = sqlite3.connect('storage.db')
                    c = conn.cursor()
                    c.execute("SELECT * FROM items WHERE id = ?", (r['suggested_item_id'],))
                    item = c.fetchone()
                    conn.close()
                    if item:
                        show_item_card_mini(item)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Подходит", key=f"ok_{r['id']}"):
                            mark_request_seen(r['id'])
                            st.rerun()
                    with col2:
                        if st.button("❌ Не подходит", key=f"no_{r['id']}"):
                            st.session_state[f"ret_{r['id']}"] = True
                    
                    if st.session_state.get(f"ret_{r['id']}"):
                        with st.form(f"ret_form_{r['id']}"):
                            reason = st.text_area("Причина")
                            if st.form_submit_button("Отправить"):
                                return_request(r['id'], reason)
                                st.session_state[f"ret_{r['id']}"] = False
                                st.rerun()
    
    elif role == "admin":
        tabs = st.tabs(["⏳ Новые", "🔧 В работе", "🔄 Возвраты", "💡 Предложенные", "✅ Одобренные", "❌ Отклоненные"])
        
        for tab, status in zip(tabs, ["pending", "in_work", "returned", "suggested", "approved", "rejected"]):
            with tab:
                for req in get_requests(status=status):
                    r = unpack_request(req)
                    with st.expander(f"{r['name']} — {r['quantity']} {r['unit']} | {r['user']}"):
                        if r['status'] == 'pending':
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("🔧 В работу", key=f"work_{r['id']}"):
                                    update_request_status(r['id'], "in_work", "Взято в работу")
                                    st.rerun()
                            with col2:
                                if st.button("✅ Одобрить", key=f"app_{r['id']}"):
                                    update_request_status(r['id'], "approved")
                                    st.rerun()
                            with col3:
                                if st.button("💡 Со склада", key=f"sug_{r['id']}"):
                                    st.session_state[f"sug_{r['id']}"] = True
                            
                            if st.session_state.get(f"sug_{r['id']}"):
                                sq = st.text_input("Поиск товара", key=f"sq_{r['id']}")
                                if sq:
                                    for item in search_items(sq):
                                        show_item_card_mini(item)
                                        if st.button("Предложить", key=f"sel_{r['id']}_{item[0]}"):
                                            update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                            st.session_state[f"sug_{r['id']}"] = False
                                            st.rerun()
                        
                        elif r['status'] == 'in_work':
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✅ Выполнено", key=f"done_{r['id']}"):
                                    update_request_status(r['id'], "approved", "Выполнено")
                                    st.rerun()
                            with col2:
                                if st.button("💡 Со склада", key=f"sug_w_{r['id']}"):
                                    st.session_state[f"sug_{r['id']}"] = True
                            with col3:
                                if st.button("❌ Отклонить", key=f"rej_w_{r['id']}"):
                                    update_request_status(r['id'], "rejected", "Отклонено")
                                    st.rerun()
                            
                            if st.session_state.get(f"sug_{r['id']}"):
                                sq = st.text_input("Поиск товара", key=f"sq_w_{r['id']}")
                                if sq:
                                    for item in search_items(sq):
                                        show_item_card_mini(item)
                                        if st.button("Предложить", key=f"sel_w_{r['id']}_{item[0]}"):
                                            update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                            st.session_state[f"sug_{r['id']}"] = False
                                            st.rerun()
                        
                        elif r['status'] in ['returned']:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✅ Одобрить", key=f"app_r_{r['id']}"):
                                    update_request_status(r['id'], "approved")
                                    st.rerun()
                            with col2:
                                if st.button("💡 Со склада", key=f"sug_r_{r['id']}"):
                                    st.session_state[f"sug_{r['id']}"] = True
                            with col3:
                                if st.button("❌ Отклонить", key=f"rej_r_{r['id']}"):
                                    update_request_status(r['id'], "rejected")
                                    st.rerun()
                        
                        if r['status'] == 'approved':
                            if st.button("📦 Создать товар", key=f"create_{r['id']}"):
                                st.session_state[f"create_{r['id']}"] = True
                            
                            if st.session_state.get(f"create_{r['id']}"):
                                with st.form(f"create_form_{r['id']}"):
                                    rooms = get_room_names()
                                    if rooms:
                                        new_room = st.selectbox("Помещение", rooms)
                                        new_loc = st.text_input("Место*")
                                        if st.form_submit_button("Сохранить") and new_loc:
                                            add_item(r['name'], "", new_loc, new_room, "", 
                                                    r['photo'] if r['photo'] and os.path.exists(r['photo']) else "",
                                                    "", r['quantity'], r['unit'], 1, "", "", None, None)
                                            st.session_state[f"create_{r['id']}"] = False
                                            st.rerun()

# Вкладка 6: Списания
with tab6:
    st.markdown("### 📤 История списаний")
    for record in get_all_consumption():
        record_id, item_id, qty, unit, object_name, user, date, status, photo, item_name = record
        st.write(f"{'✅' if status == 'confirmed' else '⏳'} {item_name} — {qty} {unit} → {object_name} | {date}")
