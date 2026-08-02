import streamlit as st
import sqlite3
from datetime import datetime

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(
    page_title="Склад Механика PRO",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- БАЗА ДАННЫХ ---
@st.cache_resource
def get_connection():
    """Создает подключение к БД и таблицы, если их нет."""
    conn = sqlite3.connect('storage.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Таблица запчастей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            article TEXT,
            quantity INTEGER DEFAULT 0,
            price REAL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица ремонтов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_model TEXT NOT NULL,
            client_name TEXT,
            description TEXT,
            total_cost REAL DEFAULT 0.0,
            repair_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица списания запчастей (связь ремонт-запчасти)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repair_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repair_id INTEGER,
            part_id INTEGER,
            quantity_used INTEGER,
            FOREIGN KEY(repair_id) REFERENCES repairs(id),
            FOREIGN KEY(part_id) REFERENCES parts(id)
        )
    ''')
    
    conn.commit()
    return conn

conn = get_connection()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def add_part(name, article, qty, price):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO parts (name, article, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', (name, article, qty, price))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Ошибка при добавлении запчасти: {e}")
        return False

def create_repair(car, client, desc, parts_used):
    """parts_used: список кортежей (part_id, qty)"""
    try:
        cursor = conn.cursor()
        # 1. Создаем запись о ремонте
        cursor.execute('''
            INSERT INTO repairs (car_model, client_name, description, total_cost)
            VALUES (?, ?, ?, 0)
        ''', (car, client, desc))
        repair_id = cursor.lastrowid
        
        # 2. Списываем запчасти и обновляем остатки
        total_cost = 0
        for part_id, qty in parts_used:
            # Получаем цену и текущий остаток
            cursor.execute('SELECT quantity, price FROM parts WHERE id = ?', (part_id,))
            res = cursor.fetchone()
            if not res:
                continue
            current_qty, price = res
            
            if qty > current_qty:
                raise ValueError(f"Недостаточно запчасти ID {part_id}. Есть: {current_qty}, нужно: {qty}")
            
            # Обновляем остаток
            new_qty = current_qty - qty
            cursor.execute('UPDATE parts SET quantity = ?, last_updated = ? WHERE id = ?', 
                           (new_qty, datetime.now(), part_id))
            
            # Добавляем в список использованных
            cursor.execute('INSERT INTO repair_parts (repair_id, part_id, quantity_used) VALUES (?, ?, ?)',
                           (repair_id, part_id, qty))
            
            total_cost += qty * price
        
        # 3. Обновляем общую стоимость ремонта
        cursor.execute('UPDATE repairs SET total_cost = ? WHERE id = ?', (total_cost, repair_id))
        conn.commit()
        return True
    except ValueError as ve:
        st.error(ve)
        conn.rollback()
        return False
    except Exception as e:
        st.error(f"Критическая ошибка при создании ремонта: {e}")
        conn.rollback()
        return False

# --- ИНТЕРФЕЙС ---

# Боковая панель
st.sidebar.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=100)
st.sidebar.title("🔧 Склад Механика PRO")
page = st.sidebar.radio("Навигация", ["📦 Остатки на складе", "🛠 Создать ремонт", "➕ Добавить запчасть"])

st.divider()

if page == "📦 Остатки на складе":
    st.header("📦 Текущие остатки")
    
    # Фильтр
    col1, col2 = st.columns([3, 1])
    search_term = col1.text_input("Поиск запчасти (по названию или артикулу)", "")
    show_low = col2.checkbox("Только остатки < 5", value=False)
    
    cursor = conn.cursor()
    if search_term:
        query = "SELECT * FROM parts WHERE name LIKE ? OR article LIKE ?"
        cursor.execute(query, (f"%{search_term}%", f"%{search_term}%"))
    else:
        cursor.execute("SELECT * FROM parts")
    
    parts = cursor.fetchall()
    
    if show_low:
        parts = [p for p in parts if p < 5] # p это quantity
        
    if not parts:
        st.info("Запчасти не найдены.")
    else:
        # Красивый вывод таблицы
        df_data = []
        for p in parts:
            status = "⚠️ Мало" if p < 5 else "✅ В норме"
            color = "orange" if p < 5 else "green"
            df_data.append({
                "ID": p,
                "Название": p,
                "Артикул": p or "-",
                "Остаток": p,
                "Цена": f"{p:.2f} ₽",
                "Статус": f"<span style='color: {color}; font-weight: bold;'>{status}</span>"
            })
        
        # Отображение таблицы (без HTML тегов в st.dataframe, используем st.table для простоты или custom)
        st.dataframe(df_data, use_container_width=True, hide_index=True)
        
        # Кнопка экспорта (опционально)
        if st.button("💾 Скачать отчет (CSV)"):
            import pandas as pd
            df = pd.DataFrame(df_data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Скачать CSV", csv, "report.csv", "text/csv")

elif page == "🛠 Создать ремонт":
    st.header("🛠 Оформление ремонта")
    
    with st.form("repair_form"):
        col1, col2 = st.columns(2)
        car_model = col1.text_input("Модель авто", required=True)
        client_name = col2.text_input("Имя клиента")
        description = st.text_area("Описание работ", placeholder="Замена масла, ремонт подвески...")
        
        st.subheader("Использованные запчасти")
        
        # Получаем все запчасти для выбора
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, quantity, price FROM parts")
        all_parts = cursor.fetchall()
        
        parts_to_use = []
        
        # Динамическое добавление строк выбора запчастей
        num_parts = st.number_input("Сколько разных запчастей использовать?", min_value=1, value=1, step=1)
        
        for i in range(num_parts):
            col_p, col_q = st.columns([3, 1])
            part_options = [(p, p) for p in all_parts] # (name, id)
            part_id = col_p.selectbox(f"Запчасть {i+1}", options=part_options, format_func=lambda x: x)
            qty = col_q.number_input(f"Кол-во {i+1}", min_value=1, value=1, key=f"qty_{i}")
            parts_to_use.append((part_id, qty))
        
        submitted = st.form_submit_button("Оформить ремонт", type="primary")
        
        if submitted:
            if create_repair(car_model, client_name, description, parts_to_use):
                st.success("✅ Ремонт оформлен! Запчасти списаны со склада.")
                st.rerun()

elif page == "➕ Добавить запчасть":
    st.header("➕ Добавление новой запчасти")
    
    with st.form("add_part_form"):
        col1, col2 = st.columns(2)
        name = col1.text_input("Название запчасти", required=True)
        article = col2.text_input("Артикул (опционально)")
        
        col3, col4 = st.columns(2)
        qty = col3.number_input("Количество на складе", min_value=0, value=0)
        price = col4.number_input("Цена за штуку (₽)", min_value=0.0, value=0.0, step=0.01)
        
        submitted = st.form_submit_button("Добавить на склад", type="primary")
        
        if submitted:
            if add_part(name, article, qty, price):
                st.success("✅ Запчасть успешно добавлена!")
                st.rerun()
