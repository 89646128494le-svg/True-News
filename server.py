# -*- coding: utf-8 -*-
"""
True News Backend Server
Flask + SQLite база данных для новостного портала и darkweb площадки
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)

# Настройки базы данных
DATABASE = 'truenews.db'

# ============ ИНИЦИАЛИЗАЦИЯ БД ============

def init_db():
    """Создание всех таблиц базы данных"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Таблица пользователей (обычный сайт)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Таблица новостей
    c.execute('''CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        preview TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Таблица darkweb пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS darkweb_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        reputation INTEGER DEFAULT 0,
        balance INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )''')

    # Таблица товаров маркета
    c.execute('''CREATE TABLE IF NOT EXISTS market_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price TEXT NOT NULL,
        category TEXT NOT NULL,
        seller_id INTEGER NOT NULL,
        seller_name TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        views INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES darkweb_users(id)
    )''')

    # Таблица группировок
    c.execute('''CREATE TABLE IF NOT EXISTS gangs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        territory TEXT NOT NULL,
        leader_id INTEGER NOT NULL,
        leader_name TEXT NOT NULL,
        reputation INTEGER DEFAULT 100,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (leader_id) REFERENCES darkweb_users(id)
    )''')

    # Таблица участников группировок
    c.execute('''CREATE TABLE IF NOT EXISTS gang_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gang_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (gang_id) REFERENCES gangs(id),
        FOREIGN KEY (user_id) REFERENCES darkweb_users(id)
    )''')

    # Таблица чатов
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        seller_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        sender TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES market_items(id)
    )''')

    # Таблица заказов адвокатов
    c.execute('''CREATE TABLE IF NOT EXISTS lawyer_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT NOT NULL,
        client_name TEXT NOT NULL,
        client_email TEXT NOT NULL,
        client_phone TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Таблица приглашений darkweb
    c.execute('''CREATE TABLE IF NOT EXISTS invite_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT UNIQUE NOT NULL,
        used BOOLEAN DEFAULT 0,
        used_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Добавляем начальные данные
    c.execute("SELECT COUNT(*) FROM news")
    if c.fetchone()[0] == 0:
        initial_news = [
            ("Трагедия в центре города", "Происшествия", 
             "Сегодня днём произошло трагическое событие...",
             "Полный текст о трагедии в центре города. Сотрудники полиции работают на месте.",
             "admin", "24.10.2025", "10:00"),
            ("Городской совет обсудил бюджет", "Политика",
             "На заседании обсуждались основные направления...",
             "Подробности обсуждения бюджета городского совета.",
             "admin", "24.10.2025", "09:30")
        ]
        c.executemany("INSERT INTO news (title, category, preview, content, author, date, time) VALUES (?, ?, ?, ?, ?, ?, ?)", initial_news)

    # Добавляем приглашения
    c.execute("SELECT COUNT(*) FROM invite_links")
    if c.fetchone()[0] == 0:
        invites = [
            "https://invite.to/rp-market/phantom666",
            "https://invite.to/rp-market/shadow2025",
            "https://invite.to/rp-market/elite999"
        ]
        c.executemany("INSERT INTO invite_links (link) VALUES (?)", [(link,) for link in invites])

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована!")

# ============ УТИЛИТЫ ============

def hash_password(password):
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    """Получение соединения с БД"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ============ API ENDPOINTS ============

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

# === ПОЛЬЗОВАТЕЛИ ===

@app.route('/api/register', methods=['POST'])
def register():
    """Регистрация обычного пользователя"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Заполните все поля'}), 400

    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  (username, hash_password(password), role))
        conn.commit()
        return jsonify({'success': True, 'message': 'Регистрация успешна!', 'username': username})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Пользователь уже существует'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    """Вход пользователя"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?",
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()

    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({
            'success': True,
            'user': {
                'username': user['username'],
                'role': user['role']
            }
        })
    return jsonify({'success': False, 'message': 'Неверный логин или пароль'}), 401

# === НОВОСТИ ===

@app.route('/api/news', methods=['GET'])
def get_news():
    """Получить все новости"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM news ORDER BY id DESC")
    news = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'news': news})

@app.route('/api/news', methods=['POST'])
def create_news():
    """Создать новость"""
    data = request.json

    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO news (title, category, preview, content, author, date, time)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (data['title'], data['category'], data['preview'], data['content'],
               data['author'], data['date'], data['time']))
    conn.commit()
    news_id = c.lastrowid
    conn.close()

    return jsonify({'success': True, 'id': news_id})

@app.route('/api/news/<int:news_id>', methods=['DELETE'])
def delete_news(news_id):
    """Удалить новость"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM news WHERE id = ?", (news_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# === DARKWEB ===

@app.route('/api/darkweb/register', methods=['POST'])
def darkweb_register():
    """Регистрация darkweb пользователя"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("INSERT INTO darkweb_users (username, password_hash) VALUES (?, ?)",
                  (username, hash_password(password)))
        conn.commit()
        user_id = c.lastrowid
        return jsonify({'success': True, 'user_id': user_id, 'username': username})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Пользователь уже существует'}), 400
    finally:
        conn.close()

@app.route('/api/darkweb/login', methods=['POST'])
def darkweb_login():
    """Вход darkweb"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM darkweb_users WHERE username = ? AND password_hash = ?",
              (username, hash_password(password)))
    user = c.fetchone()

    if user:
        c.execute("UPDATE darkweb_users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
        conn.commit()
        conn.close()
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'reputation': user['reputation']
            }
        })
    conn.close()
    return jsonify({'success': False, 'message': 'Неверные данные'}), 401

@app.route('/api/darkweb/verify-invite', methods=['POST'])
def verify_invite():
    """Проверка приглашения"""
    data = request.json
    link = data.get('link')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM invite_links WHERE link = ? AND used = 0", (link,))
    invite = c.fetchone()

    if invite:
        c.execute("UPDATE invite_links SET used = 1, used_by = ? WHERE id = ?",
                  (data.get('username', 'unknown'), invite['id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    conn.close()
    return jsonify({'success': False, 'message': 'Неверная или использованная ссылка'}), 400

# === МАРКЕТ ===

@app.route('/api/market/items', methods=['GET'])
def get_market_items():
    """Получить товары"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM market_items WHERE status = 'active' ORDER BY id DESC")
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'items': items})

@app.route('/api/market/items', methods=['POST'])
def create_market_item():
    """Создать товар"""
    data = request.json

    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO market_items (name, description, price, category, seller_id, seller_name)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (data['name'], data['description'], data['price'], data['category'],
               data['seller_id'], data['seller_name']))
    conn.commit()
    item_id = c.lastrowid
    conn.close()

    return jsonify({'success': True, 'id': item_id})

@app.route('/api/market/items/<int:item_id>', methods=['DELETE'])
def delete_market_item(item_id):
    """Удалить товар"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE market_items SET status = 'deleted' WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# === ГРУППИРОВКИ ===

@app.route('/api/gangs', methods=['GET'])
def get_gangs():
    """Получить группировки"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT g.*, COUNT(gm.id) as members 
                 FROM gangs g 
                 LEFT JOIN gang_members gm ON g.id = gm.gang_id 
                 GROUP BY g.id""")
    gangs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'gangs': gangs})

@app.route('/api/gangs', methods=['POST'])
def create_gang():
    """Создать группировку"""
    data = request.json

    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO gangs (name, territory, leader_id, leader_name)
                 VALUES (?, ?, ?, ?)""",
              (data['name'], data['territory'], data['leader_id'], data['leader_name']))
    conn.commit()
    gang_id = c.lastrowid
    conn.close()

    return jsonify({'success': True, 'id': gang_id})

# === СТАТИСТИКА АДМИНА ===

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    """Статистика для админ панели"""
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) as count FROM users")
    users_count = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM darkweb_users")
    darkweb_users_count = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM news")
    news_count = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM market_items WHERE status = 'active'")
    items_count = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM gangs")
    gangs_count = c.fetchone()['count']

    conn.close()

    return jsonify({
        'success': True,
        'stats': {
            'users': users_count,
            'darkweb_users': darkweb_users_count,
            'news': news_count,
            'market_items': items_count,
            'gangs': gangs_count
        }
    })

# ============ ЗАПУСК СЕРВЕРА ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)


