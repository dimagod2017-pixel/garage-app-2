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
                border-radius: 20px; text-align: center;
            }
            .login-title { font-size: 2.5rem; font-weight: bold; color: #2E7D32; }
            .login-icon { font-size: 3rem; }
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

# --- БАЗА ДАННЫХ ---
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
    conn.commit()
    conn.close()

init_db()

# --- ФУНКЦИИ БД ---
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

def search_items(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    ql = f"%{query}%"
    c.execute("SELECT * FROM items WHERE name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ?", (ql, ql, ql, ql))
    results = c.fetchall()
    conn.close()
    return results

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
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

def add_item(name, location, room, quantity, unit):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, location, room, date_added, quantity, unit) VALUES (?,?,?,?,?,?,?)",
              (item_id, name, location, room, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit))
    conn.commit()
    conn.close()

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def consume_item(item_id, quantity, object_name, user="Пользователь"):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id = ?", (item_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return False
    current_q, unit = result
    if quantity > current_q:
        conn.close()
        return False
    new_q = current_q - quantity
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_q, item_id))
    c.execute("INSERT INTO consumption (item_id, quantity, unit, object_name, user, date) VALUES (?,?,?,?,?,?)",
              (item_id, quantity, unit, object_name, user, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return True

def get_all_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.id, c.item_id, c.quantity, c.unit, c.object_name, c.user, c.date, c.status, c.photo, i.name 
                 FROM consumption c JOIN items i ON c.item_id = i.id 
                 ORDER BY c.date DESC LIMIT 200""")
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
    st.markdown(f"**{item[1]}** — {item[9]} {item[10]} | {item[4]} | 📍 {item[3]}")
    if item[6] and os.path.exists(item[6]):
        st.image(item[6], width=100)

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
                    'detail': f'**Описание:** {r["description"] or "Нет описания"}\n**Дата:** {r["date"]}',
                    'date': r['date'], 'request_id': r['id'], 'status': 'pending'
                })
        
        for req in get_requests(status='returned'):
            r = unpack_request(req)
            notif_id = f"returned_{r['id']}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'returned', 'icon': '🔄',
                    'title': f'Возврат: {r["name"]}',
                    'text': r['admin_comment'][:100] if r['admin_comment'] else 'Без комментария',
                    'detail': f'**Причина:** {r["admin_comment"] or "Не указана"}\n**Дата:** {r["date"]}',
                    'date': r['date'], 'request_id': r['id'], 'status': 'returned'
                })
        
        for item in get_low_stock_items():
            notif_id = f"low_{item[0]}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'low_stock', 'icon': '⚠️',
                    'title': f'Заканчивается: {item[1]}',
                    'text': f'Осталось {item[9]} {item[10]} (порог: {item[11]})',
                    'detail': f'**Помещение:** {item[4]}\n**Место:** {item[3]}',
                    'date': item[8], 'item_id': item[0], 'status': 'low_stock'
                })
    
    else:
        status_configs = {
            'pending': {'icon': '⏳', 'title_prefix': 'На рассмотрении'},
            'in_work': {'icon': '🔧', 'title_prefix': 'В работе'},
            'approved': {'icon': '✅', 'title_prefix': 'Выполнено'},
            'rejected': {'icon': '❌', 'title_prefix': 'Отклонено'},
            'suggested': {'icon': '💡', 'title_prefix': 'Предложен товар'},
            'returned': {'icon': '🔄', 'title_prefix': 'Возвращено'}
        }
        
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            config = status_configs.get(r['status'], {'icon': '📋', 'title_prefix': r['status']})
            notif_id = f"{r['status']}_{r['id']}"
            
            if notif_id not in st.session_state.dismissed_notifications:
                texts = {
                    'pending': ('Заявка отправлена', 'Ожидает рассмотрения'),
                    'in_work': ('Администратор взял заявку в работу', 'В обработке'),
                    'approved': (f'Заявка выполнена: {r["quantity"]} {r["unit"]}', 'Без комментария'),
                    'rejected': ('Заявка отклонена', 'Не указана'),
                    'suggested': ('Предложен товар со склада', ''),
                    'returned': ('Заявка возвращена', 'Не указана')
                }
                text, default_comment = texts.get(r['status'], (f'Статус: {r["status"]}', ''))
                
                notifications.append({
                    'id': notif_id, 'type': r['status'], 'icon': config['icon'],
                    'title': f'{config["title_prefix"]}: {r["name"]}',
                    'text': text,
                    'detail': f'**Комментарий:** {r["admin_comment"] or default_comment}\n**Дата:** {r["date"]}',
                    'date': r['date'], 'request_id': r['id'], 'status': r['status']
                })
    
    return sorted(notifications, key=lambda x: x['date'], reverse=True)

def get_shopping_list():
    """Формирует список покупок для админа"""
    shopping_list = []
    
    # Заявки в работе
    for req in get_requests(status='in_work'):
        r = unpack_request(req)
        shopping_list.append({
            'type': 'request_in_work',
            'icon': '🔧',
            'name': r['name'],
            'quantity': r['quantity'],
            'unit': r['unit'],
            'from': r['user'],
            'date': r['date'],
            'id': r['id'],
            'description': r['description']
        })
    
    # Заявки на рассмотрении
    for req in get_requests(status='pending'):
        r = unpack_request(req)
        shopping_list.append({
            'type': 'request_pending',
            'icon': '📝',
            'name': r['name'],
            'quantity': r['quantity'],
            'unit': r['unit'],
            'from': r['user'],
            'date': r['date'],
            'id': r['id'],
            'description': r['description']
        })
    
    # Товары с низким остатком
    for item in get_low_stock_items():
        shopping_list.append({
            'type': 'low_stock',
            'icon': '⚠️',
            'name': item[1],
            'quantity': item[9],
            'unit': item[10],
            'threshold': item[11],
            'room': item[4],
            'location': item[3],
            'id': item[0]
        })
    
    # Одобренные заявки (ожидают закупки)
    for req in get_requests(status='approved'):
        r = unpack_request(req)
        shopping_list.append({
            'type': 'request_approved',
            'icon': '✅',
            'name': r['name'],
            'quantity': r['quantity'],
            'unit': r['unit'],
            'from': r['user'],
            'date': r['date'],
            'id': r['id']
        })
    
    return sorted(shopping_list, key=lambda x: x.get('date', ''), reverse=True)

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
        shopping = get_shopping_list()
        if shopping:
            if st.sidebar.button(f"📋 Список покупок: {len(shopping)}", key="side_shopping", use_container_width=True):
                st.session_state.active_tab = 6
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
                add_item(name, location, room, qty, unit)
                st.success(f"✅ {name} добавлен!")
                st.rerun()

# --- ЗАГОЛОВОК ---
st.title("🌿 Мой Склад")

# --- ВКЛАДКИ ---
if role == "admin":
    tabs = st.tabs(["🔔 Уведомления", "🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📝 Заявки", "📤 Списания", "🛒 Список покупок"])
else:
    tabs = st.tabs(["🔔 Уведомления", "🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📝 Заявки", "📤 Списания"])

# Вкладка 1: Уведомления
with tabs[0]:
    st.markdown("## 📬 Лента уведомлений")
    
    notifications = get_all_notifications()
    
    if notifications:
        if st.button("🗑️ Очистить все", key="clear_all"):
            for n in notifications:
                st.session_state.dismissed_notifications.append(n['id'])
            st.rerun()
        
        st.divider()
        
        for n in notifications:
            notif_key = f"notif_{n['type']}_{n['id']}"
            with st.expander(f"{n['icon']} {n['title']}", expanded=True):
                st.markdown(f"### {n['icon']} {n['title']}")
                st.write(n['text'])
                st.markdown(n['detail'])
                
                if n['type'] == 'pending' and role == 'admin':
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("🔧 В работу", key=f"work_{notif_key}"):
                            update_request_status(n['request_id'], "in_work", "Взято в работу")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    with col_b:
                        if st.button("✅ Одобрить", key=f"app_{notif_key}"):
                            update_request_status(n['request_id'], "approved", "Одобрено")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    with col_c:
                        if st.button("❌ Отклонить", key=f"rej_{notif_key}"):
                            update_request_status(n['request_id'], "rejected", "Отклонено")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                
                elif n['type'] == 'suggested' and role == 'employee':
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✅ Подходит", key=f"ok_{notif_key}"):
                            mark_request_seen(n['request_id'])
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    with col_b:
                        if st.button("❌ Не подходит", key=f"no_{notif_key}"):
                            st.session_state[f"ret_{n['request_id']}"] = True
                    
                    if st.session_state.get(f"ret_{n['request_id']}"):
                        reason = st.text_area("Причина", key=f"reason_{n['request_id']}")
                        if st.button("📤 Отправить", key=f"send_{n['request_id']}"):
                            return_request(n['request_id'], reason)
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.session_state[f"ret_{n['request_id']}"] = False
                            st.rerun()
                
                elif n['type'] in ['approved', 'rejected', 'in_work', 'returned', 'pending'] and role == 'employee':
                    if st.button("👁️ Понятно", key=f"seen_{notif_key}"):
                        st.session_state.dismissed_notifications.append(n['id'])
                        st.rerun()
                
                if st.button("🗑️ Скрыть", key=f"dismiss_{notif_key}"):
                    st.session_state.dismissed_notifications.append(n['id'])
                    st.rerun()
                st.caption(f"📅 {n['date']}")
    else:
        st.success("✅ Нет новых уведомлений!")
        st.balloons()

# Вкладка 2: Поиск
with tabs[1]:
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
                st.write(f"📍 {item[3]}")
    else:
        st.info("Ничего не найдено")

# Вкладка 3: Все вещи
with tabs[2]:
    items = get_all_items()
    if items:
        for item in items:
            st.write(f"{'🔴' if item[9] <= item[11] else '🟢'} **{item[1]}** — {item[9]} {item[10]} | {item[4]} | {item[3]}")
    else:
        st.info("Склад пуст")

# Вкладка 4: Парк
with tabs[3]:
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
with tabs[4]:
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
            'approved': '✅ Выполнено',
            'rejected': '❌ Отклонено',
            'suggested': '💡 Предложено',
            'returned': '🔄 Возвращено',
            'in_work': '🔧 В работе'
        }
        
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            req_key = f"emp_{r['status']}_{r['id']}"
            with st.expander(f"{statuses_text.get(r['status'], r['status'])} | {r['name']} — {r['quantity']} {r['unit']}"):
                if r['description']:
                    st.write(f"Описание: {r['description']}")
                if r['admin_comment']:
                    st.write(f"Комментарий: {r['admin_comment']}")
                
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
                        if st.button("✅ Подходит", key=f"ok_{req_key}"):
                            mark_request_seen(r['id'])
                            st.rerun()
                    with col2:
                        if st.button("❌ Не подходит", key=f"no_{req_key}"):
                            st.session_state[f"ret_{r['id']}"] = True
                    
                    if st.session_state.get(f"ret_{r['id']}"):
                        with st.form(f"ret_form_{req_key}"):
                            reason = st.text_area("Причина")
                            if st.form_submit_button("Отправить"):
                                return_request(r['id'], reason)
                                st.session_state[f"ret_{r['id']}"] = False
                                st.rerun()
    
    elif role == "admin":
        subtabs = st.tabs(["⏳ Новые", "🔧 В работе", "🔄 Возвраты", "💡 Предложенные", "✅ Выполненные", "❌ Отклоненные"])
        
        for tab, status in zip(subtabs, ["pending", "in_work", "returned", "suggested", "approved", "rejected"]):
            with tab:
                for req in get_requests(status=status):
                    r = unpack_request(req)
                    req_key = f"adm_{status}_{r['id']}"
                    with st.expander(f"{r['name']} — {r['quantity']} {r['unit']} | {r['user']} | {r['date']}"):
                        if r['status'] in ['pending', 'returned']:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✅ Одобрить", key=f"app_{req_key}"):
                                    update_request_status(r['id'], "approved", "Одобрено")
                                    st.rerun()
                            with col2:
                                if st.button("💡 Со склада", key=f"sug_{req_key}"):
                                    st.session_state[f"sug_{req_key}"] = True
                            with col3:
                                if st.button("❌ Отклонить", key=f"rej_{req_key}"):
                                    update_request_status(r['id'], "rejected", "Отклонено")
                                    st.rerun()
                            
                            if st.session_state.get(f"sug_{req_key}"):
                                sq = st.text_input("Поиск товара", key=f"sq_{req_key}")
                                if sq:
                                    for item in search_items(sq):
                                        show_item_card_mini(item)
                                        if st.button("Предложить", key=f"sel_{req_key}_{item[0]}"):
                                            update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                            st.session_state[f"sug_{req_key}"] = False
                                            st.rerun()
                        
                        if r['status'] == 'in_work':
                            if st.button("✅ Выполнено", key=f"done_{req_key}"):
                                update_request_status(r['id'], "approved", "Выполнено")
                                st.rerun()
                        
                        if r['status'] == 'approved':
                            if st.button("📦 Создать товар", key=f"create_{req_key}"):
                                st.session_state[f"create_{req_key}"] = True
                            
                            if st.session_state.get(f"create_{req_key}"):
                                with st.form(f"create_form_{req_key}"):
                                    rooms = get_room_names()
                                    if rooms:
                                        new_room = st.selectbox("Помещение", rooms)
                                        new_loc = st.text_input("Место*")
                                        if st.form_submit_button("Сохранить") and new_loc:
                                            add_item(r['name'], new_loc, new_room, r['quantity'], r['unit'])
                                            st.session_state[f"create_{req_key}"] = False
                                            st.rerun()

# Вкладка 6: Списания
with tabs[5]:
    st.markdown("### 📤 История списаний")
    consumption = get_all_consumption()
    if consumption:
        for record in consumption:
            record_id, item_id, qty, unit, object_name, user, date, status, photo, item_name = record
            status_icon = "✅" if status == "confirmed" else "⏳"
            st.write(f"{status_icon} {item_name} — {qty} {unit} → {object_name} | {date}")
    else:
        st.info("История списаний пуста")

# Вкладка 7: Список покупок (только для админа)
if role == "admin":
    with tabs[6]:
        st.markdown("## 🛒 Список покупок")
        st.caption("Здесь собраны все заявки в работе и товары с низким остатком")
        
        shopping = get_shopping_list()
        
        if shopping:
            # Статистика
            in_work_count = len([s for s in shopping if s['type'] == 'request_in_work'])
            pending_count = len([s for s in shopping if s['type'] == 'request_pending'])
            low_count = len([s for s in shopping if s['type'] == 'low_stock'])
            approved_count = len([s for s in shopping if s['type'] == 'request_approved'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔧 В работе", in_work_count)
            with col2:
                st.metric("📝 Новые заявки", pending_count)
            with col3:
                st.metric("⚠️ Заканчиваются", low_count)
            with col4:
                st.metric("✅ К закупке", approved_count)
            
            st.divider()
            
            # Группировка по типу
            st.subheader("🔧 Заявки в работе")
            in_work_items = [s for s in shopping if s['type'] == 'request_in_work']
            if in_work_items:
                for item in in_work_items:
                    with st.expander(f"🔧 {item['name']} — {item['quantity']} {item['unit']} | От: {item['from']}"):
                        st.write(f"**Дата:** {item['date']}")
                        if item.get('description'):
                            st.write(f"**Описание:** {item['description']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Выполнено", key=f"shop_done_{item['id']}"):
                                update_request_status(item['id'], "approved", "Выполнено")
                                st.rerun()
                        with col2:
                            if st.button("📦 Создать товар", key=f"shop_create_{item['id']}"):
                                rooms = get_room_names()
                                if rooms:
                                    room = st.selectbox("Помещение", rooms, key=f"shop_room_{item['id']}")
                                    loc = st.text_input("Место", key=f"shop_loc_{item['id']}")
                                    if st.button("💾 Сохранить", key=f"shop_save_{item['id']}") and loc:
                                        add_item(item['name'], loc, room, item['quantity'], item['unit'])
                                        update_request_status(item['id'], "approved", "Создан товар")
                                        st.rerun()
            else:
                st.info("Нет заявок в работе")
            
            st.subheader("📝 Новые заявки")
            pending_items = [s for s in shopping if s['type'] == 'request_pending']
            if pending_items:
                for item in pending_items:
                    with st.expander(f"📝 {item['name']} — {item['quantity']} {item['unit']} | От: {item['from']}"):
                        st.write(f"**Дата:** {item['date']}")
                        if item.get('description'):
                            st.write(f"**Описание:** {item['description']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🔧 В работу", key=f"shop_work_{item['id']}"):
                                update_request_status(item['id'], "in_work", "Взято в работу")
                                st.rerun()
                        with col2:
                            if st.button("✅ Одобрить", key=f"shop_app_{item['id']}"):
                                update_request_status(item['id'], "approved", "Одобрено")
                                st.rerun()
            else:
                st.info("Нет новых заявок")
            
            st.subheader("⚠️ Товары с низким остатком")
            low_items = [s for s in shopping if s['type'] == 'low_stock']
            if low_items:
                for item in low_items:
                    with st.expander(f"⚠️ {item['name']} — {item['quantity']} {item['unit']} (порог: {item['threshold']})"):
                        st.write(f"**Помещение:** {item['room']}")
                        st.write(f"**Место:** {item['location']}")
                        new_qty = st.number_input("Новое количество", value=float(item['quantity']), key=f"shop_qty_{item['id']}")
                        if st.button("💾 Обновить количество", key=f"shop_upd_{item['id']}"):
                            update_quantity(item['id'], new_qty)
                            st.success("✅ Обновлено!")
                            st.rerun()
            else:
                st.info("Нет товаров с низким остатком")
            
            st.subheader("✅ Одобренные заявки (ожидают закупки)")
            approved_items = [s for s in shopping if s['type'] == 'request_approved']
            if approved_items:
                for item in approved_items:
                    with st.expander(f"✅ {item['name']} — {item['quantity']} {item['unit']} | От: {item['from']}"):
                        st.write(f"**Дата:** {item['date']}")
                        if st.button("📦 Создать товар", key=f"shop_create_app_{item['id']}"):
                            rooms = get_room_names()
                            if rooms:
                                room = st.selectbox("Помещение", rooms, key=f"shop_room_app_{item['id']}")
                                loc = st.text_input("Место", key=f"shop_loc_app_{item['id']}")
                                if st.button("💾 Сохранить", key=f"shop_save_app_{item['id']}") and loc:
                                    add_item(item['name'], loc, room, item['quantity'], item['unit'])
                                    st.success("✅ Товар создан!")
                                    st.rerun()
            else:
                st.info("Нет одобренных заявок")
            
            # Экспорт списка покупок
            st.divider()
            if st.button("📥 Экспортировать список покупок в Excel"):
                data = []
                for item in shopping:
                    data.append({
                        'Тип': item['icon'],
                        'Название': item['name'],
                        'Количество': item['quantity'],
                        'Ед. изм.': item['unit'],
                        'От кого/Где': item.get('from', item.get('room', '')),
                        'Дата': item.get('date', '')
                    })
                df = pd.DataFrame(data)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Список покупок')
                st.download_button(
                    label="⬇️ Скачать Excel",
                    data=output.getvalue(),
                    file_name=f"список_покупок_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.success("✅ Список покупок пуст! Все товары в наличии и нет активных заявок.")
            st.balloons()
