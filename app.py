import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import pandas as pd
from io import BytesIO
import qrcode
from collections import Counter
import shutil

# --- ПОЛЬЗОВАТЕЛИ ---
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>🌿 Мой Склад</h1>", unsafe_allow_html=True)
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

if "dismissed_notifications" not in st.session_state:
    st.session_state.dismissed_notifications = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id TEXT PRIMARY KEY, name TEXT, category TEXT, location TEXT, room TEXT,
                  description TEXT, item_photo TEXT, date_added TEXT,
                  quantity REAL, unit TEXT, threshold INTEGER DEFAULT 1,
                  tags TEXT, price REAL, supplier TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, number TEXT, 
                  date_added TEXT, category TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, date_added TEXT,
                  description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity REAL, unit TEXT,
                  description TEXT, photo TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending',
                  seen INTEGER DEFAULT 0, admin_comment TEXT, suggested_item_id TEXT,
                  priority TEXT DEFAULT 'normal')''')
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, quantity REAL, unit TEXT,
                  object_name TEXT, user TEXT, date TEXT, status TEXT DEFAULT 'pending')''')
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

def create_item_from_request(request_id, name, location, room, quantity, unit):
    item_id = add_item(name, location, room, quantity, unit)
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE id=?", (request_id,))
    conn.commit()
    conn.close()
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

def search_items_for_suggest(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    q = f"%{query}%"
    c.execute("SELECT * FROM items WHERE name LIKE ? OR tags LIKE ? ORDER BY name", (q, q))
    results = c.fetchall()
    conn.close()
    return results

def show_item_card_mini(item):
    st.markdown(f"**{item[1]}** — {item[6]} {item[5]} | {item[3]}")
    st.caption(f"📍 {item[2]}")

def get_shopping_list():
    shopping = []
    for req in get_requests(status='in_work'):
        shopping.append({'type': 'in_work', 'icon': '🔧', 'name': req[1], 'qty': req[2], 
                        'unit': req[3], 'user': req[6], 'id': req[0]})
    for item in [i for i in get_all_items() if i[6] <= i[7]]:
        shopping.append({'type': 'low_stock', 'icon': '⚠️', 'name': item[1], 'qty': item[6], 
                        'unit': item[5], 'threshold': item[7], 'room': item[3], 'id': item[0]})
    for req in get_requests(status='approved'):
        shopping.append({'type': 'approved', 'icon': '✅', 'name': req[1], 'qty': req[2], 
                        'unit': req[3], 'user': req[6], 'id': req[0]})
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
    c.execute("SELECT SUM(quantity * COALESCE(price, 0)) FROM items")
    stats['value'] = c.fetchone()[0] or 0
    conn.close()
    return stats

def get_notifications():
    notifs = []
    if role == "admin":
        for req in get_requests(status='pending'):
            nid = f"p_{req[0]}"
            if nid not in st.session_state.dismissed_notifications:
                notifs.append({'id': nid, 'icon': '📝', 'title': f'Заявка: {req[1]}', 
                              'text': f'{req[2]} {req[3]} от {req[6]}', 'rid': req[0]})
        for item in [i for i in get_all_items() if i[6] <= i[7]]:
            nid = f"l_{item[0]}"
            if nid not in st.session_state.dismissed_notifications:
                notifs.append({'id': nid, 'icon': '⚠️', 'title': f'Заканчивается: {item[1]}',
                              'text': f'{item[6]} {item[5]}', 'iid': item[0]})
    else:
        for req in get_requests(user=user_name):
            nid = f"{req[8]}_{req[0]}"
            if nid not in st.session_state.dismissed_notifications:
                icons = {'pending':'⏳','in_work':'🔧','approved':'✅','rejected':'❌','suggested':'💡'}
                notifs.append({'id': nid, 'icon': icons.get(req[8],'📋'), 'title': req[1],
                              'text': f'Статус: {req[8]}', 'rid': req[0]})
    return notifs

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    
    notifs = get_notifications()
    if notifs:
        if st.sidebar.button(f"🔔 Уведомлений: {len(notifs)}", use_container_width=True):
            st.session_state.active_tab = 1
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
tabs = st.tabs(["📊 Дашборд", "🔔 Уведомления", "📋 Товары", "📝 Заявки", "📤 Списания", "🛒 Покупки", "🚜 Парк", "⚙️ Управление"])

# Дашборд
with tabs[0]:
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
        st.metric("💰 Стоимость", f"{stats['value']:,.0f} ₽")

# Уведомления
with tabs[1]:
    st.markdown("## 📬 Уведомления")
    notifs = get_notifications()
    if notifs:
        if st.button("🗑️ Очистить все"):
            for n in notifs:
                st.session_state.dismissed_notifications.append(n['id'])
            st.rerun()
        for n in notifs:
            with st.expander(f"{n['icon']} {n['title']}", expanded=True):
                st.write(n['text'])
                if n.get('rid') and role == 'admin' and n['icon'] == '📝':
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("🔧 В работу", key=f"w_{n['id']}"):
                            update_request_status(n['rid'], "in_work")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    with col2:
                        if st.button("✅ Одобрить", key=f"a_{n['id']}"):
                            update_request_status(n['rid'], "approved")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                    with col3:
                        if st.button("❌ Отклонить", key=f"r_{n['id']}"):
                            update_request_status(n['rid'], "rejected")
                            st.session_state.dismissed_notifications.append(n['id'])
                            st.rerun()
                if st.button("🗑️ Скрыть", key=f"d_{n['id']}"):
                    st.session_state.dismissed_notifications.append(n['id'])
                    st.rerun()
    else:
        st.success("✅ Нет уведомлений!")

# Товары
with tabs[2]:
    st.markdown("## 📋 Товары")
    search = st.text_input("🔍 Поиск")
    if search:
        conn = sqlite3.connect('storage.db')
        c = conn.cursor()
        q = f"%{search}%"
        c.execute("SELECT * FROM items WHERE name LIKE ? OR location LIKE ? OR tags LIKE ?", (q, q, q))
        items = c.fetchall()
        conn.close()
    else:
        items = get_all_items()
    
    if items:
        for item in items:
            with st.expander(f"{'🔴' if item[6] <= item[7] else '🟢'} {item[1]} — {item[6]} {item[5]} | {item[3]}"):
                st.write(f"📍 {item[2]}")
                if len(item) > 8 and item[8]:
                    st.write(f"🏷️ {item[8]}")
    else:
        st.info("Ничего не найдено")

# Заявки
with tabs[3]:
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
            if st.form_submit_button("📤 Отправить") and name:
                add_request(name, qty, unit, desc, user_name)
                st.success("✅ Отправлено!")
                st.rerun()
        
        st.divider()
        for req in get_requests(user=user_name):
            r = req
            req_id = r[0]
            status_text = {'pending': '⏳ На рассмотрении', 'in_work': '🔧 В работе', 
                          'approved': '✅ Выполнено', 'rejected': '❌ Отклонено',
                          'suggested': '💡 Предложено', 'returned': '🔄 Возвращено'}
            
            with st.expander(f"{status_text.get(r[8], r[8])} | {r[1]} — {r[2]} {r[3]}"):
                if r[8] == 'suggested' and len(r) > 11 and r[11]:
                    st.markdown("### 💡 Предложенный товар:")
                    conn = sqlite3.connect('storage.db')
                    c = conn.cursor()
                    c.execute("SELECT * FROM items WHERE id=?", (r[11],))
                    item = c.fetchone()
                    conn.close()
                    if item:
                        show_item_card_mini(item)
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Подходит", key=f"ok_{req_id}"):
                                update_request_status(req_id, "approved", "Принято сотрудником")
                                st.rerun()
                        with col2:
                            if st.button("❌ Не подходит", key=f"no_{req_id}"):
                                st.session_state[f"return_{req_id}"] = True
                        
                        if st.session_state.get(f"return_{req_id}"):
                            reason = st.text_area("Причина возврата", key=f"reason_{req_id}")
                            if st.button("📤 Отправить на пересмотр", key=f"send_ret_{req_id}"):
                                comment = f"Отклонено: {reason}" if reason else "Отклонено сотрудником"
                                update_request_status(req_id, "returned", comment)
                                st.session_state[f"return_{req_id}"] = False
                                st.rerun()
    
    elif role == "admin":
        subtabs = st.tabs(["⏳ Новые", "🔧 В работе", "🔄 Возвраты", "💡 Предложенные", "✅ Выполненные", "❌ Отклоненные"])
        
        for tab, status in zip(subtabs, ["pending", "in_work", "returned", "suggested", "approved", "rejected"]):
            with tab:
                for req in get_requests(status=status):
                    r = req
                    req_id = r[0]
                    with st.expander(f"{r[1]} — {r[2]} {r[3]} | {r[6]} | {r[7][:10]}"):
                        if status in ['pending', 'returned']:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✅ Одобрить", key=f"app_{req_id}"):
                                    update_request_status(req_id, "approved", "Заявка одобрена")
                                    st.rerun()
                            with col2:
                                if st.button("💡 Со склада", key=f"sug_{req_id}"):
                                    st.session_state[f"show_suggest_{req_id}"] = True
                            with col3:
                                if st.button("❌ Отклонить", key=f"rej_{req_id}"):
                                    update_request_status(req_id, "rejected", "Заявка отклонена")
                                    st.rerun()
                            
                            if st.session_state.get(f"show_suggest_{req_id}"):
                                st.markdown("---")
                                search_term = st.text_input("Поиск товара", key=f"search_sug_{req_id}")
                                if search_term:
                                    found = search_items_for_suggest(search_term)
                                    if found:
                                        for item in found:
                                            show_item_card_mini(item)
                                            if st.button("📤 Предложить", key=f"sel_{req_id}_{item[0]}"):
                                                update_request_status(req_id, "suggested", f"Предложен: {item[1]}", item[0])
                                                st.session_state[f"show_suggest_{req_id}"] = False
                                                st.rerun()
                                if st.button("❌ Закрыть", key=f"close_{req_id}"):
                                    st.session_state[f"show_suggest_{req_id}"] = False
                                    st.rerun()
                        
                        elif status == 'in_work':
                            if st.button("✅ Выполнено", key=f"done_{req_id}"):
                                update_request_status(req_id, "approved", "Заявка выполнена")
                                st.rerun()
                        
                        elif status == 'approved':
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("📦 Создать товар", key=f"create_{req_id}"):
                                    st.session_state[f"show_create_{req_id}"] = True
                            with col2:
                                if st.button("🗑️ Удалить", key=f"del_{req_id}"):
                                    conn = sqlite3.connect('storage.db')
                                    c = conn.cursor()
                                    c.execute("DELETE FROM requests WHERE id=?", (req_id,))
                                    conn.commit()
                                    conn.close()
                                    st.rerun()
                            
                            if st.session_state.get(f"show_create_{req_id}"):
                                with st.form(f"create_form_{req_id}"):
                                    st.markdown("### 📦 Создать товар из заявки")
                                    rooms = get_room_names()
                                    if rooms:
                                        new_room = st.selectbox("Помещение*", rooms)
                                        new_loc = st.text_input("Место*")
                                        if st.form_submit_button("💾 Сохранить и удалить заявку"):
                                            if new_loc:
                                                create_item_from_request(req_id, r[1], new_loc, new_room, r[2], r[3])
                                                st.session_state[f"show_create_{req_id}"] = False
                                                st.success(f"✅ Товар '{r[1]}' создан, заявка удалена!")
                                                st.rerun()
                                            else:
                                                st.error("Укажите место!")

# Списания
with tabs[4]:
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

# Список покупок
with tabs[5]:
    st.markdown("## 🛒 Список покупок")
    items = get_shopping_list()
    
    if items:
        in_work = len([i for i in items if i['type'] == 'in_work'])
        low = len([i for i in items if i['type'] == 'low_stock'])
        approved = len([i for i in items if i['type'] == 'approved'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔧 В работе", in_work)
        with col2:
            st.metric("⚠️ Заканчиваются", low)
        with col3:
            st.metric("✅ К закупке", approved)
        
        st.divider()
        
        for item in items:
            with st.expander(f"{item['icon']} {item['name']} — {item['qty']} {item['unit']}"):
                if item['type'] == 'in_work':
                    st.write(f"От: {item['user']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Выполнено", key=f"done_{item['id']}"):
                            update_request_status(item['id'], "approved")
                            st.rerun()
                    with col2:
                        if st.button("📦 Создать товар", key=f"create_w_{item['id']}"):
                            st.session_state[f"show_create_{item['id']}"] = True
                    
                    if st.session_state.get(f"show_create_{item['id']}"):
                        with st.form(f"create_form_{item['id']}"):
                            rooms = get_room_names()
                            if rooms:
                                new_room = st.selectbox("Помещение*", rooms, key=f"room_{item['id']}")
                                new_loc = st.text_input("Место*", key=f"loc_{item['id']}")
                                if st.form_submit_button("💾 Сохранить и удалить заявку"):
                                    if new_loc:
                                        create_item_from_request(item['id'], item['name'], new_loc, new_room, item['qty'], item['unit'])
                                        st.session_state[f"show_create_{item['id']}"] = False
                                        st.success(f"✅ Товар '{item['name']}' создан, заявка удалена!")
                                        st.rerun()
                                    else:
                                        st.error("Укажите место!")
                
                elif item['type'] == 'low_stock':
                    st.write(f"📍 {item['room']} (порог: {item['threshold']})")
                    new_qty = st.number_input("Новое кол-во", value=float(item['qty']), key=f"q_{item['id']}")
                    if st.button("💾 Обновить количество", key=f"upd_{item['id']}"):
                        conn = sqlite3.connect('storage.db')
                        c = conn.cursor()
                        c.execute("UPDATE items SET quantity=? WHERE id=?", (new_qty, item['id']))
                        conn.commit()
                        conn.close()
                        st.success("✅ Количество обновлено!")
                        st.rerun()
                
                elif item['type'] == 'approved':
                    st.write(f"От: {item['user']}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📦 Создать товар", key=f"create_a_{item['id']}"):
                            st.session_state[f"show_create_{item['id']}"] = True
                    with col2:
                        if st.button("🗑️ Удалить заявку", key=f"del_{item['id']}"):
                            conn = sqlite3.connect('storage.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM requests WHERE id=?", (item['id'],))
                            conn.commit()
                            conn.close()
                            st.success("🗑️ Заявка удалена!")
                            st.rerun()
                    with col3:
                        if st.button("📋 В работу", key=f"back_{item['id']}"):
                            update_request_status(item['id'], "in_work", "Возвращено в работу")
                            st.rerun()
                    
                    if st.session_state.get(f"show_create_{item['id']}"):
                        with st.form(f"create_form_a_{item['id']}"):
                            rooms = get_room_names()
                            if rooms:
                                new_room = st.selectbox("Помещение*", rooms, key=f"room_a_{item['id']}")
                                new_loc = st.text_input("Место*", key=f"loc_a_{item['id']}")
                                if st.form_submit_button("💾 Сохранить и удалить заявку"):
                                    if new_loc:
                                        create_item_from_request(item['id'], item['name'], new_loc, new_room, item['qty'], item['unit'])
                                        st.session_state[f"show_create_{item['id']}"] = False
                                        st.success(f"✅ Товар '{item['name']}' создан, заявка удалена!")
                                        st.rerun()
                                    else:
                                        st.error("Укажите место!")
    else:
        st.success("✅ Список покупок пуст!")

# Парк
with tabs[6]:
    st.markdown("## 🚜 Парк")
    if role == "admin":
        with st.form("add_eq"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Название*")
            with col2:
                num = st.text_input("Номер")
            if st.form_submit_button("Добавить") and name:
                conn = sqlite3.connect('storage.db')
                c = conn.cursor()
                c.execute("INSERT INTO equipment (name, number, date_added) VALUES (?,?,?)",
                          (name, num, datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                conn.close()
                st.rerun()

# Управление
with tabs[7]:
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
                if not os.path.exists("backups"):
                    os.makedirs("backups")
                fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2('storage.db', f"backups/{fname}")
                st.success(f"✅ Бэкап создан: {fname}")
