import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Мой Склад", layout="wide")
st.title("📦 Мой Склад")
st.write("Версия с полной базой данных, но без карточек")

PASSWORD = "12345"
user_pass = st.sidebar.text_input("🔑 Введите пароль:", type="password")
if user_pass != PASSWORD:
    st.sidebar.warning("⚠️ Неверный пароль!")
    st.stop()

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

init_db()

st.success("✅ База данных и все функции готовы!")

# Показываем список вещей
items = get_all_items()
st.write(f"📌 Всего вещей в базе: {len(items)}")

if items:
    st.write("Список вещей (только текст, без карточек):")
    for item in items:
        st.write(f"- {item[1]} (Количество: {item[9]} {item[10]})")
else:
    st.info("Пока нет вещей. Добавьте их через боковое меню!")

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
