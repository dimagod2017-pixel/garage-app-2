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
import hashlib

# --- НАСТРОЙКИ ---
DB_PATH = "storage.db"
IMAGES_DIR = "images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Пароли теперь хешируются, а не хранятся в открытом виде
def hash_password(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

USERS_HASHED = {
    hash_password("12345"): {"role": "admin", "name": "Администратор"},
    hash_password("1111"): {"role": "employee", "name": "Сотрудник"},
}

EMAIL_SENDER = "Yvedomlenie-scald.sad@yandex.ru"
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
        # В продакшене пароль лучше брать из переменных окружения, не в коде
        server.login(EMAIL_SENDER, st.secrets.get("yandex_smtp_password", "ТВОЙ_ПАРОЛЬ_ОТ_ПОЧТЫ"))
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error("Ошибка отправки почты (настройте SMTP и секреты).")
        return False

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
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

# --- ФУНКЦИИ БД (без изменений логики, только более безопасные) ---
def add_room(name):
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM rooms ORDER BY name")
    names = [row[0] for row in c.fetchall()]
    conn.close()
    return names

def add_equipment(name, number=""):
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM equipment ORDER BY name")
    results = c.fetchall()
    conn.close()
    return results

def search_items(query, category=None, room=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ql = f"%{query}%"
    where_parts = []
    params = []
    
    where_parts.append("(name LIKE ? OR category LIKE ? OR location LIKE ? OR description LIKE ?)")
    params.extend([ql, ql, ql, ql])
    
    if category:
        where_parts.append("category = ?")
        params.append(category)
    if room:
        where_parts.append("room = ?")
        params.append(room)
    
    query_str = "SELECT * FROM items WHERE " + " AND ".join(where_parts)
    c.execute(query_str, params)
    results = c.fetchall()
    conn.close()
    return results

def get_all_items():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM items ORDER BY date_added DESC")
    results = c.fetchall()
    conn.close()
    return results

def get_low_stock_items():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM items WHERE quantity <= threshold ORDER BY quantity ASC")
    results = c.fetchall()
    conn.close()
    return results

def add_item(name, location, room, quantity, unit, category="", application=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, category, location, room, date_added, quantity, unit, application) VALUES (?,?,?,?,?,?,?,?,?)",
              (item_id, name, category, location, room, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, application))
    conn.commit()
    conn.close()

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def consume_item(item_id, quantity, object_name, user="Пользователь"):
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT c.id, c.item_id, c.quantity, c.unit, c.object_name, c.user, c.date, c.status, c.photo, i.name 
                 FROM consumption c JOIN items i ON c.item_id = i.id 
                 ORDER BY c.date DESC LIMIT 200""")
    results = c.fetchall()
    conn.close()
    return results

def add_request(name, quantity, unit, description, photo_path, user):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO requests (name, quantity, unit, description, photo, user, date) VALUES (?,?,?,?,?,?,?)",
              (name, quantity, unit, description, photo_path, user, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_requests(status=None, user=None):
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    comment = f"Отклонено: {reason}" if reason else "Отклонено сотрудником"
    c.execute("UPDATE requests SET status='returned', admin_comment=?, seen=0 WHERE id=?", (comment, request_id))
    conn.commit()
    conn.close()

def mark_request_seen(request_id):
    conn = sqlite3.connect(DB_PATH)
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

# --- УТИЛИТЫ UI ---
def show_item_card_mini(item):
    st.markdown(f"**{item[1]}** — {item[9]} {item[10]} | {item[4]} | 📍 {item[3]}")
    if item[6] and os.path.exists(item[6]):
        st.image(item[6], width=100, use_column_width=False)

def show_photo_modal(photo_path, caption=""):
    if photo_path and os.path.exists(photo_path):
        img = Image.open(photo_path)
        st.image(img, caption=caption, use_column_width=True)

def status_badge(status):
    icons = {
        "pending": "⏳", "in_work": "🔧", "approved": "✅",
        "rejected": "❌", "suggested": "💡", "returned": "🔄"
    }
    colors = {
        "pending": "#FF9800", "in_work": "#FFC107", "approved": "#4CAF50",
        "rejected": "#F44336", "suggested": "#2196F3", "returned": "#9E9E9E"
    }
    icon = icons.get(status, "📋")
    color = colors.get(status, "#999")
    return f"<span style='background:{color}; color:white; padding:4px 8px; border-radius:6px; font-size:0.9em;'>{icon} {status}</span>"

# --- ЛОГИН ---
if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.set_page_config(page_title="Мой Склад — Вход", page_icon="🌿", layout="centered")
    st.markdown("""
        <style>
            .login-container { max-width: 400px; margin: 100px auto; padding: 2rem; background: #f9f9f9; border: 1px solid #ddd; border-radius: 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
            .login-title { font-size: 2.2rem; font-weight: bold; color: #2E7D32; }
            .login-icon { font-size: 3rem; }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1
