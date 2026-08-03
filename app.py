import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

def test_email():
    EMAIL = "Yvedomlenie-scald.sad@yandex.ru"
    PASSWORD = "bpzhkwtwimhurhkt"
    RECIPIENT = "Yvedomlenie-scald.sad@yandex.ru"  # Можно отправить себе же
    
    try:
        print("📧 Подключаюсь к Yandex...")
        server = smtplib.SMTP("smtp.yandex.ru", 587)
        print("✅ Подключились")
        
        print("🔒 Запускаю TLS...")
        server.starttls()
        print("✅ TLS готов")
        
        print("🔑 Авторизуюсь...")
        server.login(EMAIL, PASSWORD)
        print("✅ Авторизация успешна!")
        
        print("📨 Создаю письмо...")
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = RECIPIENT
        msg['Subject'] = Header("✅ Тест", 'utf-8').encode()
        msg.attach(MIMEText("Работает!", 'plain', 'utf-8'))
        
        print("📤 Отправляю...")
        server.send_message(msg)
        print("✅ Письмо отправлено!")
        
        server.quit()
        print("🎉 ВСЕ РАБОТАЕТ!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ ОШИБКА АВТОРИЗАЦИИ: {e}")
        print("Проверьте:")
        print("  1. Включен ли IMAP в настройках почты")
        print("  2. Правильный ли пароль")
        return False
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False

test_email()
