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

# --- НАСТРОЙКА ПОЧТЫ ---
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

# --- ПОЛЬЗОВАТЕЛИ ---
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
        
        password = st.text_input("Введите пароль", type="password", placeholder="Пароль", label_visibility="collapsed")
        
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

if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Главная"
if "photo_index" not in st.session_state:
    st.session_state.photo_index = {}
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
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity REAL, unit TEXT,
                  description TEXT, photo TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending',
                  seen INTEGER DEFAULT 0, admin_comment TEXT, suggested_item_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- ФУНКЦИИ БД (сокращенные) ---
def get_room_names():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT name FROM rooms ORDER BY name")
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names

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

def search_items(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    ql = f"%{query}%"
    c.execute("SELECT * FROM items WHERE name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ?", (ql, ql, ql, ql))
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

def update_request_status(request_id, status, comment="", item_id=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if item_id:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0, suggested_item_id=? WHERE id=?",
                  (status, comment, item_id, request_id))
    else:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0 WHERE id=?", (status, comment, request_id))
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
        # Новые заявки
        for req in get_requests(status='pending'):
            r = unpack_request(req)
            notif_id = f"pending_{r['id']}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id,
                    'type': 'pending',
                    'icon': '📝',
                    'title': f'Новая заявка: {r["name"]}',
                    'text': f'От: {r["user"]} | {r["quantity"]} {r["unit"]}',
                    'detail': f'**Описание:** {r["description"] or "Нет описания"}\n**Дата:** {r["date"]}',
                    'date': r['date'],
                    'request_id': r['id']
                })
        
        # Возвращенные
        for req in get_requests(status='returned'):
            r = unpack_request(req)
            notif_id = f"returned_{r['id']}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id,
                    'type': 'returned',
                    'icon': '🔄',
                    'title': f'Возврат: {r["name"]}',
                    'text': r['admin_comment'][:100],
                    'detail': f'**Причина:** {r["admin_comment"]}\n**Дата:** {r["date"]}',
                    'date': r['date'],
                    'request_id': r['id']
                })
        
        # Заканчивающиеся товары
        for item in get_low_stock_items():
            notif_id = f"low_{item[0]}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id,
                    'type': 'low_stock',
                    'icon': '⚠️',
                    'title': f'Заканчивается: {item[1]}',
                    'text': f'Осталось {item[9]} {item[10]} (порог: {item[11]})',
                    'detail': f'**Помещение:** {item[4]}\n**Место:** {item[3]}\n**Дата добавления:** {item[8]}',
                    'date': item[8],
                    'item_id': item[0]
                })
    
    else:  # employee
        # Одобренные
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            if r['status'] == 'approved' and r['seen'] == 0:
                notif_id = f"approved_{r['id']}"
                if notif_id not in st.session_state.dismissed_notifications:
                    notifications.append({
                        'id': notif_id,
                        'type': 'approved',
                        'icon': '✅',
                        'title': f'Заявка выполнена: {r["name"]}',
                        'text': f'Одобрено {r["quantity"]} {r["unit"]}',
                        'detail': f'**Комментарий:** {r["admin_comment"] or "Без комментария"}\n**Дата:** {r["date"]}',
                        'date': r['date'],
                        'request_id': r['id']
                    })
            
            if r['status'] == 'suggested' and r['seen'] == 0:
                notif_id = f"suggested_{r['id']}"
                if notif_id not in st.session_state.dismissed_notifications:
                    notifications.append({
                        'id': notif_id,
                        'type': 'suggested',
                        'icon': '💡',
                        'title': f'Предложен товар: {r["name"]}',
                        'text': 'Администратор предложил товар со склада',
                        'detail': f'**Комментарий:** {r["admin_comment"]}\n**Дата:** {r["date"]}',
                        'date': r['date'],
                        'request_id': r['id']
                    })
    
    return sorted(notifications, key=lambda x: x['date'], reverse=True)

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.markdown(f"*{'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}*")
    st.divider()
    
    # Навигация
    pages = ["🏠 Главная", "🔍 Поиск", "📋 Все вещи", "📝 Заявки", "⚙️ Настройки"]
    st.session_state.current_page = st.radio("📱 Навигация", pages, 
                                               index=pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0)
    
    st.divider()
    
    # Счетчики
    notifications = get_all_notifications()
    total_unread = len(notifications)
    
    if total_unread > 0:
        st.warning(f"🔔 Уведомлений: {total_unread}")
    
    if role == "admin":
        pending = len(get_requests(status='pending'))
        low = len(get_low_stock_items())
        if pending:
            st.info(f"📝 Новых заявок: {pending}")
        if low:
            st.error(f"⚠️ Заканчивается: {low}")
    else:
        my_reqs = get_requests(user=user_name)
        approved = len([r for r in my_reqs if unpack_request(r)['status'] == 'approved' and unpack_request(r)['seen'] == 0])
        suggested = len([r for r in my_reqs if unpack_request(r)['status'] == 'suggested' and unpack_request(r)['seen'] == 0])
        if approved:
            st.success(f"✅ Выполнено: {approved}")
        if suggested:
            st.info(f"💡 Предложено: {suggested}")
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.query_params.clear()
        st.session_state.user = None
        st.rerun()

# --- ЗАГОЛОВОК ---
st.title("🌿 Мой Склад")

# --- СТРАНИЦА: ГЛАВНАЯ ---
if st.session_state.current_page == "🏠 Главная":
    st.markdown("## 📬 Лента уведомлений")
    
    notifications = get_all_notifications()
    
    if notifications:
        # Кнопка "Очистить все"
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Очистить все уведомления", use_container_width=True, type="primary"):
                for n in notifications:
                    st.session_state.dismissed_notifications.append(n['id'])
                st.rerun()
        
        st.divider()
        
        # Лента уведомлений
        for n in notifications:
            with st.expander(f"{n['icon']} {n['title']} — {n['text'][:50]}...", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {n['icon']} {n['title']}")
                    st.write(n['text'])
                    st.markdown(n['detail'])
                    
                    # Дополнительная информация в зависимости от типа
                    if n['type'] in ['pending', 'returned', 'approved', 'suggested']:
                        req = get_requests(status=n.get('status')) if n.get('status') else None
                        if n['type'] == 'pending' and role == 'admin':
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("🔧 Взять в работу", key=f"work_{n['request_id']}"):
                                    update_request_status(n['request_id'], "in_work", "Взято в работу")
                                    st.session_state.dismissed_notifications.append(n['id'])
                                    st.rerun()
                            with col_b:
                                if st.button("✅ Быстро одобрить", key=f"fast_app_{n['request_id']}"):
                                    update_request_status(n['request_id'], "approved", "Одобрено быстро")
                                    st.session_state.dismissed_notifications.append(n['id'])
                                    st.rerun()
                        
                        elif n['type'] == 'suggested' and role == 'employee':
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✅ Подходит", key=f"ok_{n['request_id']}"):
                                    mark_request_seen(n['request_id'])
                                    st.session_state.dismissed_notifications.append(n['id'])
                                    st.rerun()
                            with col_b:
                                if st.button("❌ Не подходит", key=f"no_{n['request_id']}"):
                                    st.session_state[f"ret_{n['request_id']}"] = True
                            
                            if st.session_state.get(f"ret_{n['request_id']}"):
                                reason = st.text_area("Причина возврата", key=f"reason_{n['request_id']}")
                                if st.button("📤 Отправить", key=f"send_ret_{n['request_id']}"):
                                    return_request(n['request_id'], reason)
                                    st.session_state.dismissed_notifications.append(n['id'])
                                    st.session_state[f"ret_{n['request_id']}"] = False
                                    st.rerun()
                        
                        elif n['type'] == 'approved' and role == 'employee':
                            if st.button("✅ Принять", key=f"accept_{n['request_id']}"):
                                mark_request_seen(n['request_id'])
                                st.session_state.dismissed_notifications.append(n['id'])
                                st.rerun()
                    
                    elif n['type'] == 'low_stock' and role == 'admin':
                        if st.button("📦 Перейти к товару", key=f"goto_{n['item_id']}"):
                            st.session_state.current_page = "🔍 Поиск"
                            st.rerun()
                
                with col2:
                    if st.button("🗑️ Скрыть", key=f"dismiss_{n['id']}"):
                        st.session_state.dismissed_notifications.append(n['id'])
                        st.rerun()
                    st.caption(f"📅 {n['date']}")
        
        # Кнопка внизу
        st.divider()
        if st.button("🗑️ Очистить все уведомления (внизу)", use_container_width=True):
            for n in notifications:
                st.session_state.dismissed_notifications.append(n['id'])
            st.rerun()
    else:
        st.success("✅ Нет новых уведомлений!")
        st.balloons()

# --- СТРАНИЦА: ПОИСК ---
elif st.session_state.current_page == "🔍 Поиск":
    st.markdown("## 🔍 Поиск товаров")
    search_query = st.text_input("Введите название, категорию или место")
    
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
                if item[6] and os.path.exists(item[6]):
                    st.image(item[6], width=200)
    else:
        st.info("Ничего не найдено")

# --- СТРАНИЦА: ВСЕ ВЕЩИ ---
elif st.session_state.current_page == "📋 Все вещи":
    st.markdown("## 📋 Все товары")
    items = get_all_items()
    if items:
        for item in items:
            st.write(f"{'🔴' if item[9] <= item[11] else '🟢'} **{item[1]}** — {item[9]} {item[10]} | {item[4]} | {item[3]}")
    else:
        st.info("Склад пуст")

# --- СТРАНИЦА: ЗАЯВКИ ---
elif st.session_state.current_page == "📝 Заявки":
    st.markdown("## 📝 Заявки на пополнение")
    
    if role == "employee":
        with st.form("req_form", clear_on_submit=True):
            st.subheader("➕ Новая заявка")
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
    
    elif role == "admin":
        tabs = st.tabs(["⏳ Новые", "💡 Предложенные", "✅ Одобренные", "❌ Отклоненные"])
        
        for tab, status in zip(tabs, ["pending", "suggested", "approved", "rejected"]):
            with tab:
                for req in get_requests(status=status):
                    r = unpack_request(req)
                    with st.expander(f"{r['name']} — {r['quantity']} {r['unit']} | {r['user']}"):
                        if r['status'] == 'pending':
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
                                sq = st.text_input("Поиск товара", key=f"sq_{r['id']}")
                                if sq:
                                    for item in search_items(sq):
                                        show_item_card_mini(item)
                                        if st.button("Предложить", key=f"sel_{r['id']}_{item[0]}"):
                                            update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                            st.session_state[f"sug_{r['id']}"] = False
                                            st.rerun()

# --- СТРАНИЦА: НАСТРОЙКИ ---
elif st.session_state.current_page == "⚙️ Настройки":
    st.markdown("## ⚙️ Настройки")
    
    if role == "admin":
        st.subheader("➕ Добавить помещение")
        with st.form("add_room_form"):
            room_name = st.text_input("Название*")
            if st.form_submit_button("Добавить") and room_name:
                if add_room(room_name):
                    st.success(f"✅ Добавлено!")
                    st.rerun()
        
        st.subheader("➕ Добавить товар")
        with st.form("add_item_form"):
            name = st.text_input("Название*")
            rooms = get_room_names()
            room = st.selectbox("Помещение*", rooms if rooms else ["Нет помещений"])
            location = st.text_input("Место*")
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Количество", min_value=0.0, value=1.0)
            with col2:
                unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект"])
            
            if st.form_submit_button("💾 Сохранить") and name and location and room != "Нет помещений":
                add_item(name, location, room, qty, unit)
                st.success(f"✅ Добавлен!")
                st.rerun()
