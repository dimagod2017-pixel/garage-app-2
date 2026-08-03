import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import pandas as pd
from io import BytesIO
import qrcode
import requests
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
                max-width: 400px;
                margin: 100px auto;
                padding: 2rem;
                background: linear-gradient(135deg, #f5f5f5, #e0e0e0);
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
            }
            .login-title {
                font-size: 2.5rem;
                font-weight: bold;
                color: #2E7D32;
                margin-bottom: 1rem;
            }
            .login-subtitle {
                font-size: 1.1rem;
                color: #666;
                margin-bottom: 2rem;
            }
            .login-icon {
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            input[type="password"] {
                -webkit-text-security: disc !important;
                font-size: 1.2rem !important;
                letter-spacing: 4px !important;
                text-align: center;
                padding: 10px !important;
            }
            input[type="password"]:focus {
                outline: 2px solid #4CAF50 !important;
                border-color: #4CAF50 !important;
            }
            .stButton button {
                background: linear-gradient(135deg, #4CAF50, #2E7D32) !important;
                color: white !important;
                border: none !important;
                border-radius: 10px !important;
                padding: 10px 30px !important;
                font-size: 1.1rem !important;
                font-weight: bold !important;
                transition: all 0.3s;
            }
            .stButton button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
            }
            .login-footer {
                margin-top: 1rem;
                color: #999;
                font-size: 0.8rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-icon">🌿</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Мой Склад</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Система учета запчастей и материалов</div>', unsafe_allow_html=True)
        
        password = st.text_input(
            "Введите пароль",
            type="password",
            key="login_password",
            placeholder="Введите пароль здесь",
            label_visibility="collapsed"
        )
        
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
                st.session_state.login_password = ""
                st.rerun()
        
        st.markdown('<div class="login-footer">🔐 Доступ только для авторизованных пользователей</div>', unsafe_allow_html=True)
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

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "photo_index" not in st.session_state:
    st.session_state.photo_index = {}
if "show_low_stock" not in st.session_state:
    st.session_state.show_low_stock = False

with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    
    col1, col2 = st.columns(2)
    with col1:
        dark_mode_toggle = st.toggle("🌙 Тёмная тема", value=st.session_state.dark_mode)
        if dark_mode_toggle != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode_toggle
            st.rerun()
    with col2:
        if st.button("🚪 Выйти"):
            st.query_params.clear()
            st.session_state.user = None
            st.rerun()
    
    st.divider()
    
    if role == "admin":
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM requests WHERE status = 'pending'")
            pending_count = c.fetchone()[0]
            if pending_count > 0:
                st.sidebar.warning(f"🔔 Новых заявок: {pending_count}")
        except:
            pass
        conn.close()
    else:
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM requests WHERE user = ? AND ((status = 'approved' AND seen = 0) OR (status = 'suggested' AND seen = 0))", (user_name,))
            notification_count = c.fetchone()[0]
            if notification_count > 0:
                st.sidebar.success(f"✅ Уведомлений: {notification_count}")
        except:
            pass
        conn.close()

if st.session_state.dark_mode:
    st.markdown("""
        <style>
            .stApp { background-color: #0d1a0d; color: #d4e8d4; }
            .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
                color: #d4e8d4 !important;
            }
            .stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label {
                color: #b8d9b8 !important;
            }
            .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
                background-color: #1a2a1a !important;
                color: #d4e8d4 !important;
                border-color: #2e5a2e !important;
                border-radius: 8px;
            }
            .stButton button {
                background-color: #4CAF50 !important;
                color: #ffffff !important;
                border-radius: 8px;
                font-weight: bold;
            }
            .stButton button:hover {
                background-color: #2E7D32 !important;
                color: #ffffff !important;
            }
            .stCaption, .stCaption p { color: #9acd9a !important; }
            .stInfo, .stWarning, .stError, .stSuccess {
                background-color: #1a2a1a !important;
                color: #d4e8d4 !important;
            }
            .stAlert { background-color: #1a2a1a !important; }
            .element-container, .stContainer, .stColumn { background-color: transparent !important; }
            div[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0d1a0d, #1a2a1a) !important;
                border-right: 2px solid #2e5a2e !important;
            }
            div[data-testid="stSidebar"] * { color: #d4e8d4 !important; }
        </style>
    """, unsafe_allow_html=True)

if not os.path.exists("images"):
    os.makedirs("images")

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
                  date TEXT,
                  status TEXT DEFAULT 'pending',
                  photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                  suggested_item_id TEXT)''')
    
    # Проверяем существующие колонки
    c.execute("PRAGMA table_info(requests)")
    req_columns = [col[1] for col in c.fetchall()]
    if 'suggested_item_id' not in req_columns:
        try:
            c.execute("ALTER TABLE requests ADD COLUMN suggested_item_id TEXT")
        except:
            pass
    if 'admin_comment' not in req_columns:
        try:
            c.execute("ALTER TABLE requests ADD COLUMN admin_comment TEXT")
        except:
            pass
    if 'seen' not in req_columns:
        try:
            c.execute("ALTER TABLE requests ADD COLUMN seen INTEGER DEFAULT 0")
        except:
            pass
    
    conn.commit()
    conn.close()

# Все остальные функции БД (add_room, get_rooms и т.д.) остаются без изменений
# Вставьте их сюда из предыдущего кода

def add_request(name, quantity, unit, description, photo_path, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO requests (name, quantity, unit, description, photo, user, date) VALUES (?,?,?,?,?,?,?)",
              (name, quantity, unit, description, photo_path, user, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return True

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
        c.execute("UPDATE requests SET status = ?, admin_comment = ?, seen = 0, suggested_item_id = ? WHERE id = ?", 
                  (status, admin_comment, suggested_item_id, request_id))
    else:
        c.execute("UPDATE requests SET status = ?, admin_comment = ?, seen = 0 WHERE id = ?", 
                  (status, admin_comment, request_id))
    conn.commit()
    conn.close()
    return True

def mark_request_seen(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET seen = 1 WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

def delete_request(request_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT photo FROM requests WHERE id = ?", (request_id,))
    result = c.fetchone()
    if result and result[0] and os.path.exists(result[0]):
        os.remove(result[0])
    c.execute("DELETE FROM requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

# Вспомогательная функция для безопасной распаковки заявки
def unpack_request(req):
    return {
        'id': req[0],
        'name': req[1],
        'quantity': req[2],
        'unit': req[3],
        'description': req[4] if len(req) > 4 else "",
        'photo': req[5] if len(req) > 5 else "",
        'user': req[6] if len(req) > 6 else "",
        'date': req[7] if len(req) > 7 else "",
        'status': req[8] if len(req) > 8 else "pending",
        'seen': req[9] if len(req) > 9 else 0,
        'admin_comment': req[10] if len(req) > 10 else "",
        'suggested_item_id': req[11] if len(req) > 11 else None
    }

init_db()

st.title("🌿 Мой Склад")
st.caption(f"👋 Добро пожаловать, {user_name}! {('🔑 Администратор' if role == 'admin' else '🔧 Сотрудник')}")

# Здесь должны быть все остальные функции (show_low_stock_banner, статистика, боковая панель, вкладки)
# Они остаются такими же как в предыдущем коде, но с использованием unpack_request() для заявок

# Пример использования в разделе заявок для сотрудника:
# my_requests = get_requests(user=user_name)
# if my_requests:
#     for req in my_requests:
#         r = unpack_request(req)
#         # Используйте r['id'], r['name'], r['status'] и т.д.

# Полный код слишком длинный для одного сообщения. 
# Используйте unpack_request() везде, где распаковываете заявки.
