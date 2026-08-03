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
EMAIL_PASSWORD = "ТВОЙ_ПАРОЛЬ_ОТ_ПОЧТЫ"  # ← ЗАМЕНИ НА СВОЙ ПАРОЛЬ
EMAIL_RECIPIENT = "Yvedomlenie-scald.sad@yandex.ru"
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 587

def send_email(subject, body):
    """Отправляет email через Yandex с поддержкой UTF-8"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        
        # Явно указываем кодировку UTF-8 для русского текста
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
    """Отображает форму входа в центре страницы"""
    # CSS для центрирования формы
    st.markdown("""
        <style>
            .login-container {
                max-width: 400px;
                margin: 0 auto;
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
            input[type="password"] {
                -webkit-text-security: disc !important;
                font-size: 1.2rem !important;
                letter-spacing: 4px !important;
                text-align: center;
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
        </style>
    """, unsafe_allow_html=True)
    
    # Центрированная форма
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🌿 Мой Склад</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Система учета запчастей и материалов</div>', unsafe_allow_html=True)
        
        password = st.text_input(
            "Введите пароль",
            type="password",
            key="login_password",
            placeholder="Введите пароль здесь"
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
        
        st.markdown('</div>', unsafe_allow_html=True)

# Проверяем авторизацию
if st.session_state.user is None:
    # Проверяем сохраненный пароль в URL
    if "user" in st.query_params:
        saved_user = st.query_params["user"]
        if saved_user in USERS:
            st.session_state.user = USERS[saved_user]
            st.session_state.user["password"] = saved_user
    
    # Если не авторизован - показываем форму входа
    if st.session_state.user is None:
        login_page()
        st.stop()

user = st.session_state.user
role = user["role"]
user_name = user["name"]

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Мой Склад", page_icon="🌿", layout="wide")

# ... (остальной код остается без изменений)
