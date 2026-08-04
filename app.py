import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import shutil

# ============================================================
# 1. НАСТРОЙКА И ПЕРЕМЕННЫЕ
# ============================================================

# Создаём папки
for folder in ["images", "images/items", "images/take", "backups"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Пароли
USERS = {
    "12345": {"role": "admin", "name": "Администратор"},
    "1111": {"role": "employee", "name": "Сотрудник"},
}

# Инициализация сессии
if "user" not in st.session_state:
    st.session_state.user = None
if "dismissed_notifications" not in st.session_state:
    st.session_state.dismissed_notifications = []

st.set_page_config(page_title="Мой Склад", page_icon="📦", layout="wide")

# ============================================================
# 2. БАЗА ДАННЫХ
# ============================================================

def init_db():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    
    # Товары
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        name TEXT,
        location TEXT,
        room TEXT,
        date_added TEXT,
        quantity REAL,
        unit TEXT,
        threshold INTEGER DEFAULT 1,
        photos_count INTEGER DEFAULT 0
    )''')
    
    # Техника
    c.execute('''CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        number TEXT,
        date_added TEXT
    )''')
    
    # Помещения
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        date_added TEXT
    )''')
    
    # Заявки
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        suggested_item_id TEXT
    )''')
    
    # Списания
    c.execute('''CREATE TABLE IF NOT EXISTS consumption (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT,
        quantity REAL,
        unit TEXT,
        object_name TEXT,
        user TEXT,
        date TEXT,
        equipment_name TEXT,
        equipment_number TEXT,
        photo TEXT
    )''')
    
    # Фото товаров
    c.execute('''CREATE TABLE IF NOT EXISTS item_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT,
        photo_path TEXT,
        date_added TEXT,
        is_main INTEGER DEFAULT 0
    )''')
    
    conn.commit()
    conn.close()

init_db()

# ============================================================
# 3. ФУНКЦИИ БАЗЫ ДАННЫХ
# ============================================================

def get_room_names():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT name FROM rooms ORDER BY name")
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result

def add_room(name):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rooms (name, date_added) VALUES (?, ?)", 
                  (name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def get_equipment():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM equipment ORDER BY name")
    result = c.fetchall()
    conn.close()
    return result

def add_equipment(name, number=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO equipment (name, number, date_added) VALUES (?, ?, ?)",
                  (name, number, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def search_equipment(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    q = f"%{query}%"
    c.execute("SELECT * FROM equipment WHERE name LIKE ? OR number LIKE ? ORDER BY name", (q, q))
    result = c.fetchall()
    conn.close()
    return result

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items ORDER BY date_added DESC")
    result = c.fetchall()
    conn.close()
    return result

def search_items(query):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    q = f"%{query}%"
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items WHERE name LIKE ? OR location LIKE ? OR room LIKE ?", (q, q, q))
    result = c.fetchall()
    conn.close()
    return result

def add_item(name, location, room, quantity, unit):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, location, room, date_added, quantity, unit, threshold) VALUES (?,?,?,?,?,?,?,?)",
              (item_id, name, location, room, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, 1))
    conn.commit()
    conn.close()
    return item_id

def update_item(item_id, name, location, room, quantity, unit, threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET name=?, location=?, room=?, quantity=?, unit=?, threshold=? WHERE id=?",
              (name, location, room, quantity, unit, threshold, item_id))
    conn.commit()
    conn.close()

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity=? WHERE id=?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def move_item(item_id, new_location, new_room):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET location=?, room=? WHERE id=?", (new_location, new_room, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    # Удаляем фото
    c.execute("SELECT photo_path FROM item_photos WHERE item_id=?", (item_id,))
    for photo in c.fetchall():
        if os.path.exists(photo[0]):
            try: os.remove(photo[0])
            except: pass
    c.execute("DELETE FROM item_photos WHERE item_id=?", (item_id,))
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_low_stock():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, name, location, room, date_added, unit, quantity, threshold, photos_count FROM items WHERE quantity <= threshold ORDER BY quantity ASC")
    result = c.fetchall()
    conn.close()
    return result

def add_item_photo(item_id, photo_path, is_main=False):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if is_main:
        c.execute("UPDATE item_photos SET is_main=0 WHERE item_id=?", (item_id,))
    c.execute("INSERT INTO item_photos (item_id, photo_path, date_added, is_main) VALUES (?,?,?,?)",
              (item_id, photo_path, datetime.now().strftime("%Y-%m-%d %H:%M"), 1 if is_main else 0))
    c.execute("UPDATE items SET photos_count = photos_count + 1 WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_item_photos(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT id, photo_path, is_main FROM item_photos WHERE item_id=? ORDER BY is_main DESC, date_added DESC", (item_id,))
    result = c.fetchall()
    conn.close()
    return result

def delete_item_photo(photo_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_id, photo_path FROM item_photos WHERE id=?", (photo_id,))
    row = c.fetchone()
    if row:
        item_id, photo_path = row
        if os.path.exists(photo_path):
            try: os.remove(photo_path)
            except: pass
        c.execute("DELETE FROM item_photos WHERE id=?", (photo_id,))
        c.execute("UPDATE items SET photos_count = photos_count - 1 WHERE id=?", (item_id,))
        # Если удалили главное - делаем первое главным
        c.execute("SELECT id FROM item_photos WHERE item_id=? LIMIT 1", (item_id,))
        first = c.fetchone()
        if first:
            c.execute("UPDATE item_photos SET is_main=1 WHERE id=?", (first[0],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def set_main_photo(photo_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT item_id FROM item_photos WHERE id=?", (photo_id,))
    row = c.fetchone()
    if row:
        item_id = row[0]
        c.execute("UPDATE item_photos SET is_main=0 WHERE item_id=?", (item_id,))
        c.execute("UPDATE item_photos SET is_main=1 WHERE id=?", (photo_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def rotate_photo(path, degrees):
    try:
        img = Image.open(path)
        img = img.rotate(degrees, expand=True)
        img.save(path, quality=95)
        return True
    except:
        return False

def take_item(item_id, quantity, eq_name, eq_number, photo_path=""):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT quantity, unit FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    if not row or quantity > row[0]:
        conn.close()
        return False, "Недостаточно товара"
    new_q = row[0] - quantity
    c.execute("UPDATE items SET quantity=? WHERE id=?", (new_q, item_id))
    c.execute("""INSERT INTO consumption (item_id, quantity, unit, object_name, user, date, equipment_name, equipment_number, photo)
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (item_id, quantity, row[1], f"{eq_name} (№{eq_number})", 
               st.session_state.user["name"], datetime.now().strftime("%Y-%m-%d %H:%M"),
               eq_name, eq_number, photo_path))
    conn.commit()
    conn.close()
    return True, f"✅ Взято {quantity} {row[1]} на {eq_name}"

def get_consumption():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM consumption ORDER BY date DESC LIMIT 100")
    result = c.fetchall()
    conn.close()
    return result

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
    result = c.fetchall()
    conn.close()
    return result

def update_request_status(req_id, status, comment="", suggested_id=None):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    if suggested_id:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0, suggested_item_id=? WHERE id=?",
                  (status, comment, suggested_id, req_id))
    else:
        c.execute("UPDATE requests SET status=?, admin_comment=?, seen=0 WHERE id=?",
                  (status, comment, req_id))
    conn.commit()
    conn.close()

def delete_request(req_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

def unpack_request(req):
    return {
        'id': req[0], 'name': req[1] or "", 'quantity': req[2] or 0,
        'unit': req[3] or "", 'description': req[4] or "", 'photo': req[5] or "",
        'user': req[6] or "", 'date': req[7] or "", 'status': req[8] or "pending",
        'seen': req[9] or 0, 'admin_comment': req[10] or "", 'suggested_item_id': req[11] or None
    }

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

# ============================================================
# 4. ВХОД В СИСТЕМУ
# ============================================================

def login_page():
    st.markdown("<h1 style='text-align:center;'>📦 Управление складом</h1>", unsafe_allow_html=True)
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

# ============================================================
# 5. УВЕДОМЛЕНИЯ
# ============================================================

def get_notifications():
    notifications = []
    if role == "admin":
        for req in get_requests(status='pending'):
            r = unpack_request(req)
            nid = f"pending_{r['id']}"
            if nid not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': nid, 'icon': '📝', 'title': f'Новая заявка: {r["name"]}',
                    'text': f'От: {r["user"]} | {r["quantity"]} {r["unit"]}',
                    'date': r['date'], 'request_id': r['id']
                })
        for item in get_low_stock():
            nid = f"low_{item[0]}"
            if nid not in st.session_state.dismissed_notifications:
                notifications.append({
                    'id': nid, 'icon': '⚠️', 'title': f'Заканчивается: {item[1]}',
                    'text': f'Осталось {item[6]} {item[5]} (порог: {item[7]})',
                    'date': item[4], 'item_id': item[0]
                })
    else:
        for req in get_requests(user=user_name):
            r = unpack_request(req)
            nid = f"{r['status']}_{r['id']}"
            if nid not in st.session_state.dismissed_notifications:
                icons = {'pending':'⏳','in_work':'🔧','approved':'✅','rejected':'❌','suggested':'💡','returned':'🔄'}
                notifications.append({
                    'id': nid, 'icon': icons.get(r['status'], '📋'),
                    'title': r['name'], 'text': f'Статус: {r["status"]}',
                    'date': r['date'], 'request_id': r['id']
                })
    return sorted(notifications, key=lambda x: x['date'], reverse=True)

def get_shopping_list():
    shopping = []
    for req in get_requests(status='in_work'):
        r = unpack_request(req)
        shopping.append({'type': 'in_work', 'icon': '🔧', 'name': r['name'], 
                         'qty': float(r['quantity'] or 0), 'unit': r['unit'], 'id': r['id']})
    for req in get_requests(status='pending'):
        r = unpack_request(req)
        shopping.append({'type': 'pending', 'icon': '📝', 'name': r['name'], 
                         'qty': float(r['quantity'] or 0), 'unit': r['unit'], 'id': r['id']})
    for item in get_low_stock():
        shopping.append({'type': 'low_stock', 'icon': '⚠️', 'name': item[1], 
                         'qty': float(item[6] or 0), 'unit': item[5], 'id': item[0]})
    for req in get_requests(status='approved'):
        r = unpack_request(req)
        shopping.append({'type': 'approved', 'icon': '✅', 'name': r['name'], 
                         'qty': float(r['quantity'] or 0), 'unit': r['unit'], 'id': r['id']})
    return shopping

# ============================================================
# 6. БОКОВАЯ ПАНЕЛЬ
# ============================================================

with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(f"Роль: {'🔑 Администратор' if role == 'admin' else '🔧 Сотрудник'}")
    
    notifs = get_notifications()
    if notifs and st.button(f"🔔 Уведомлений: {len(notifs)}", use_container_width=True):
        st.session_state.active_tab = 0
        st.rerun()
    
    if role == "admin":
        shopping = get_shopping_list()
        if shopping and st.button(f"🛒 К покупке: {len(shopping)}", use_container_width=True):
            st.session_state.active_tab = 6
            st.rerun()
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    
    st.divider()
    
    if role == "admin":
        with st.form("quick_add", clear_on_submit=True):
            st.markdown("### ➕ Новый товар")
            name = st.text_input("Название*")
            location = st.text_input("Место*")
            rooms = get_room_names()
            room = st.selectbox("Помещение*", rooms if rooms else ["Нет помещений"])
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Кол-во", min_value=0.0, value=1.0)
            with col2:
                unit = st.selectbox("Ед.", ["шт", "л", "кг", "м", "комплект"])
            
            st.markdown("---")
            st.markdown("📸 **Фото товара**")
            uploaded_photo = st.file_uploader("Выберите фото", type=["jpg","jpeg","png"], key="quick_photo")
            is_main = st.checkbox("⭐ Сделать главным", value=True)
            
            if st.form_submit_button("💾 Сохранить") and name and location and room != "Нет помещений":
                item_id = add_item(name, location, room, qty, unit)
                if uploaded_photo:
                    ext = uploaded_photo.name.split('.')[-1]
                    photo_path = f"images/items/{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                    with open(photo_path, "wb") as f:
                        f.write(uploaded_photo.getbuffer())
                    add_item_photo(item_id, photo_path, is_main)
                st.success(f"✅ {name} добавлен!")
                st.rerun()

# ============================================================
# 7. ОСНОВНОЙ ИНТЕРФЕЙС
# ============================================================

st.title("📦 SmartStock Pro")

tabs = st.tabs(["🔔 Уведомления", "📊 Дашборд", "🔍 Поиск", "📋 Товары", "📝 Заявки", "📤 Списания", "🛒 Покупки", "🚜 Парк", "⚙️ Управление"])

# ============================================================
# 7.1 УВЕДОМЛЕНИЯ
# ============================================================

with tabs[0]:
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
                if n.get('request_id') and role == 'admin':
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

# ============================================================
# 7.2 ДАШБОРД
# ============================================================

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

# ============================================================
# 7.3 ПОИСК
# ============================================================

with tabs[2]:
    st.markdown("## 🔍 Поиск товаров")
    search = st.text_input("Поиск по названию, месту, помещению")
    
    items = search_items(search) if search else get_all_items()
    
    if items:
        for item in items:
            qty = item[6] if len(item) > 6 else 0
            threshold = item[7] if len(item) > 7 else 1
            with st.expander(f"{'🔴' if qty <= threshold else '🟢'} {item[1]} — {qty} {item[5]} | {item[3]}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"📍 Место: {item[2]}")
                    st.write(f"🏠 Помещение: {item[3]}")
                    st.write(f"📦 Количество: {qty} {item[5]}")
                    st.write(f"⚠️ Порог: {threshold}")
                with col2:
                    photos = get_item_photos(item[0])
                    if photos:
                        main = next((p for p in photos if p[2] == 1), photos[0])
                        if os.path.exists(main[1]):
                            st.image(main[1], use_container_width=True)
    else:
        st.info("Ничего не найдено")

# ============================================================
# 7.4 ТОВАРЫ
# ============================================================

with tabs[3]:
    st.markdown("## 📋 Все товары")
    
    # Статистика
    all_items = get_all_items()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Всего", len(all_items))
    with col2:
        st.metric("⚠️ Заканчиваются", len([i for i in all_items if i[6] <= i[7] and i[6] > 0]))
    with col3:
        st.metric("🚫 Нет в наличии", len([i for i in all_items if i[6] == 0]))
    with col4:
        st.metric("📸 С фото", len([i for i in all_items if i[8] and int(i[8]) > 0]))
    
    st.divider()
    
    # Фильтры
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("🔍 Поиск", placeholder="Введите запрос...", key="items_search")
    with col2:
        filter_type = st.selectbox("Фильтр", ["Все", "Заканчиваются", "Нет в наличии", "В наличии"])
    with col3:
        sort_by = st.selectbox("Сортировка", ["По дате (новые)", "По дате (старые)", "По названию", "По количеству"])
    
    # Получаем и фильтруем
    items = search_items(search) if search else get_all_items()
    
    if filter_type == "Заканчиваются":
        items = [i for i in items if i[6] <= i[7] and i[6] > 0]
    elif filter_type == "Нет в наличии":
        items = [i for i in items if i[6] == 0]
    elif filter_type == "В наличии":
        items = [i for i in items if i[6] > 0]
    
    # Сортировка
    if sort_by == "По дате (новые)":
        items.sort(key=lambda x: x[4] or "", reverse=True)
    elif sort_by == "По дате (старые)":
        items.sort(key=lambda x: x[4] or "")
    elif sort_by == "По названию":
        items.sort(key=lambda x: x[1] or "")
    elif sort_by == "По количеству":
        items.sort(key=lambda x: x[6] or 0)
    
    if items:
        st.success(f"Найдено товаров: {len(items)}")
        
        # Пагинация
        per_page = 10
        total_pages = (len(items) - 1) // per_page + 1
        page = st.selectbox("Страница", range(1, total_pages + 1), key="items_page") if total_pages > 1 else 1
        
        start = (page - 1) * per_page
        end = min(start + per_page, len(items))
        
        for idx, item in enumerate(items[start:end]):
            item_id = item[0]
            name = item[1]
            location = item[2] if len(item) > 2 else ""
            room = item[3] if len(item) > 3 else ""
            date_added = item[4] if len(item) > 4 else ""
            unit = item[5] if len(item) > 5 else "шт"
            quantity = float(item[6]) if len(item) > 6 else 0
            threshold = int(item[7]) if len(item) > 7 else 1
            
            if quantity == 0:
                status_icon, status_text = "🚫", "Нет в наличии"
            elif quantity <= threshold:
                status_icon, status_text = "⚠️", f"Заканчивается (порог: {threshold})"
            else:
                status_icon, status_text = "✅", f"В наличии: {quantity} {unit}"
            
            # Уникальный суффикс для ключей
            uid = f"{item_id}_{idx}"
            
            with st.container():
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown(f"### {status_icon} {name}")
                    st.caption(f"📍 {location} | 🏠 {room} | 📅 {date_added[:10] if date_added else 'Н/Д'}")
                    st.markdown(f"**📊 Количество:** {quantity} {unit}")
                    st.markdown(f"**⚠️ Порог:** {threshold}")
                    
                    if quantity == 0:
                        st.error(status_text)
                    elif quantity <= threshold:
                        st.warning(status_text)
                    else:
                        st.success(status_text)
                    
                    # --- КНОПКИ ДЛЯ АДМИНА ---
                    if role == "admin":
                        # РЕДАКТИРОВАНИЕ
                        with st.expander("✏️ Редактировать", expanded=False):
                            with st.form(key=f"edit_{uid}"):
                                edit_name = st.text_input("Название*", value=name, key=f"en_{uid}")
                                edit_loc = st.text_input("Место*", value=location, key=f"el_{uid}")
                                rooms = get_room_names()
                                edit_room = st.selectbox("Помещение", rooms if rooms else ["Нет"], 
                                                        index=rooms.index(room) if room in rooms else 0,
                                                        key=f"er_{uid}")
                                c1, c2 = st.columns(2)
                                with c1:
                                    edit_qty = st.number_input("Количество", value=float(quantity), key=f"eq_{uid}")
                                with c2:
                                    edit_unit = st.selectbox("Ед.", ["шт","л","кг","м","комплект"], 
                                                            index=["шт","л","кг","м","комплект"].index(unit) if unit in ["шт","л","кг","м","комплект"] else 0,
                                                            key=f"eu_{uid}")
                                edit_threshold = st.number_input("Порог", value=int(threshold), key=f"et_{uid}")
                                if st.form_submit_button("💾 Сохранить"):
                                    if edit_name and edit_loc and edit_room != "Нет":
                                        update_item(item_id, edit_name, edit_loc, edit_room, edit_qty, edit_unit, edit_threshold)
                                        st.success("✅ Обновлено!")
                                        st.rerun()
                        
                        # ПЕРЕМЕЩЕНИЕ
                        with st.expander("📦 Переместить", expanded=False):
                            with st.form(key=f"move_{uid}"):
                                new_loc = st.text_input("Новое место*", value=location, key=f"ml_{uid}")
                                rooms = get_room_names()
                                new_room = st.selectbox("Новое помещение", rooms if rooms else ["Нет"],
                                                       index=rooms.index(room) if room in rooms else 0,
                                                       key=f"mr_{uid}")
                                if st.form_submit_button("📦 Переместить"):
                                    if new_loc and new_room != "Нет":
                                        move_item(item_id, new_loc, new_room)
                                        st.success(f"✅ Перемещено в {new_loc} ({new_room})")
                                        st.rerun()
                        
                        # КОЛИЧЕСТВО
                        with st.expander("🔢 Количество", expanded=False):
                            with st.form(key=f"qty_{uid}"):
                                action = st.radio("Действие", ["Установить", "Прибавить", "Убавить"], key=f"qa_{uid}")
                                value = st.number_input("Значение", value=1.0, key=f"qv_{uid}")
                                if st.form_submit_button("✅ Применить"):
                                    current = float(quantity)
                                    if action == "Установить":
                                        new_qty = value
                                    elif action == "Прибавить":
                                        new_qty = current + value
                                    else:
                                        new_qty = max(0, current - value)
                                    update_quantity(item_id, new_qty)
                                    st.success(f"✅ Обновлено: {new_qty} {unit}")
                                    st.rerun()
                        
                        # УДАЛЕНИЕ
                        with st.expander("🗑️ Удалить", expanded=False):
                            st.warning(f"⚠️ Удалить '{name}'?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Да", key=f"del_yes_{uid}"):
                                    delete_item(item_id)
                                    st.success(f"🗑️ '{name}' удалён")
                                    st.rerun()
                            with col2:
                                if st.button("❌ Нет", key=f"del_no_{uid}"):
                                    st.rerun()
                    
                    # --- КНОПКА ДЛЯ СОТРУДНИКА ---
                    elif role == "employee":
                        with st.expander("📤 Взять", expanded=False):
                            if quantity > 0:
                                take_qty = st.number_input(
                                    "Количество", 
                                    min_value=0.1, 
                                    max_value=float(quantity), 
                                    value=1.0, 
                                    key=f"tq_{uid}"
                                )
                                eq_search = st.text_input(
                                    "Поиск техники", 
                                    key=f"eqs_{uid}"
                                )
                                eq_list = search_equipment(eq_search) if eq_search else get_equipment()
                                if eq_list:
                                    eq_options = {f"{e[1]}" + (f" (№{e[2]})" if e[2] else ""): e for e in eq_list}
                                    selected = st.selectbox(
                                        "Выберите технику", 
                                        list(eq_options.keys()), 
                                        key=f"eq_sel_{uid}"
                                    )
                                    eq = eq_options[selected]
                                    take_photo = st.file_uploader(
                                        "📸 Фото", 
                                        type=["jpg","jpeg","png"], 
                                        key=f"tp_{uid}"
                                    )
                                    if st.button("✅ Подтвердить", key=f"confirm_{uid}"):
                                        photo_path = ""
                                        if take_photo:
                                            ext = take_photo.name.split('.')[-1]
                                            photo_path = f"images/take/take_{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                                            with open(photo_path, "wb") as f:
                                                f.write(take_photo.getbuffer())
                                        success, msg = take_item(
                                            item_id, 
                                            take_qty, 
                                            eq[1], 
                                            eq[2] if len(eq) > 2 else "", 
                                            photo_path
                                        )
                                        if success:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                else:
                                    st.warning("⚠️ Нет техники. Добавьте в 'Парк'")
                            else:
                                st.warning("🚫 Товара нет")
                
                with col2:
                    st.markdown("#### 📸 Фото")
                    photos = get_item_photos(item_id)
                    
                    if photos:
                        # Индекс текущего фото
                        photo_key = f"photo_idx_{item_id}"
                        if photo_key not in st.session_state:
                            st.session_state[photo_key] = 0
                        
                        current_idx = st.session_state[photo_key]
                        if current_idx >= len(photos):
                            current_idx = 0
                            st.session_state[photo_key] = 0
                        
                        current_photo = photos[current_idx]
                        
                        if os.path.exists(current_photo[1]):
                            # Навигация
                            if len(photos) > 1:
                                c1, c2, c3 = st.columns([1, 2, 1])
                                with c1:
                                    if st.button("◀", key=f"prev_{uid}"):
                                        st.session_state[photo_key] = (current_idx - 1) % len(photos)
                                        st.rerun()
                                with c2:
                                    st.caption(f"{current_idx + 1} / {len(photos)}")
                                with c3:
                                    if st.button("▶", key=f"next_{uid}"):
                                        st.session_state[photo_key] = (current_idx + 1) % len(photos)
                                        st.rerun()
                            
                            st.image(current_photo[1], use_container_width=True)
                            if current_photo[2] == 1:
                                st.caption("⭐ Главное")
                    else:
                        st.info("📷 Нет фото")
                    
                    # --- НАСТРОЙКИ ФОТО (ТОЛЬКО ДЛЯ АДМИНА) ---
                    if role == "admin":
                        with st.expander("⚙️ Настройки фото", expanded=False):
                            if photos and os.path.exists(photos[current_idx][1]):
                                current_photo = photos[current_idx]
                                
                                # Поворот
                                st.caption("🔄 Поворот:")
                                c1, c2, c3, c4 = st.columns(4)
                                with c1:
                                    if st.button("↺ 90°", key=f"rot_l_{uid}"):
                                        if rotate_photo(current_photo[1], 90):
                                            st.rerun()
                                with c2:
                                    if st.button("↻ 90°", key=f"rot_r_{uid}"):
                                        if rotate_photo(current_photo[1], -90):
                                            st.rerun()
                                with c3:
                                    if st.button("180°", key=f"rot_180_{uid}"):
                                        if rotate_photo(current_photo[1], 180):
                                            st.rerun()
                                with c4:
                                    if st.button("↺", key=f"rot_reset_{uid}"):
                                        if rotate_photo(current_photo[1], 0):
                                            st.rerun()
                                
                                st.divider()
                                
                                if current_photo[2] != 1:
                                    if st.button("⭐ Сделать главным", key=f"main_{uid}"):
                                        set_main_photo(current_photo[0])
                                        st.rerun()
                                
                                if st.button("🗑️ Удалить это фото", key=f"del_p_{uid}"):
                                    delete_item_photo(current_photo[0])
                                    st.session_state[photo_key] = 0
                                    st.rerun()
                            else:
                                st.info("Нет фото для управления")
                            
                            st.divider()
                            st.caption("📤 Добавить фото:")
                            uploaded = st.file_uploader(
                                "Выберите фото", 
                                type=["jpg","jpeg","png"], 
                                accept_multiple_files=True, 
                                key=f"upload_{uid}"
                            )
                            if uploaded:
                                c1, c2 = st.columns(2)
                                with c1:
                                    is_main = st.checkbox("⭐ Главное", key=f"is_main_{uid}")
                                with c2:
                                    if st.button("📤 Загрузить", key=f"save_{uid}"):
                                        for i, uf in enumerate(uploaded):
                                            ext = uf.name.split('.')[-1]
                                            path = f"images/items/{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.{ext}"
                                            with open(path, "wb") as f:
                                                f.write(uf.getbuffer())
                                            add_item_photo(item_id, path, is_main=(i == 0 and is_main))
                                        st.success(f"✅ Загружено {len(uploaded)} фото!")
                                        st.rerun()
                
                st.divider()
    else:
        st.info("📭 Склад пуст. Добавьте товары через боковую панель.")
# ============================================================
# 7.5 ЗАЯВКИ
# ============================================================

with tabs[4]:
    st.markdown("## 📝 Заявки")
    
    if role == "employee":
        with st.form("new_request", clear_on_submit=True):
            st.subheader("➕ Новая заявка")
            name = st.text_input("Название*")
            c1, c2 = st.columns(2)
            with c1:
                qty = st.number_input("Кол-во", min_value=0.1, value=1.0)
            with c2:
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
            status_text = {'pending':'⏳ На рассмотрении','in_work':'🔧 В работе',
                          'approved':'✅ Выполнено','rejected':'❌ Отклонено',
                          'suggested':'💡 Предложено','returned':'🔄 Возвращено'}
            with st.expander(f"{status_text.get(r['status'], r['status'])} | {r['name']} — {r['quantity']} {r['unit']}"):
                if r['description']:
                    st.write(f"📝 Описание: {r['description']}")
                if r['admin_comment']:
                    st.write(f"💬 Комментарий: {r['admin_comment']}")
                if r['photo'] and os.path.exists(r['photo']):
                    st.image(r['photo'], width=200)
                st.caption(f"📅 {r['date']}")
    
    elif role == "admin":
        statuses = {"⏳ Новые": "pending", "🔧 В работе": "in_work", "🔄 Возвраты": "returned",
                    "💡 Предложенные": "suggested", "✅ Готовые": "approved", "❌ Отклоненные": "rejected"}
        subtabs = st.tabs(list(statuses.keys()))
        for tab, (label, status) in zip(subtabs, statuses.items()):
            with tab:
                reqs = get_requests(status=status)
                if reqs:
                    for req in reqs:
                        r = unpack_request(req)
                        with st.expander(f"{r['name']} — {r['quantity']} {r['unit']} | от {r['user']} | {r['date'][:10]}"):
                            if r['description']:
                                st.write(f"📝 Описание: {r['description']}")
                            if r['admin_comment']:
                                st.write(f"💬 Комментарий: {r['admin_comment']}")
                            if r['photo'] and os.path.exists(r['photo']):
                                st.image(r['photo'], width=200)
                            if r['suggested_item_id']:
                                st.write(f"💡 Предложен товар ID: {r['suggested_item_id']}")
                            
                            st.divider()
                            
                            if status in ['pending', 'returned']:
                                c1, c2, c3 = st.columns(3)
                                with c1:
                                    if st.button("✅ Одобрить", key=f"app_{r['id']}"):
                                        update_request_status(r['id'], "approved")
                                        st.rerun()
                                with c2:
                                    if st.button("💡 Со склада", key=f"sug_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = True
                                with c3:
                                    if st.button("❌ Отклонить", key=f"rej_{r['id']}"):
                                        update_request_status(r['id'], "rejected")
                                        st.rerun()
                                
                                if st.session_state.get(f"sug_{r['id']}"):
                                    sq = st.text_input("Поиск товара", key=f"sq_{r['id']}")
                                    if sq:
                                        found = search_items(sq)
                                        for item in found:
                                            st.write(f"📦 {item[1]} — {item[6]} {item[5]}")
                                            if st.button("📤 Предложить", key=f"sel_{r['id']}_{item[0]}"):
                                                update_request_status(r['id'], "suggested", f"Предложен: {item[1]}", item[0])
                                                st.session_state[f"sug_{r['id']}"] = False
                                                st.rerun()
                                    if st.button("❌ Закрыть", key=f"close_{r['id']}"):
                                        st.session_state[f"sug_{r['id']}"] = False
                                        st.rerun()
                            
                            elif status == 'in_work':
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.button("✅ Выполнено", key=f"done_{r['id']}"):
                                        update_request_status(r['id'], "approved")
                                        st.rerun()
                                with c2:
                                    if st.button("🗑️ Удалить", key=f"del_req_{r['id']}"):
                                        delete_request(r['id'])
                                        st.rerun()
                            
                            elif status == 'approved':
                                if st.button("📦 Создать товар", key=f"create_{r['id']}"):
                                    rooms = get_room_names()
                                    if rooms:
                                        room = st.selectbox("Помещение", rooms, key=f"cr_{r['id']}")
                                        loc = st.text_input("Место", key=f"cl_{r['id']}")
                                        if st.button("💾 Сохранить", key=f"cs_{r['id']}") and loc:
                                            item_id = add_item(r['name'], loc, room, r['quantity'], r['unit'])
                                            delete_request(r['id'])
                                            st.success(f"✅ Товар '{r['name']}' создан!")
                                            st.rerun()
                else:
                    st.info(f"Нет заявок со статусом '{label}'")

# ============================================================
# 7.6 СПИСАНИЯ
# ============================================================

with tabs[5]:
    st.markdown("## 📤 Списания")
    cons = get_consumption()
    if cons:
        for c in cons:
            st.write(f"📤 {c[9]} — {c[2]} {c[3]} → {c[4]} | {c[5]} | {c[6]}")
    else:
        st.info("Нет списаний")

# ============================================================
# 7.7 ПОКУПКИ
# ============================================================

with tabs[6]:
    st.markdown("## 🛒 Список покупок")
    shopping = get_shopping_list()
    if shopping:
        for item in shopping:
            with st.expander(f"{item['icon']} {item['name']} — {item['qty']} {item['unit']}"):
                if item['type'] in ['in_work', 'pending']:
                    st.write(f"От: {item['user']}" if 'user' in item else "")
                    if st.button("✅ Выполнено", key=f"done_{item['id']}"):
                        update_request_status(item['id'], "approved")
                        st.rerun()
                elif item['type'] == 'low_stock':
                    new_qty = st.number_input("Новое кол-во", value=float(item['qty']), key=f"nq_{item['id']}")
                    if st.button("💾 Обновить", key=f"upd_{item['id']}"):
                        update_quantity(item['id'], new_qty)
                        st.rerun()
    else:
        st.success("✅ Список покупок пуст!")

# ============================================================
# 7.8 ПАРК ТЕХНИКИ
# ============================================================

with tabs[7]:
    st.markdown("## 🚜 Парк техники")
    if role == "admin":
        with st.form("add_eq"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Название*")
            with c2:
                num = st.text_input("Номер")
            if st.form_submit_button("Добавить") and name:
                add_equipment(name, num)
                st.rerun()
    
    for eq in get_equipment():
        with st.expander(f"🚜 {eq[1]}" + (f" (№{eq[2]})" if eq[2] else "")):
            st.caption(f"📅 Добавлен: {eq[3][:10] if eq[3] else 'Н/Д'}")

# ============================================================
# 7.9 УПРАВЛЕНИЕ
# ============================================================

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
            st.markdown("**Существующие помещения:**")
            for room in get_room_names():
                st.write(f"• {room}")
        with tab_b:
            if st.button("💾 Создать бэкап"):
                fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2('storage.db', f"backups/{fname}")
                st.success(f"✅ Бэкап создан: {fname}")
