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

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, location TEXT, room TEXT,
                  date_added TEXT, quantity REAL, unit TEXT, threshold INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, number TEXT, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity REAL, unit TEXT,
                  description TEXT, photo TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending',
                  seen INTEGER DEFAULT 0, admin_comment TEXT, suggested_item_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, quantity REAL, unit TEXT,
                  object_name TEXT, user TEXT, date TEXT)''')
    conn.commit()
    conn.close()

init_db()
# --- ФУНКЦИИ БД ---
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

def search_items(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    ql = f"%{query}%"
    c.execute("SELECT * FROM items WHERE name LIKE ? OR location LIKE ? OR room LIKE ?", (ql, ql, ql))
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
    return item_id

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

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

def get_all_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("""SELECT c.*, i.name FROM consumption c JOIN items i ON c.item_id = i.id 
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
    st.markdown(f"**{item[1]}** — {item[6]} {item[5]} | {item[3]}")
    st.caption(f"📍 {item[2]}")

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
            notif_id = f"low_{item[0]}"
            if notif_id not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': notif_id, 'type': 'low_stock', 'icon': '⚠️',
                    'title': f'Заканчивается: {item[1]}',
                    'text': f'Осталось {item[6]} {item[5]} (порог: {item[7]})',
                    'date': item[4], 'item_id': item[0]
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
    for item in [i for i in get_all_items() if i[6] <= i[7]]:
        shopping.append({'type': 'low_stock', 'icon': '⚠️', 'name': item[1], 'qty': float(item[6] or 0), 
                        'unit': item[5], 'threshold': item[7], 'room': item[3], 'id': item[0]})
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
            with st.expander(f"{'🔴' if item[6] <= item[7] else '🟢'} {item[1]} — {item[6]} {item[5]} | {item[3]}"):
                st.write(f"📍 {item[2]}")
    else:
        st.info("Ничего не найдено")

найдено")
# Товары
with tabs[3]:
    st.markdown("## 📋 Все товары")

    # CSS для карточек и модального окна
    st.markdown("""
    <style>
        .product-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
        }
        .product-card {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            background: #fff;
            padding: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .product-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        .card-status {
            font-size: 0.85rem;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            color: white;
        }
        .status-low { background-color: #d32f2f; }
        .status-ok { background-color: #2e7d32; }
        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin: 8px 0 4px;
            line-height: 1.3;
        }
        .card-meta {
            font-size: 0.9rem;
            color: #555;
            line-height: 1.4;
        }
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index:

# Товары
with tabs[3]:
    st.markdown("## 📋 Все товары")

    # CSS для карточек и модального окна
    st.markdown("""
    <style>
        .product-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
        }
        .product-card {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            background: #fff;
            padding: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .product-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        .card-status {
            font-size: 0.85rem;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            color: white;
        }
        .status-low { background-color: #d32f2f; }
        .status-ok { background-color: #2e7d32; }
        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin: 8px 0 4px;
            line-height: 1.3;
        }
        .card-meta {
            font-size: 0.9rem;
            color: #555;
            line-height: 1.4;
        }
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index:

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
                # Показываем описание заявки
                if r['description']:
                    st.write(f"📝 Описание: {r['description']}")
                # Показываем комментарий
                if r['admin_comment']:
                    st.write(f"💬 Комментарий: {r['admin_comment']}")
                # Показываем фото заявки
                if r['photo'] and os.path.exists(r['photo']):
                    st.image(r['photo'], caption="Фото заявки", width=200)
                # Показываем дату
                st.caption(f"📅 {r['date']}")
                
                # Показываем предложенный товар
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
                            # ПОКАЗЫВАЕМ ВСЮ ИНФОРМАЦИЮ О ЗАЯВКЕ
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
                            
                            # КНОПКИ ДЕЙСТВИЙ
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
