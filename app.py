import streamlit as st
import sqlite3
import os
from datetime import datetime

st.set_page_config(page_title="Тест", layout="wide")
st.title("📦 Мой Склад — ТЕСТОВАЯ ВЕРСИЯ")
st.write("Это минимальный код для проверки работы приложения.")

# Пароль
PASSWORD = "12345"
user_pass = st.sidebar.text_input("🔑 Введите пароль:", type="password")
if user_pass != PASSWORD:
    st.sidebar.warning("⚠️ Неверный пароль!")
    st.stop()

# База данных
conn = sqlite3.connect('test.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS test
             (id INTEGER PRIMARY KEY, name TEXT)''')
conn.commit()
conn.close()

st.success("✅ База данных создана! Приложение работает.")
st.info("Теперь можно добавлять код постепенно.")
