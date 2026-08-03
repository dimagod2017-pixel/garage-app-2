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

# Хеширование паролей (чтобы не хранить в открытом виде)
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

# Отправка писем через SMTP
def send_email(subject, body):
    try:
        smtp_pwd = st.secrets.get("yandex_smtp_password", "")
        if not smtp_pwd:
            st.warning("⚠️ SMTP не настроен: нет пароля в secrets.toml")
            return False

        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, smtp_pwd)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Ошибка отправки почты: {e}")
        return False
# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Таблица запчастей/материалов
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, category TEXT, location TEXT, room TEXT,
                  description TEXT, item_photo TEXT, location_photo TEXT, date_added TEXT,
                  quantity REAL, unit TEXT, threshold INTEGER DEFAULT 1, application TEXT,
                  installed_photo TEXT, equipment_id INTEGER, unit_id INTEGER)''')
    # Техника/оборудование
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, number TEXT, date_added TEXT)''')
    # Узлы/единицы техники (если нужно делить по агрегатам)
    c.execute('''CREATE TABLE IF NOT EXISTS units
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, equipment_id INTEGER, date_added TEXT,
                  UNIQUE(name, equipment_id))''')
    # Списания (расход материалов на объекты)
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, quantity REAL, unit TEXT,
                  object_name TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending', photo TEXT)''')
    # Помещения/зоны склада
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT)''')
    # Заявки на пополнение/выдачу
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity REAL, unit TEXT,
                  description TEXT, photo TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending',
                  seen INTEGER DEFAULT 0, admin_comment TEXT, suggested_item_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- ФУНКЦИИ РАБОТЫ С ДАННЫМИ (БД) ---

# Добавление помещения
def add_room(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?,?)",
                 (name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Если такое помещение уже есть
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

# Добавление техники
def add_equipment(name, number=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment (name, number, date_added) VALUES (?,?,?)",
                  (name, number, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
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

# Поиск позиций (с фильтрами)
def search_items(query, category=None, room=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ql = f"%{query}%"
    where_parts = []
    params = []

    # Поиск по названию, категории, месту хранения, описанию
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

# Добавление позиции на склад
def add_item(name, location, room, quantity, unit, category="", application=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("""INSERT INTO items (id, name, category, location, room, date_added, quantity, unit, application)
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (item_id, name, category, location, room, datetime.now().strftime("%Y-%m-%d %H:%M"),
               quantity, unit, application))
    conn.commit()
    conn.close()

# Изменение количества
def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()

# Списание позиции (расход)
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
    c.execute("""INSERT INTO consumption (item_id, quantity, unit, object_name, user, date)
                 VALUES (?,?,?,?,?,?)""",
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

# Заявки
def add_request(name, quantity, unit, description, photo_path, user):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO requests (name, quantity, unit, description, photo, user, date)
                 VALUES (?,?,?,?,?,?,?)""",
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
        c.execute("""UPDATE requests SET status=?, admin_comment=?, seen=0, suggested_item_id=? WHERE id=?""",
                  (status, admin_comment, suggested_item_id, request_id))
    else:
        c.execute("""UPDATE requests SET status=?, admin_comment=?, seen=0 WHERE id=?""",
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
        'id': req[0],
        'name': req[1] if len(req) > 1 else "",
        'quantity': req[2] if len(req) > 2 else 0,
        'unit': req[3] if len(req) > 3 else "",
        'description': req[4] if len(req) > 4 else "",
        'photo': req[5] if len(req) > 5 else "",
        'user': req[6] if len(req) > 6 else "",
        'date': req[7] if len(req) > 7 else "",
        'status': req[8] if len(req) > 8 else "pending",
        'seen': req[9] if len(req) > 9 else 0,
        'admin_comment': req[10] if len(req) > 10 else "",
        'suggested_item_id': req[11] if len(req) > 11 else None
    }
# --- УТИЛИТЫ ДЛЯ ОТОБРАЖЕНИЯ (UI) ---

def show_item_card_mini(item):
    """Компактная карточка позиции — удобно для списков на складе"""
    st.markdown(f"**{item[1]}** — {item[9]} {item[10]} | {item[4]} | 📍 {item[3]}")
    if item[6] and os.path.exists(item[6]):
        st.image(item[6], width=100)

def status_badge(status):
    """Красивый бейдж статуса (для заявок, списаний)"""
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

# --- ЛОГИН И СЕССИЯ ---

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
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-icon">🌿</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Мой Склад</div>', unsafe_allow_html=True)
        
        pwd = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            pwd_hash = hash_password(pwd)
            if pwd_hash in USERS_HASHED:
                st.session_state.user = USERS_HASHED[pwd_hash]
                st.rerun()
            else:
                st.error("Неверный пароль")
        
        st.markdown("</div>", unsafe_allow_html=True)

# Если пользователь ещё не вошёл — показываем страницу входа
if st.session_state.user is None:
    login_page()
    st.stop()  # Останавливаем выполнение, пока не войдёт

# --- ИНТЕРФЕЙС: ВКЛАДКИ И НАВИГАЦИЯ ---

user_role = st.session_state.user["role"]
user_name = st.session_state.user["name"]

st.set_page_config(page_title=f"Мой Склад ({user_name})", page_icon="🛠️", layout="wide")
st.title(f"🌿 Мой Склад — {user_name}")

# Боковая панель: навигация по разделам
nav = st.sidebar.selectbox("Раздел", [
    "📊 Уведомления и низкий остаток",
    "🔍 Поиск и каталог",
    "🧰 Все позиции",
    "🚜 Парк техники",
    "📝 Заявки на пополнение",
    "🔥 Списания и расход",
    "🛒 Список покупок"
])

# Вспомогательная функция: показать таблицу в виде DataFrame (удобно для экспорта)
def render_table(data, columns):
    df = pd.DataFrame(data, columns=columns)
    st.dataframe(df, use_container_width=True)
    return df

# Кнопка экспорта CSV (универсальная)
def export_csv_button(df, filename):
    csv = df.to_csv(index=False).encode("utf-8")
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Скачать CSV отчёт</a>'
    st.markdown(href, unsafe_allow_html=True)
import base64

# --- ЛОГИКА ВКЛАДОК ---

if nav == "📊 Уведомления и низкий остаток":
    st.subheader("⚠️ Низкий остаток (ниже порога)")
    low_stock = get_low_stock_items()
    if low_stock:
        cols = ["ID", "Название", "Категория", "Помещение", "Место", "Кол-во", "Ед.", "Порог", "Применение"]
        df_low = render_table(low_stock, cols)
        export_csv_button(df_low, "low_stock_report.csv")
        
        st.warning("Эти позиции требуют пополнения! Рассмотрите создание заявки.")
    else:
        st.success("✅ Все остатки выше пороговых значений.")

    st.subheader("📩 Новые заявки (требуют внимания)")
    pending_reqs = get_requests(status="pending")
    if pending_reqs:
        for req in pending_reqs:
            r = unpack_request(req)
            badge = status_badge(r["status"])
            st.markdown(f"{badge} **{r['name']}** — {r['quantity']} {r['unit']} | Пользователь: {r['user']} | Дата: {r['date']}")
            if r["description"]:
                st.caption(f"📝 {r['description']}")
            if r["photo"] and os.path.exists(r["photo"]):
                st.image(r["photo"], width=150)
            
            # Только админ может менять статусы
            if user_role == "admin":
                col1, col2, col3 = st.columns([3, 3, 4])
                with col1:
                    if st.button("✅ Одобрить", key=f"approve_{r['id']}"):
                        update_request_status(r["id"], "approved")
                        st.rerun()
                with col2:
                    if st.button("💡 Предложить позицию", key=f"suggest_{r['id']}"):
                        with st.expander("Выбрать позицию из склада"):
                            items = get_all_items()
                            item_map = {i[1]: i[0] for i in items}
                            selected = st.selectbox("Выберите позицию для предложения", list(item_map.keys()))
                            if st.button("Предложить", key=f"submit_suggest_{r['id']}"):
                                update_request_status(r["id"], "suggested", admin_comment="Предложена позиция", suggested_item_id=item_map[selected])
                                st.success("Позиция предложена!")
                                st.rerun()
                with col3:
                    reason = st.text_input("Причина отклонения", key=f"reason_{r['id']}")
                    if st.button("❌ Отклонить", key=f"reject_{r['id']}"):
                        return_request(r["id"], reason)
                        st.rerun()
            else:
                if not r["seen"]:
                    if st.button("Я видел(а)", key=f"seen_{r['id']}"):
                        mark_request_seen(r["id"])
                        st.rerun()
    else:
        st.info("Нет новых заявок.")

elif nav == "🔍 Поиск и каталог":
    st.subheader("🔎 Поиск позиций")
    query = st.text_input("Что ищем? (название, категория, место, описание)")
    category_filter = st.selectbox("Категория (опционально)", ["", "Запчасти", "Расходные материалы", "Инструменты", "Прочее"])
    room_filter = st.selectbox("Помещение (опционально)", [""] + get_room_names())
    
    results = search_items(query, category_filter, room_filter) if query else get_all_items()
    
    if results:
        cols = ["ID", "Название", "Категория", "Помещение", "Место", "Кол-во", "Ед.", "Порог", "Применение"]
        df_res = render_table(results, cols)
        export_csv_button(df_res, "search_results.csv")
    else:
        st.info("Ничего не найдено. Попробуйте другой запрос.")

elif nav == "🧰 Все позиции":
    st.subheader("📦 Все позиции на складе")
    items = get_all_items()
    if items:
        cols = ["ID", "Название", "Категория", "Помещение", "Место", "Кол-во", "Ед.", "Порог", "Применение"]
        df_items = render_table(items, cols)
        export_csv_button(df_items, "all_items.csv")
        
        # Быстрый просмотр карточек (компактно)
        st.subheader("Компактный вид (мини-карточки)")
        for item in items:
            show_item_card_mini(item)
            st.divider()
    else:
        st.info("Склад пуст. Добавьте первые позиции.")

elif nav == "🚜 Парк техники":
    st.subheader("🚜 Парк техники и оборудования")
    equipments = get_equipment()
    if equipments:
        df_eq = pd.DataFrame(equipments, columns=["ID", "Название", "Инв. номер", "Дата добавления"])
        st.dataframe(df_eq, use_container_width=True)
        
        with st.expander("Добавить технику"):
            eq_name = st.text_input("Название техники (трактор, насос и т.п.)")
            eq_number = st.text_input("Инвентарный номер (необязательно)")
            if st.button("Добавить технику"):
                if add_equipment(eq_name, eq_number):
                    st.success("Техника добавлена!")
                    st.rerun()
                else:
                    st.error("Не удалось добавить (возможно, такая техника уже есть).")
    else:
        st.info("Парк техники пуст.")
        with st.expander("Добавить первую единицу техники"):
            eq_name = st.text_input("Название техники")
            eq_number = st.text_input("Инв. номер")
            if st.button("Добавить"):
                if add_equipment(eq_name, eq_number):
                    st.success("Добавлено!")
                    st.rerun()

elif nav == "📝 Заявки на пополнение":
    st.subheader("📝 Заявки на пополнение/выдачу")
    
    with st.expander("Подать новую заявку"):
        req_name = st.text_input("Что нужно (название)")
        req_qty = st.number_input("Количество", min_value=0.01, step=0.1)
        req_unit = st.selectbox("Единица измерения", ["шт", "кг", "л", "м", "комплект"])
        req_desc = st.text_area("Описание/обоснование (где и зачем нужно)")
        uploaded_photo = st.file_uploader("Фото (опционально)", type=["jpg", "jpeg", "png"])
        
        if st.button("Отправить заявку"):
            photo_path = None
            if uploaded_photo:
                photo_path = os.path.join(IMAGES_DIR, f"{uuid.uuid4()}.png")
                with open(photo_path, "wb") as f:
                    f.write(uploaded_photo.read())
            add_request(req_name, req_qty, req_unit, req_desc, photo_path, user_name)
            st.success("Заявка отправлена!")
            st.rerun()

    # Показать все заявки пользователя
    my_requests = get_requests(user=user_name)
    if my_requests:
        st.subheader("Мои заявки")
        for req in my_requests:
            r = unpack_request(req)
            badge = status_badge(r["status"])
            st.markdown(f"{badge} **{r['name']}** — {r['quantity']} {r['unit']} | Дата: {r['date']}")
            if r["admin_comment"]:
                st.caption(f"💬 Комментарий админа: {r['admin_comment']}")
    else:
        st.info("У вас пока нет заявок.")

elif nav == "🔥 Списания и расход":
    st.subheader("🔥 Списание материалов и запчастей")
    
    items = get_all_items()
    item_map = {f"{i[1]} ({i[9]} {i[10]}, {i[3]})": i[0] for i in items}
    
    selected_item_label = st.selectbox("Выберите позицию для списания", list(item_map.keys()) if item_map else ["Нет позиций"])
    if selected_item_label != "Нет позиций":
        item_id = item_map[selected_item_label]
        consume_qty = st.number_input("Сколько списать?", min_value=0.01, step=0.1)
        object_name = st.text_input("На какой объект/агрегат (трактор, насосная станция и т.п.)", placeholder="Например: Трактор МТЗ-82 №123")
        user_comment = st.text_area("Комментарий (необязательно)", placeholder="Причина списания, вид работ и т.д.")
        
        if st.button("Списать"):
            if consume_item(item_id, consume_qty, object_name, user_name):
                st.success(f"✅ Списано {consume_qty} {selected_item_label}")
                # Можно отправить уведомление админу, если остаток стал низким
                st.rerun()
            else:
                st.error("Не удалось списать: недостаточно остатка или ошибка БД.")
    
    st.subheader("История списаний (последние 50)")
    consumptions = get_all_consumption()
    if consumptions:
        cols = ["ID", "Позиция", "Кол-во", "Ед.", "Объект", "Пользователь", "Дата", "Статус", "Фото"]
        df_cons = pd.DataFrame(consumptions, columns=cols)
        st.dataframe(df_cons, use_container_width=True)
        export_csv_button(df_cons, "consumption_history.csv")
    else:
        st.info("Пока нет списаний.")

elif nav == "🛒 Список покупок":
    # Доступен только админу
    if user_role != "admin":
        st.error("Доступ запрещён: раздел «Список покупок» только для администратора.")
    else:
        st.subheader("🛒 Список покупок (для заказа у поставщика)")
        low_stock = get_low_stock_items()
        if low_stock:
            st.info("Позиции ниже порога — кандидаты на заказ.")
            cols = ["Название", "Требуется", "Ед.", "Помещение", "Порог"]
            df_buy = pd.DataFrame([
                [i[1], max(0, i[7] - i[9]), i[10], i[3], i[7]] for i in low_stock
            ], columns=cols)
            st.dataframe(df_buy, use_container_width=True)
            export_csv_button(df_buy, "shopping_list.csv")
            
            with st.expander("Быстрое создание договора поставки (шаблон)"):
                st.write("Ниже — простой шаблон текста для письма поставщику. Можно скопировать и доработать.")
                supplier_name = st.text_input("Поставщик")
                contact_person = st.text_input("Контактное лицо")
                delivery_address = st.text_area("Адрес доставки")
                if st.button("Сгенерировать текст письма"):
                    lines = [
                        f"Поставщик: {supplier_name}",
                        f"Контактное лицо: {contact_person}",
                        f"Адрес доставки: {delivery_address}",
                        "",
                        "Прошу поставить следующие позиции:",
                        ""
                    ]
                    for i in low_stock:
                        need = max(0, i[7] - i[9])
                        if need > 0:
                            lines.append(f"- {i[1]}, {need} {i[10]} (порог: {i[7]}, остаток: {i[9]})")
                    text = "\n".join(lines)
                    st.code(text, language="text")
        else:
            st.success("Все позиции в норме. Список покупок пуст.")
