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
        # Создаём письмо
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        # Тема письма (UTF-8)
        msg['Subject'] = subject
        
        # Тело письма с явной кодировкой UTF-8
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Отправляем
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "✅ Email отправлен"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

# --- ОСТАЛЬНАЯ ЧАСТЬ КОДА (БЕЗ ИЗМЕНЕНИЙ) ---
# ... (весь остальной код остаётся таким же, как в предыдущей версии)
