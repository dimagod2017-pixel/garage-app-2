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
        return True, "✅ Email отправлен"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

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

# Статусы заявок
REQUEST_STATUSES = {
    'pending': {'icon': '⏳', 'text': 'На рассмотрении'},
    'approved': {'icon': '✅', 'text': 'Одобрено'},
    'rejected': {'icon': '❌', 'text': 'Отклонено'},
    'suggested': {'icon': '💡', 'text': 'Предложено со склада'},
    'returned': {'icon': '🔄', 'text': 'Возвращено'}
}

init_db()

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.markdown(f"*{'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}*")
    
    # Счетчики-кнопки
    if role == "admin":
        pending = len(get_requests(status='pending'))
        returned = len(get_requests(status='returned'))
        low = len(get_low_stock_items())
        
        if pending:
            if st.sidebar.button(f"📝 Новые заявки: {pending}", key="btn_pending", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
        if returned:
            if st.sidebar.button(f"🔄 Возвраты: {returned}", key="btn_returned", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
        if low:
            if st.sidebar.button(f"⚠️ Заканчивается: {low}", key="btn_low", use_container_width=True):
                st.session_state.active_tab = 0
                st.session_state.show_low_stock = True
                st.rerun()
    else:
        my_reqs = get_requests(user=user_name)
        approved = [r for r in my_reqs if unpack_request(r)['status'] == 'approved' and unpack_request(r)['seen'] == 0]
        suggested = [r for r in my_reqs if unpack_request(r)['status'] == 'suggested' and unpack_request(r)['seen'] == 0]
        
        if approved:
            if st.sidebar.button(f"✅ Одобрено: {len(approved)}", key="btn_approved", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
        if suggested:
            if st.sidebar.button(f"💡 Предложено: {len(suggested)}", key="btn_suggested", use_container_width=True):
                st.session_state.active_tab = 3
                st.rerun()
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.query_params.clear()
        st.session_state.user = None
        st.rerun()
    
    st.divider()
    
    # Форма добавления (только админ)
    if role == "admin":
        st.subheader("➕ Добавить вещь")
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Название*")
            location = st.text_input("Место*")
            room = st.selectbox("Помещение*", get_room_names() if get_room_names() else ["Нет помещений"])
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

# --- УВЕДОМЛЕНИЯ НА ГЛАВНОМ ЭКРАНЕ ---
if role == "admin":
    pending_reqs = get_requests(status='pending')
    if pending_reqs:
        with st.expander(f"📝 Новые заявки ({len(pending_reqs)})", expanded=True):
            for req in pending_reqs:
                r = unpack_request(req)
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{r['name']}** — {r['quantity']} {r['unit']} от {r['user']}")
                with col2:
                    st.caption(r['date'])
                with col3:
                    if st.button("🔍 Открыть", key=f"goto_req_{r['id']}"):
                        st.session_state.active_tab = 3
                        st.rerun()
    
    returned_reqs = get_requests(status='returned')
    if returned_reqs:
        with st.expander(f"🔄 Возвращенные заявки ({len(returned_reqs)})", expanded=True):
            for req in returned_reqs:
                r = unpack_request(req)
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{r['name']}** — {r['admin_comment'][:50]}")
                with col2:
                    st.caption(r['date'])
                with col3:
                    if st.button("🔍 Открыть", key=f"goto_ret_{r['id']}"):
                        st.session_state.active_tab = 3
                        st.rerun()
    
    low_items = get_low_stock_items()
    if low_items:
        with st.expander(f"⚠️ Заканчиваются ({len(low_items)})", expanded=True):
            for item in low_items[:5]:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{item[1]}** — {item[9]} {item[10]} в {item[4]}")
                with col2:
                    st.caption(f"Порог: {item[11]}")
                with col3:
                    if st.button("📦 Пополнить", key=f"goto_low_{item[0]}"):
                        st.session_state.active_tab = 0
                        st.session_state.show_low_stock = True
                        st.rerun()

elif role == "employee":
    my_requests = get_requests(user=user_name)
    
    # Группируем по статусам
    approved_list = [r for r in my_requests if unpack_request(r)['status'] == 'approved' and unpack_request(r)['seen'] == 0]
    suggested_list = [r for r in my_requests if unpack_request(r)['status'] == 'suggested' and unpack_request(r)['seen'] == 0]
    rejected_list = [r for r in my_requests if unpack_request(r)['status'] == 'rejected']
    
    if approved_list:
        with st.expander(f"✅ Одобренные заявки ({len(approved_list)})", expanded=True):
            for req in approved_list:
                r = unpack_request(req)
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{r['name']}** — {r['quantity']} {r['unit']}")
                with col2:
                    st.caption(r['date'])
                with col3:
                    if st.button("👁️ Смотреть", key=f"goto_app_{r['id']}"):
                        mark_request_seen(r['id'])
                        st.session_state.active_tab = 3
                        st.rerun()
    
    if suggested_list:
        with st.expander(f"💡 Предложенные товары ({len(suggested_list)})", expanded=True):
            for req in suggested_list:
                r = unpack_request(req)
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{r['name']}** — предложен со склада")
                with col2:
                    st.caption(r['date'])
                with col3:
                    if st.button("👁️ Смотреть", key=f"goto_sug_{r['id']}"):
                        st.session_state.active_tab = 3
                        st.rerun()

# --- ВКЛАДКИ ---
tabs = ["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📝 Заявки"]
if st.session_state.active_tab >= len(tabs):
    st.session_state.active_tab = 0

tab1, tab2, tab3, tab4 = st.tabs(tabs)

# Вкладка 1: Поиск
with tab1:
    if st.session_state.get("show_low_stock"):
        st.warning("⚠️ Показаны заканчивающиеся товары")
        items = get_low_stock_items()
        st.session_state.show_low_stock = False
    else:
        search_query = st.text_input("🔍 Поиск по названию, категории, месту", key="search_main")
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
                    st.write(f"📅 {item[8]}")
                    if item[9] <= item[11]:
                        st.error(f"⚠️ Осталось {item[9]} {item[10]} (порог: {item[11]})")
                    else:
                        st.success(f"✅ В наличии: {item[9]} {item[10]}")
                with col2:
                    photos = [p for p in [item[6], item[7], item[13]] if p and os.path.exists(p)]
                    if photos:
                        show_photo_carousel(f"search_{item[0]}", photos)
                
                # Кнопки действий
                if role == "admin":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_qty = st.number_input("Новое кол-во", value=float(item[9]), key=f"qty_{item[0]}")
                        if st.button("💾 Обновить", key=f"upd_{item[0]}"):
                            update_quantity(item[0], new_qty)
                            st.rerun()
                    with col_b:
                        if st.button("🗑️ Удалить", key=f"del_{item[0]}"):
                            delete_item(item[0])
                            st.rerun()
    else:
        st.info("Ничего не найдено")

# Вкладка 2: Все вещи
with tab2:
    items = get_all_items()
    if items:
        for item in items:
            st.write(f"{'🔴' if item[9] <= item[11] else '🟢'} **{item[1]}** — {item[9]} {item[10]} | {item[4]} | {item[3]}")
    else:
        st.info("Склад пуст")

# Вкладка 3: Парк
with tab3:
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
            items = c.fetchall()
            conn.close()
            if items:
                for item in items:
                    st.write(f"  {'🔴' if item[9] <= item[11] else '🟢'} {item[1]} — {item[9]} {item[10]}")
            else:
                st.caption("Нет запчастей")

# Вкладка 4: Заявки
with tab4:
    st.markdown("### 📝 Заявки на пополнение")
    
    if role == "employee":
        # Форма создания
        with st.form("req_form", clear_on_submit=True):
            st.subheader("➕ Создать заявку")
            req_name = st.text_input("Название*", placeholder="Что нужно закупить?")
            col1, col2 = st.columns(2)
            with col1:
                req_qty = st.number_input("Количество", min_value=0.1, value=1.0)
            with col2:
                req_unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект", "упаковка"])
            req_desc = st.text_area("Описание", placeholder="Для чего нужно?")
            req_photo = st.file_uploader("📷 Фото", type=["jpg","jpeg","png"])
            
            if st.form_submit_button("📤 Отправить заявку"):
                if req_name:
                    photo_path = ""
                    if req_photo:
                        ext = req_photo.name.split('.')[-1]
                        photo_path = f"images/req_{uuid.uuid4()}.{ext}"
                        with open(photo_path, "wb") as f:
                            f.write(req_photo.getbuffer())
                    add_request(req_name, req_qty, req_unit, req_desc, photo_path, user_name)
                    st.success("✅ Заявка отправлена!")
                    st.rerun()
                else:
                    st.error("Укажите название!")
        
        st.divider()
        st.subheader("📋 Мои заявки")
        
        my_requests = get_requests(user=user_name)
        if my_requests:
            for req in my_requests:
                r = unpack_request(req)
                status_info = REQUEST_STATUSES.get(r['status'], {'icon': '❓', 'text': r['status']})
                
                with st.expander(f"{status_info['icon']} {r['name']} — {r['quantity']} {r['unit']} | {status_info['text']}"):
                    st.write(f"**Статус:** {status_info['text']}")
                    st.write(f"**Дата:** {r['date']}")
                    if r['description']:
                        st.write(f"**Описание:** {r['description']}")
                    if r['admin_comment']:
                        st.write(f"**Комментарий:** {r['admin_comment']}")
                    if r['photo'] and os.path.exists(r['photo']):
                        st.image(r['photo'], width=200)
                    
                    # Для предложенных товаров
                    if r['status'] == 'suggested' and r['suggested_item_id']:
                        st.markdown("---")
                        st.markdown("### 💡 Предложенный товар со склада:")
                        conn = sqlite3.connect('storage.db')
                        c = conn.cursor()
                        c.execute("SELECT * FROM items WHERE id = ?", (r['suggested_item_id'],))
                        item = c.fetchone()
                        conn.close()
                        if item:
                            show_item_card_mini(item)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Подходит", key=f"accept_{r['id']}"):
                                    mark_request_seen(r['id'])
                                    st.success("✅ Принято!")
                                    st.rerun()
                            with col2:
                                if st.button("❌ Не подходит", key=f"return_{r['id']}"):
                                    st.session_state[f"show_return_{r['id']}"] = True
                            
                            if st.session_state.get(f"show_return_{r['id']}"):
                                with st.form(f"return_form_{r['id']}"):
                                    st.warning("Укажите причину возврата:")
                                    reason = st.text_area("Причина", placeholder="Не подходит размер, модель и т.д.")
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        if st.form_submit_button("📤 Отправить на пересмотр"):
                                            return_request(r['id'], reason)
                                            st.session_state[f"show_return_{r['id']}"] = False
                                            st.success("Заявка возвращена администратору!")
                                            st.rerun()
                                    with col_b:
                                        if st.form_submit_button("❌ Отмена"):
                                            st.session_state[f"show_return_{r['id']}"] = False
                                            st.rerun()
        else:
            st.info("У вас пока нет заявок")
    
    elif role == "admin":
        # Подвкладки для админа
        admin_tabs = st.tabs(["⏳ Новые", "🔄 Возвраты", "💡 Предложенные", "✅ Одобренные", "❌ Отклоненные"])
        
        statuses = ["pending", "returned", "suggested", "approved", "rejected"]
        
        for tab, status in zip(admin_tabs, statuses):
            with tab:
                requests_list = get_requests(status=status)
                if requests_list:
                    for req in requests_list:
                        r = unpack_request(req)
                        status_info = REQUEST_STATUSES.get(r['status'], {'icon': '❓', 'text': r['status']})
                        
                        with st.expander(f"{status_info['icon']} {r['name']} — {r['quantity']} {r['unit']} | от {r['user']} | {r['date']}"):
                            st.write(f"**От:** {r['user']}")
                            st.write(f"**Статус:** {status_info['text']}")
                            if r['description']:
                                st.write(f"**Описание:** {r['description']}")
                            if r['admin_comment']:
                                st.write(f"**Комментарий:** {r['admin_comment']}")
                            if r['photo'] and os.path.exists(r['photo']):
                                st.image(r['photo'], width=200)
                            
                            # Действия для новых и возвращенных
                            if r['status'] in ['pending', 'returned']:
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("✅ Одобрить закупку", key=f"approve_{r['id']}", use_container_width=True):
                                        update_request_status(r['id'], "approved", "Заявка одобрена. Требуется закупка.")
                                        st.success("✅ Заявка одобрена!")
                                        st.rerun()
                                with col2:
                                    if st.button("💡 Предложить со склада", key=f"suggest_{r['id']}", use_container_width=True):
                                        st.session_state[f"show_suggest_{r['id']}"] = True
                                with col3:
                                    if st.button("❌ Отклонить", key=f"reject_{r['id']}", use_container_width=True):
                                        update_request_status(r['id'], "rejected", "Заявка отклонена.")
                                        st.success("❌ Заявка отклонена!")
                                        st.rerun()
                                
                                # Поиск товара для предложения
                                if st.session_state.get(f"show_suggest_{r['id']}"):
                                    st.markdown("---")
                                    st.markdown("### 🔍 Найти товар на складе")
                                    suggest_search = st.text_input("Поиск товара", key=f"search_sug_{r['id']}", placeholder="Введите название...")
                                    
                                    if suggest_search:
                                        found = search_items(suggest_search)
                                        if found:
                                            st.success(f"Найдено: {len(found)}")
                                            for item in found:
                                                with st.container():
                                                    st.markdown("---")
                                                    show_item_card_mini(item)
                                                    if st.button("📤 Предложить", key=f"select_{r['id']}_{item[0]}"):
                                                        update_request_status(r['id'], "suggested", f"Предложен товар: {item[1]}", item[0])
                                                        st.session_state[f"show_suggest_{r['id']}"] = False
                                                        st.success(f"✅ Товар '{item[1]}' предложен!")
                                                        st.rerun()
                                        else:
                                            st.warning("Ничего не найдено")
                                    
                                    if st.button("❌ Закрыть поиск", key=f"close_sug_{r['id']}"):
                                        st.session_state[f"show_suggest_{r['id']}"] = False
                                        st.rerun()
                            
                            # Для одобренных - создание товара
                            if r['status'] == 'approved':
                                if st.button("📦 Создать товар из заявки", key=f"create_{r['id']}"):
                                    st.session_state[f"show_create_{r['id']}"] = True
                                
                                if st.session_state.get(f"show_create_{r['id']}"):
                                    with st.form(f"create_form_{r['id']}"):
                                        st.markdown("### 📦 Создать товар")
                                        st.info(f"**{r['name']}** — {r['quantity']} {r['unit']}")
                                        
                                        rooms = get_room_names()
                                        if rooms:
                                            new_room = st.selectbox("Помещение*", rooms)
                                            new_location = st.text_input("Место*")
                                            new_category = st.text_input("Категория")
                                            
                                            col1, col2 = st.columns(2)
                                            with col1:
                                                if st.form_submit_button("💾 Сохранить"):
                                                    if new_location:
                                                        add_item(r['name'], new_category, new_location, new_room, 
                                                                r['description'] or "",
                                                                r['photo'] if r['photo'] and os.path.exists(r['photo']) else "",
                                                                "", r['quantity'], r['unit'], 1, "", "", None, None)
                                                        st.session_state[f"show_create_{r['id']}"] = False
                                                        st.success(f"✅ Товар '{r['name']}' создан!")
                                                        st.rerun()
                                                    else:
                                                        st.error("Укажите место!")
                                            with col2:
                                                if st.form_submit_button("❌ Отмена"):
                                                    st.session_state[f"show_create_{r['id']}"] = False
                                                    st.rerun()
                                        else:
                                            st.error("Сначала добавьте помещения!")
                            
                            # Кнопка удаления
                            if st.button("🗑️ Удалить заявку", key=f"del_req_{r['id']}"):
                                delete_request(r['id'])
                                st.success("Заявка удалена!")
                                st.rerun()
                else:
                    st.info(f"Нет заявок со статусом '{status}'")
