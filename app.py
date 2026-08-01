import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import pandas as pd
from io import BytesIO

# --- ПАРОЛЬ ---
PASSWORD = "12345"

user_pass = st.sidebar.text_input("🔑 Введите пароль:", type="password")
if user_pass != PASSWORD:
    st.sidebar.warning("⚠️ Неверный пароль!")
    st.stop()

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="📦", layout="wide")
st.title("📦 Мой Склад")
st.caption("Добро пожаловать! Храните и находите вещи легко.")

# --- ПАПКА ДЛЯ ФОТО ---
if not os.path.exists("images"):
    os.makedirs("images")

# --- БАЗА ДАННЫХ ---
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
                  threshold INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS park
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  date_added TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS consumption
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  item_id TEXT,
                  quantity REAL,
                  unit TEXT,
                  object_name TEXT,
                  user TEXT,
                  date TEXT)''')
    conn.commit()
    conn.close()

def add_item(name, category, location, room, description, item_photo_path, location_photo_path, quantity, unit, threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    item_id = str(uuid.uuid4())[:8]
    c.execute("INSERT INTO items (id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (item_id, name, category, location, room, description, item_photo_path, location_photo_path, datetime.now().strftime("%Y-%m-%d %H:%M"), quantity, unit, threshold))
    conn.commit()
    conn.close()
    return item_id

def update_quantity(item_id, new_quantity):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()

def update_threshold(item_id, new_threshold):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("UPDATE items SET threshold = ? WHERE id = ?", (new_threshold, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def get_all_items():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM items ORDER BY date_added DESC")
    results = c.fetchall()
    conn.close()
    return results

def get_all_rooms():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT room FROM items")
    rooms = [row[0] for row in c.fetchall()]
    conn.close()
    return rooms if rooms else ["Общий"]

def get_statistics():
    conn = sqlite3.connect('storage.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM items")
    total_items = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT room) FROM items")
    total_rooms = c.fetchone()[0]
    conn.close()
    return total_items, total_rooms

init_db()

# --- СТАТИСТИКА ---
total_items, total_rooms = get_statistics()

col1, col2 = st.columns(2)
with col1:
    st.metric("📦 Всего вещей", total_items)
with col2:
    st.metric("🏠 Помещений", total_rooms)

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("➕ Добавить вещь")
    existing_rooms = get_all_rooms()
    room_options = ["Новое помещение"] + existing_rooms
    
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Название вещи*")
        category = st.text_input("Категория")
        room_choice = st.selectbox("Помещение", room_options)
        if room_choice == "Новое помещение":
            room = st.text_input("Название нового помещения*")
        else:
            room = room_choice
        location = st.text_input("Место внутри помещения*")
        description = st.text_area("Описание")
        col1, col2, col3 = st.columns(3)
        with col1:
            quantity = st.number_input("Количество", min_value=0.0, step=0.5, value=1.0)
        with col2:
            unit = st.selectbox("Ед. изм.", ["шт", "л", "кг", "м", "комплект", "упаковка", "м²", "другой"])
            if unit == "другой":
                unit = st.text_input("Своя единица")
        with col3:
            threshold = st.number_input("Порог", min_value=0, step=1, value=1)
        submitted = st.form_submit_button("💾 Сохранить")
        if submitted and name and location and room:
            add_item(name, category, location, room, description, "", "", quantity, unit, threshold)
            st.success(f"✅ Добавлено {quantity} {unit} '{name}'")
            st.rerun()
        elif submitted:
            st.error("⚠️ Название, Помещение и Место обязательны!")

# --- ГЛАВНАЯ ОБЛАСТЬ ---
st.subheader("📋 Все вещи")

items = get_all_items()

if not items:
    st.info("В базе пока нет вещей. Добавьте первую вещь через боковое меню!")
else:
    # Отображаем в виде карточек
    cols = st.columns(3)
    for idx, item in enumerate(items):
        with cols[idx % 3]:
            # Распаковываем данные
            item_id, name, category, location, room, description, item_photo, location_photo, date_added, quantity, unit, threshold = item
            
            # Преобразуем количество
            try:
                qty = float(quantity)
            except:
                qty = 0
            
            # Определяем статус
            if qty <= 0:
                status = "🔴 КРИТИЧНО!"
            elif qty <= threshold:
                status = f"🟡 Скоро закончится (≤ {threshold})"
            else:
                status = "🟢 В норме"
            
            with st.container(border=True):
                st.markdown(f"**{name}**")
                if category:
                    st.caption(f"📂 {category}")
                st.caption(f"🏠 {room} → 📍 {location}")
                st.caption(f"📦 Количество: **{qty} {unit}**")
                st.caption(f"📊 Статус: **{status}**")
                
                # Фото (заглушка)
                st.image("https://via.placeholder.com/150/cccccc/969696?text=Нет+фото", use_container_width=True)
                
                if description:
                    st.write(f"📝 {description}")
                st.caption(f"🕒 Добавлено: {date_added}")
                
                # Кнопки управления
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✏️ Кол-во", key=f"edit_{item_id}"):
                        st.session_state[f"edit_{item_id}"] = True
                with col_btn2:
                    if st.button("🗑️", key=f"del_{item_id}"):
                        delete_item(item_id)
                        st.rerun()
                
                # Диалог изменения количества
                if st.session_state.get(f"edit_{item_id}", False):
                    with st.container():
                        st.write("---")
                        new_q = st.number_input(f"Новое количество ({unit})", min_value=0.0, step=0.5, value=float(qty), key=f"new_q_{item_id}")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Сохранить", key=f"save_q_{item_id}"):
                                update_quantity(item_id, new_q)
                                st.session_state[f"edit_{item_id}"] = False
                                st.rerun()
                        with col2:
                            if st.button("❌ Отмена", key=f"cancel_q_{item_id}"):
                                st.session_state[f"edit_{item_id}"] = False
                                st.rerun()
