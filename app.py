import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime

# --- ПОЛЬЗОВАТЕЛИ ---
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

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, location TEXT, room TEXT,
                  date_added TEXT, quantity REAL, unit TEXT, threshold INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity REAL, unit TEXT,
                  description TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending',
                  admin_comment TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, quantity REAL, unit TEXT,
                  object_name TEXT, user TEXT, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- ФУНКЦИИ ---
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
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?,?)", 
                  (name, datetime.now().strftime("%Y-%m-%d %H:%M")))
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

def add_item(name, location, room, quantity, unit):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, location, room, date_added, quantity, unit) VALUES (?,?,?,?,?,?,?)",
              (item_id, name, location, room, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit))
    conn.commit()
    conn.close()
    return item_id

def add_request(name, quantity, unit, description, user):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("INSERT INTO requests (name, quantity, unit, description, user, date) VALUES (?,?,?,?,?,?)",
              (name, quantity, unit, description, user, datetime.now().strftime("%Y-%m-%d %H:%M")))
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

def update_request_status(request_id, status, comment=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET status=?, admin_comment=? WHERE id=?", (status, comment, request_id))
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

def consume_item(item_id, quantity, object_name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id=?", (item_id,))
    result = c.fetchone()
    if not result or quantity > result[0]:
        conn.close()
        return False
    new_q = result[0] - quantity
    c.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item_id))
    c.execute("INSERT INTO consumption (item_id, quantity, unit, object_name, user, date) VALUES (?,?,?,?,?,?)",
              (item_id, quantity, result[1], object_name, user_name, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return True

def get_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("""SELECT c.*, i.name FROM consumption c JOIN items i ON c.item_id = i.id 
                     ORDER BY c.date DESC LIMIT 100""")
        return c.fetchall()
    except:
        return []

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
    conn.close()
    return stats

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    
    if role == "admin":
        pending = len(get_requests(status='pending'))
        if pending:
            st.warning(f"📝 Новых заявок: {pending}")
    
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Дашборд", "📋 Товары", "📝 Заявки", "📤 Списания", "⚙️ Управление"])

# Дашборд
with tab1:
    st.markdown("## 📊 Панель управления")
    stats = get_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 Товаров", stats['items'])
    with col2:
        st.metric("⚠️ Заканчиваются", stats['low'])
    with col3:
        st.metric("📝 Заявок", stats['pending'])

# Товары
with tab2:
    st.markdown("## 📋 Товары")
    search = st.text_input("🔍 Поиск")
    if search:
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        q = f"%{search}%"
        c.execute("SELECT * FROM items WHERE name LIKE ? OR location LIKE ?", (q, q))
        items = c.fetchall()
        conn.close()
    else:
        items = get_all_items()
    
    if items:
        for item in items:
            with st.expander(f"{'🔴' if item[6] <= item[7] else '🟢'} {item[1]} — {item[6]} {item[5]} | {item[3]}"):
                st.write(f"📍 {item[2]}")
    else:
        st.info("Ничего не найдено")

# Заявки
with tab3:
    st.markdown("## 📝 Заявки")
    
    if role == "employee":
        with st.form("req_form", clear_on_submit=True):
            name = st.text_input("Название*")
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Кол-во", min_value=0.1, value=1.0)
            with col2:
                unit = st.selectbox("Ед.", ["шт", "л", "кг", "м", "комплект"])
            if st.form_submit_button("📤 Отправить") and name:
                add_request(name, qty, unit, "", user_name)
                st.success("✅ Отправлено!")
                st.rerun()
    
    elif role == "admin":
        subtabs = st.tabs(["⏳ Новые", "🔧 В работе", "✅ Одобренные", "❌ Отклоненные"])
        
        for tab, status in zip(subtabs, ["pending", "in_work", "approved", "rejected"]):
            with tab:
                for req in get_requests(status=status):
                    r = req
                    with st.expander(f"{r[1]} — {r[2]} {r[3]} | {r[6]}"):
                        if status == "pending":
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✅ Одобрить", key=f"app_{r[0]}"):
                                    update_request_status(r[0], "approved")
                                    st.rerun()
                            with col2:
                                if st.button("🔧 В работу", key=f"work_{r[0]}"):
                                    update_request_status(r[0], "in_work")
                                    st.rerun()
                            with col3:
                                if st.button("❌ Отклонить", key=f"rej_{r[0]}"):
                                    update_request_status(r[0], "rejected")
                                    st.rerun()
                        
                        elif status == "in_work":
                            if st.button("✅ Выполнено", key=f"done_{r[0]}"):
                                update_request_status(r[0], "approved")
                                st.rerun()
                        
                        elif status == "approved":
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("📦 Создать товар", key=f"create_{r[0]}"):
                                    rooms = get_room_names()
                                    if rooms:
                                        room = st.selectbox("Помещение", rooms, key=f"room_{r[0]}")
                                        loc = st.text_input("Место", key=f"loc_{r[0]}")
                                        if st.button("💾 Сохранить", key=f"save_{r[0]}") and loc:
                                            create_item_from_request(r[0], r[1], loc, room, r[2], r[3])
                                            st.success(f"✅ Товар '{r[1]}' создан!")
                                            st.rerun()
                            with col2:
                                if st.button("🗑️ Удалить", key=f"del_{r[0]}"):
                                    delete_request(r[0])
                                    st.rerun()

# Списания
with tab4:
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
    
    cons = get_consumption()
    if cons:
        for c in cons:
            st.write(f"📤 {c[9]} — {c[2]} {c[3]} → {c[4]} | {c[5]}")

# Управление
with tab5:
    st.markdown("## ⚙️ Управление")
    if role == "admin":
        with st.form("add_room"):
            name = st.text_input("Название помещения*")
            if st.form_submit_button("Добавить") and name:
                add_room(name)
                st.rerun()
        
        rooms = get_room_names()
        if rooms:
            st.write("**Помещения:**")
            for r in rooms:
                st.write(f"🏠 {r}")
