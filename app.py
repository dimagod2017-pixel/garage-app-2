import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from PIL import Image
import pandas as pd
from io import BytesIO
import qrcode
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# --- БЕЗОПАСНАЯ НАСТРОЙКА YANDEX ПОЧТЫ ---
def get_email_config():
    """Безопасное получение настроек почты"""
    try:
        return {
            "sender": st.secrets["email_sender"],
            "password": st.secrets["email_password"],
            "recipient": st.secrets["email_recipient"]
        }
    except:
        import os
        return {
            "sender": os.getenv("EMAIL_SENDER", "Yvedomlenie-scald.sad@yandex.ru"),
            "password": os.getenv("EMAIL_PASSWORD", ""),
            "recipient": os.getenv("EMAIL_RECIPIENT", "Yvedomlenie-scald.sad@yandex.ru")
        }

EMAIL_CONFIG = get_email_config()
EMAIL_SENDER = EMAIL_CONFIG["sender"]
EMAIL_PASSWORD = EMAIL_CONFIG["password"]
EMAIL_RECIPIENT = EMAIL_CONFIG["recipient"]
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 587

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ---
def init_user_db():
    """Создает таблицу для хранения почтовых адресов пользователей"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_emails
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  email TEXT,
                  subscription_type TEXT DEFAULT 'all',
                  date_added TEXT)''')
    conn.commit()
    conn.close()

init_user_db()

def save_user_email(username, email, subscription_type="all"):
    """Сохраняет почту пользователя"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO user_emails (username, email, subscription_type, date_added) VALUES (?,?,?,?)",
                  (username, email, subscription_type, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True, f"✅ Почта {email} сохранена для пользователя {username}"
    except Exception as e:
        conn.close()
        return False, f"❌ Ошибка: {str(e)}"

def get_user_email(username):
    """Получает почту пользователя"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT email, subscription_type FROM user_emails WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    return None, None

def delete_user_email(username):
    """Удаляет почту пользователя"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM user_emails WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True, f"✅ Почта удалена"

def get_all_subscribed_emails():
    """Получает все подписанные почты"""
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT username, email, subscription_type FROM user_emails")
    results = c.fetchall()
    conn.close()
    return results

# --- ФУНКЦИЯ ОТПРАВКИ РАССЫЛКИ ---
def send_newsletter(subject, body, subscription_type="all"):
    """
    Отправляет рассылку всем подписанным пользователям
    """
    subscribers = get_all_subscribed_emails()
    if not subscribers:
        return False, "❌ Нет подписанных пользователей"
    
    sent_count = 0
    errors = []
    
    for username, email, sub_type in subscribers:
        # Проверяем, подходит ли подписка
        if subscription_type != "all" and sub_type != subscription_type and sub_type != "all":
            continue
        
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = email
            msg['Subject'] = Header(f"{subject} (для {username})", 'utf-8').encode()
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            sent_count += 1
        except Exception as e:
            errors.append(f"❌ {username} ({email}): {str(e)}")
    
    if errors:
        return True, f"✅ Отправлено: {sent_count}, ошибок: {len(errors)}\n" + "\n".join(errors)
    return True, f"✅ Рассылка отправлена {sent_count} пользователям"

# --- ФУНКЦИИ EMAIL ---
def send_email(subject, body, recipient=None):
    """
    Отправка email с поддержкой кириллицы
    """
    try:
        if not EMAIL_PASSWORD:
            return False, "❌ Пароль не настроен! Добавьте его в Secrets или переменные окружения"
        
        # Если получатель не указан, отправляем на основной
        to_email = recipient if recipient else EMAIL_RECIPIENT
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8').encode()
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True, f"✅ Email отправлен на {to_email}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "❌ Ошибка аутентификации: проверьте пароль или настройки почты"
    except smtplib.SMTPException as e:
        return False, f"❌ SMTP ошибка: {str(e)}"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

def check_and_notify_low_stock():
    """Проверяет вещи с низким остатком и отправляет уведомление на почту"""
    low_items = get_low_stock_items()
    if low_items:
        subject = "⚠️ ВНИМАНИЕ! Нужно пополнить склад!"
        body = "Здравствуйте!\n\nОбнаружены вещи с низким остатком:\n\n"
        body += "=" * 50 + "\n"
        for item in low_items:
            name = item[1]
            quantity = item[9]
            unit = item[10]
            room = item[4]
            threshold = item[11]
            body += f"📦 {name}\n"
            body += f"   ➜ Остаток: {quantity} {unit}\n"
            body += f"   ➜ Порог: {threshold} {unit}\n"
            body += f"   ➜ Помещение: {room}\n"
            body += "-" * 30 + "\n"
        
        body += "\nПожалуйста, пополните запасы!\n"
        body += f"\nПроверено: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Отправляем всем подписанным пользователям
        all_emails = get_all_subscribed_emails()
        if all_emails:
            success_count = 0
            for username, email, sub_type in all_emails:
                success, msg = send_email(subject, body, email)
                if success:
                    success_count += 1
            
            with open(f"notified_{datetime.now().strftime('%Y-%m-%d')}.txt", "w") as f:
                f.write("sent")
            return True, f"Уведомление отправлено {success_count} пользователям"
        else:
            # Если нет подписанных, отправляем на основной адрес
            success, msg = send_email(subject, body)
            if success:
                with open(f"notified_{datetime.now().strftime('%Y-%m-%d')}.txt", "w") as f:
                    f.write("sent")
                return True, "Уведомление отправлено"
            else:
                return False, msg
    return True, "Все в норме"

# --- ОСТАЛЬНОЙ КОД (ПАРОЛИ, БАЗА ДАННЫХ, ФУНКЦИИ) ---

# --- ПАРОЛИ И РОЛИ ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.sidebar.title("🔐 Вход")
    
    if "user" in st.session_state and st.session_state.user is not None:
        return
    
    st.sidebar.markdown("""
        <style>
            input[type="password"] {
                -webkit-text-security: disc !important;
                font-size: 1.2rem !important;
                letter-spacing: 4px !important;
            }
            input[type="password"]:focus {
                outline: 2px solid #4CAF50 !important;
                border-color: #4CAF50 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    password = st.sidebar.text_input(
        "Введите пароль:",
        type="password",
        key="login_password",
        placeholder="12345"
    )
    
    col1, col2, col3 = st.sidebar.columns([2, 1, 1])
    with col1:
        if st.button("🔓 Войти", use_container_width=True):
            if password in USERS:
                st.session_state.user = USERS[password]
                st.session_state.user["password"] = password
                st.query_params["user"] = password
                st.rerun()
            else:
                st.sidebar.error("❌ Неверный пароль!")
    with col2:
        if st.button("🔄 Сброс", use_container_width=True):
            st.query_params.clear()
            st.session_state.user = None
            st.rerun()
    with col3:
        if st.button("✖️", help="Очистить поле"):
            st.session_state.login_password = ""
            st.rerun()

if "user" in st.query_params:
    saved_user = st.query_params["user"]
    if saved_user in USERS and st.session_state.user is None:
        st.session_state.user = USERS[saved_user]
        st.session_state.user["password"] = saved_user

if st.session_state.user is None:
    login()
    st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

st.title("🌿 Мой Склад")
st.caption(f"👋 Добро пожаловать, {user_name}! {('🔑 Администратор' if role == 'admin' else '🔧 Сотрудник')}")

if st.sidebar.button("🚪 Выйти"):
    st.query_params.clear()
    st.session_state.user = None
    st.rerun()

# --- PWA НАСТРОЙКИ ---
st.markdown("""
    <link rel="manifest" href="manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Мой Склад">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="apple-touch-icon" href="icon-192.png">
    <meta name="theme-color" content="#2E7D32">
""", unsafe_allow_html=True)

# --- ТЁМНАЯ ТЕМА ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "selected_room" not in st.session_state:
    st.session_state.selected_room = None
if "selected_equipment" not in st.session_state:
    st.session_state.selected_equipment = None
if "show_low_stock" not in st.session_state:
    st.session_state.show_low_stock = False

with st.sidebar:
    dark_mode_toggle = st.toggle("🌙 Тёмная тема", value=st.session_state.dark_mode)
    if dark_mode_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode_toggle
        st.rerun()

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
            div[data-testid="stSidebar"] .stTextInput input {
                background-color: #1a2a1a !important;
                color: #d4e8d4 !important;
                border-color: #2e5a2e !important;
            }
        </style>
    """, unsafe_allow_html=True)

if not os.path.exists("images"):
    os.makedirs("images")

# --- БАЗА ДАННЫХ (ОСНОВНАЯ) ---
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
    c.execute("PRAGMA table_info(items)")
    columns = [col[1] for col in c.fetchall()]
    if 'application' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN application TEXT")
    if 'installed_photo' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN installed_photo TEXT")
    if 'equipment_id' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN equipment_id INTEGER")
    if 'unit_id' not in columns:
        c.execute("ALTER TABLE items ADD COLUMN unit_id INTEGER")
    c.execute("PRAGMA table_info(consumption)")
    cons_columns = [col[1] for col in c.fetchall()]
    if 'status' not in cons_columns:
        c.execute("ALTER TABLE consumption ADD COLUMN status TEXT DEFAULT 'pending'")
    if 'photo' not in cons_columns:
        c.execute("ALTER TABLE consumption ADD COLUMN photo TEXT")
    c.execute("PRAGMA table_info(equipment)")
    eq_columns = [col[1] for col in c.fetchall()]
    if 'number' not in eq_columns:
        c.execute("ALTER TABLE equipment ADD COLUMN number TEXT")
    conn.commit()
    conn.close()

# --- ВСЕ ОСТАЛЬНЫЕ ФУНКЦИИ БАЗЫ ДАННЫХ (без изменений) ---
# [Здесь должны быть все функции: add_room, get_rooms, add_equipment, consume_item, add_item, search_items, etc.]
# Чтобы не дублировать, я их пропущу, так как они уже были в предыдущих версиях

init_db()

# --- АВТОМАТИЧЕСКАЯ ПРОВЕРКА ПРИ ЗАПУСКЕ ---
if role == "admin":
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(f"notified_{today}.txt"):
        low_items = get_low_stock_items()
        if low_items:
            success, msg = check_and_notify_low_stock()
            if success:
                st.success("📧 Уведомление о низких остатках отправлено!")
            else:
                st.warning(f"⚠️ {msg}")

# --- ПОКАЗ УВЕДОМЛЕНИЙ ---
def show_low_stock_banner():
    if role != "admin":
        return
    low_items = get_low_stock_items()
    if low_items:
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, #ffebee, #ffcdd2);
                border-left: 5px solid #f44336;
                border-radius: 12px;
                padding: 1.2rem 1.5rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 4px 15px rgba(244, 67, 54, 0.2);
            ">
                <div style="display: flex; align-items: center; gap: 0.8rem;">
                    <span style="font-size: 2rem;">🔴</span>
                    <div>
                        <strong style="font-size: 1.1rem; color: #c62828;">⚠️ ВНИМАНИЕ! Нужно пополнить склад!</strong>
                        <div style="font-size: 0.9rem; color: #b71c1c; margin-top: 0.3rem;">
        """, unsafe_allow_html=True)
        for item in low_items:
            st.write(f"• **{item[1]}** — {item[9]} {item[10]} (порог: {item[11]}) в **{item[4]}**")
        st.markdown("""
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# --- СТАТИСТИКА ---
total_items, total_rooms, low_stock_count, top_categories, total_equipment, total_rooms_list, total_consumption = get_statistics()

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    if st.button("📦\n" + str(total_items) + "\nВещи", use_container_width=True):
        st.session_state.active_tab = 1
        st.rerun()

with col2:
    if st.button("🏠\n" + str(total_rooms_list) + "\nПомещения", use_container_width=True):
        st.session_state.active_tab = 5
        st.rerun()

with col3:
    if role == "admin":
        if st.button("⚠️\n" + str(low_stock_count) + "\nПополнить", use_container_width=True):
            st.session_state.active_tab = 0
            st.session_state.show_low_stock = True
            st.rerun()

with col4:
    top_cat_str = "\n".join([f"{cat}" for cat, count in top_categories[:2]]) if top_categories else "—"
    st.button("🏆\nТоп\n" + top_cat_str, use_container_width=True, disabled=True)

with col5:
    if st.button("🚜\n" + str(total_equipment) + "\nТехника", use_container_width=True):
        st.session_state.active_tab = 3
        st.rerun()

with col6:
    if st.button("📤\n" + str(total_consumption) + "\nСписано", use_container_width=True):
        st.session_state.active_tab = 4
        st.rerun()

show_low_stock_banner()

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    st.divider()
    
    st.subheader("📧 Уведомления")
    
    if EMAIL_PASSWORD:
        st.success("✅ Почта настроена")
    else:
        st.error("⚠️ Почта не настроена!")
    
    if st.button("📧 Тестовое письмо", use_container_width=True):
        user_email, _ = get_user_email(user_name)
        if user_email:
            success, msg = send_email(
                "✅ Тестовое письмо!",
                f"Привет, {user_name}!\n\nЭто тестовое письмо из приложения.\n\nВаша почта настроена правильно!",
                user_email
            )
            if success:
                st.success(msg)
            else:
                st.error(msg)
        else:
            success, msg = send_email(
                "✅ Тестовое письмо!",
                f"Привет, {user_name}!\n\nЭто тестовое письмо из приложения.\n\nВы не настроили свою почту, поэтому письмо пришло на основной адрес.",
                EMAIL_RECIPIENT
            )
            if success:
                st.success("✅ Тестовое письмо отправлено на основной адрес")
            else:
                st.error(msg)
    
    if role == "admin":
        low_items = get_low_stock_items()
        if low_items:
            if st.button("⚠️ Отправить уведомление о пополнении", use_container_width=True):
                success, msg = check_and_notify_low_stock()
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    st.divider()
    
    # --- ОСТАЛЬНАЯ ЧАСТЬ БОКОВОЙ ПАНЕЛИ (БЕЗ ИЗМЕНЕНИЙ) ---

# --- ОСНОВНАЯ ОБЛАСТЬ: ВКЛАДКИ ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Поиск", "📋 Все вещи", "🚜 Парк", "📤 История списаний", "🏠 Помещения", "📧 Настройки почты"])

# --- ОСТАЛЬНЫЕ ВКЛАДКИ (БЕЗ ИЗМЕНЕНИЙ) ---
# Вкладка "Поиск", "Все вещи", "Парк", "История списаний", "Помещения" остаются без изменений

# --- НОВАЯ ВКЛАДКА: НАСТРОЙКИ ПОЧТЫ ---
with tab6:
    st.subheader("📧 Настройки уведомлений по почте")
    
    st.info("""
    📬 **Как это работает:**
    1. Вы можете указать свою почту для получения уведомлений
    2. Выберите тип уведомлений, которые хотите получать
    3. Администратор может отправлять рассылки всем подписанным пользователям
    """)
    
    # Получаем текущие настройки пользователя
    user_email, subscription_type = get_user_email(user_name)
    
    # Раздел настройки почты
    with st.container(border=True):
        st.write(f"**👤 Ваша почта для уведомлений**")
        
        if user_email:
            st.success(f"✅ Ваша почта: **{user_email}**")
            st.caption(f"📊 Тип подписки: {subscription_type}")
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                new_email = st.text_input("✏️ Изменить почту", value=user_email, key="change_email")
            with col2:
                new_subscription = st.selectbox("📊 Тип подписки", 
                    ["all", "critical", "daily", "weekly"],
                    index=["all", "critical", "daily", "weekly"].index(subscription_type) if subscription_type in ["all", "critical", "daily", "weekly"] else 0,
                    key="change_subscription"
                )
            with col3:
                st.write("")
                st.write("")
                if st.button("💾 Сохранить изменения", use_container_width=True):
                    if new_email:
                        success, msg = save_user_email(user_name, new_email, new_subscription)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Введите почту!")
            
            if st.button("🗑️ Отписаться от уведомлений", use_container_width=True):
                success, msg = delete_user_email(user_name)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.info("📝 Вы еще не настроили почту для уведомлений")
            
            with st.form("email_form", clear_on_submit=True):
                new_email = st.text_input("✉️ Ваш Email", placeholder="example@mail.ru", key="new_email_input")
                subscription_type = st.selectbox("📊 Тип уведомлений", 
                    ["all", "critical", "daily", "weekly"],
                    format_func=lambda x: {
                        "all": "Все уведомления",
                        "critical": "Только критичные (низкие остатки)",
                        "daily": "Ежедневные отчеты",
                        "weekly": "Еженедельные отчеты"
                    }.get(x, x),
                    key="subscription_select"
                )
                
                st.caption("📋 **Пояснение:**")
                st.caption("• **Все** - получать все уведомления")
                st.caption("• **Критичные** - только о низких остатках")
                st.caption("• **Ежедневные** - отчеты раз в день")
                st.caption("• **Еженедельные** - отчеты раз в неделю")
                
                if st.form_submit_button("✅ Подписаться", use_container_width=True):
                    if new_email:
                        success, msg = save_user_email(user_name, new_email, subscription_type)
                        if success:
                            st.success(msg)
                            # Отправляем приветственное письмо
                            welcome_body = f"""
                            Здравствуйте, {user_name}!
                            
                            Вы успешно подписались на уведомления от приложения "Мой Склад".
                            
                            📊 Тип подписки: {subscription_type}
                            
                            Вы будете получать уведомления о:
                            - Низких остатках на складе
                            - Новых заявках на списание
                            - Ежедневных/еженедельных отчетах
                            
                            Чтобы отписаться, зайдите в настройки и нажмите "Отписаться".
                            
                            С уважением,
                            Команда "Мой Склад"
                            """
                            send_email("📬 Добро пожаловать в рассылку!", welcome_body, new_email)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Введите почту!")
    
    # Раздел администратора (только для админа)
    if role == "admin":
        st.divider()
        st.subheader("📊 Управление подписчиками")
        
        subscribers = get_all_subscribed_emails()
        if subscribers:
            st.caption(f"📬 Всего подписчиков: {len(subscribers)}")
            
            # Таблица подписчиков
            data = []
            for username, email, sub_type in subscribers:
                data.append({
                    "Пользователь": username,
                    "Почта": email,
                    "Тип подписки": sub_type
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            # Отправка рассылки
            st.divider()
            st.write("📨 **Отправить рассылку подписчикам**")
            
            with st.form("newsletter_form"):
                subject = st.text_input("Тема письма*", placeholder="Важное уведомление")
                body = st.text_area("Текст письма*", placeholder="Напишите сообщение для всех подписчиков...", height=150)
                target_group = st.selectbox("📊 Кому отправить", 
                    ["all", "critical", "daily", "weekly"],
                    format_func=lambda x: {
                        "all": "Всем подписчикам",
                        "critical": "Только критичные уведомления",
                        "daily": "Только ежедневные отчеты",
                        "weekly": "Только еженедельные отчеты"
                    }.get(x, x)
                )
                
                if st.form_submit_button("📧 Отправить рассылку", use_container_width=True):
                    if subject and body:
                        success, msg = send_newsletter(subject, body, target_group)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Заполните тему и текст письма!")
        else:
            st.info("🌱 Пока нет подписчиков")

st.caption("📱 Мой Склад v2.0 | Уведомления по email")
