import requests
import time
import json
import random
from datetime import datetime, timedelta
import threading
from flask import Flask, request, jsonify
from werkzeug.serving import make_server

# === НАСТРОЙКИ ===
TOKEN = "8466725404:AAFsxikWr8541rgTZcpxZdBXqdO-1qra4Mo"
ADMIN_CHAT_ID = "6319679398"
WITHDRAW_BOT_USERNAME = "OksajdShop_Raketa_bot"
BOT_USERNAME = "Raketa_oxide_bot"
STATS_CHANNEL_ID = "-1003002379769"
STATS_MESSAGE_ID = 832
MAIN_GROUP_ID = "-1003117157578"
GROUP_INVITE_LINK = "https://t.me/+bjAMAhtua9xmNzgy"
WEB_APP_URL = "https://ваш-домен.vercel.app/webapp.html"  # Замените на ваш URL
WEB_APP_PORT = 8080

# Права доступа
ADMIN_IDS = ["6319675398", "6999365345"]

# Стоимость админ-услуг
ADMIN_PRICES = {
    'mute': 50,      # мут на 30 минут
    'ban': 100,      # бан на 1 день
    'kick': 15,      # кик
    'delete': 5,     # удаление сообщения
    'unmute': 20,    # размут
    'unban': 40      # разбан
}

# Глобальные переменные
users_data = {}
treasury = 25
last_treasury_update = time.time()
withdraw_codes = {}
withdraw_requests = {}
last_update_id = 0
groups_data = {}  # Данные о группах
active_games = {}  # Активные игры в крестики-нолики
web_app_requests = {}  # Запросы от Web App
flask_app = None  # Flask приложение
flask_server = None  # Flask сервер

# === FLASK WEB APP SERVER ===
class WebAppServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_routes()
        self.server = None
        self.thread = None
        
    def setup_routes(self):
        @self.app.route('/')
        def index():
            return "Web App API Server - Rocket 3.0", 200
        
        @self.app.route('/api/get_user_data', methods=['GET'])
        def get_user_data():
            try:
                user_id = request.args.get('user_id')
                if not user_id:
                    return jsonify({'success': False, 'error': 'No user_id'})
                
                global users_data, treasury
                
                if user_id in users_data:
                    user_data = users_data[user_id]
                    return jsonify({
                        'success': True,
                        'balance': user_data.get('balance', 0),
                        'business_level': user_data.get('business_level', 0),
                        'treasury': treasury,
                        'last_robbery_time': user_data.get('last_robbery_time', 0),
                        'last_casino_time': user_data.get('last_casino_time', 0),
                        'robbery_count': user_data.get('robbery_count', 0),
                        'daily_robbery_earnings': user_data.get('daily_robbery_earnings', 0),
                        'last_daily_bonus': user_data.get('last_daily_bonus', ''),
                        'last_robbery_date': user_data.get('last_robbery_date', '')
                    })
                
                # Если пользователя нет, создаем базовую запись
                users_data[user_id] = {
                    'username': f'user_{user_id}',
                    'balance': 0,
                    'business_level': 0,
                    'last_robbery_time': 0,
                    'last_casino_time': 0,
                    'robbery_count': 0,
                    'daily_robbery_earnings': 0,
                    'last_daily_bonus': None,
                    'last_robbery_date': datetime.now().strftime("%Y-%m-%d")
                }
                save_data()
                
                return jsonify({
                    'success': True,
                    'balance': 0,
                    'business_level': 0,
                    'treasury': treasury,
                    'last_robbery_time': 0,
                    'last_casino_time': 0,
                    'robbery_count': 0,
                    'daily_robbery_earnings': 0,
                    'last_daily_bonus': '',
                    'last_robbery_date': datetime.now().strftime("%Y-%m-%d")
                })
                
            except Exception as e:
                print(f"❌ Web App Error (get_user_data): {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/get_bot_stats', methods=['GET'])
        def get_bot_stats():
            try:
                user_id = request.args.get('user_id')
                
                global users_data, treasury, active_games
                
                # Рейтинг пользователя
                user_rank = None
                if user_id and user_id in users_data:
                    sorted_users = sorted(
                        [(uid, ud.get('balance', 0)) for uid, ud in users_data.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )
                    
                    for rank, (uid, _) in enumerate(sorted_users, 1):
                        if uid == user_id:
                            user_rank = rank
                            break
                
                return jsonify({
                    'success': True,
                    'total_users': len(users_data),
                    'treasury': treasury,
                    'active_games': len(active_games),
                    'user_rank': user_rank
                })
                
            except Exception as e:
                print(f"❌ Web App Error (get_bot_stats): {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/rob_treasury', methods=['POST'])
        def rob_treasury():
            try:
                data = request.json
                user_id = str(data.get('user_id'))
                username = data.get('username', f'user_{user_id}')
                
                global users_data, treasury, last_treasury_update
                
                # Создаем пользователя если не существует
                if user_id not in users_data:
                    users_data[user_id] = {
                        'username': username,
                        'balance': 0,
                        'business_level': 0,
                        'last_income': 0,
                        'robbery_count': 0,
                        'last_robbery_date': datetime.now().strftime("%Y-%m-%d"),
                        'last_robbery_time': 0,
                        'last_daily_bonus': None,
                        'last_casino_time': 0,
                        'daily_robbery_earnings': 0
                    }
                
                user_data = users_data[user_id]
                current_time = time.time()
                
                # Проверяем кулдаун (30 минут)
                if current_time - user_data.get('last_robbery_time', 0) < 1800:
                    return jsonify({
                        'success': False,
                        'message': 'Подождите 30 минут до следующего ограбления'
                    })
                
                # Проверяем дневной лимит (3 ограбления в день)
                today = datetime.now().strftime("%Y-%m-%d")
                if user_data.get('last_robbery_date') != today:
                    user_data['robbery_count'] = 0
                    user_data['daily_robbery_earnings'] = 0
                    user_data['last_robbery_date'] = today
                
                if user_data.get('robbery_count', 0) >= 3:
                    return jsonify({
                        'success': False,
                        'message': 'Достигнут дневной лимит ограблений (3/день)'
                    })
                
                # Обновляем казну (каждые 2 часа)
                if current_time - last_treasury_update > 7200:
                    treasury = random.randint(25, 100)
                    last_treasury_update = current_time
                
                # Шанс успеха 90%
                success = random.random() <= 0.9
                
                if success:
                    stolen_amount = random.randint(1, min(20, treasury))
                    treasury -= stolen_amount
                    if treasury < 0:
                        treasury = 0
                    
                    user_data['balance'] = user_data.get('balance', 0) + stolen_amount
                    user_data['robbery_count'] = user_data.get('robbery_count', 0) + 1
                    user_data['daily_robbery_earnings'] = user_data.get('daily_robbery_earnings', 0) + stolen_amount
                    user_data['last_robbery_time'] = current_time
                    
                    result = {
                        'success': True,
                        'stolen_amount': stolen_amount,
                        'new_balance': user_data['balance'],
                        'new_treasury': treasury
                    }
                else:
                    user_data['robbery_count'] = user_data.get('robbery_count', 0) + 1
                    user_data['last_robbery_time'] = current_time
                    
                    result = {
                        'success': True,
                        'stolen_amount': 0,
                        'new_balance': user_data['balance'],
                        'new_treasury': treasury
                    }
                
                save_data()
                update_stats_message()
                
                return jsonify(result)
                
            except Exception as e:
                print(f"❌ Web App Error (rob_treasury): {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/play_casino', methods=['POST'])
        def play_casino():
            try:
                data = request.json
                user_id = str(data.get('user_id'))
                username = data.get('username', f'user_{user_id}')
                amount = int(data.get('amount', 0))
                
                global users_data
                
                if user_id not in users_data:
                    users_data[user_id] = {
                        'username': username,
                        'balance': 0,
                        'business_level': 0,
                        'last_income': 0,
                        'robbery_count': 0,
                        'last_robbery_date': datetime.now().strftime("%Y-%m-%d"),
                        'last_robbery_time': 0,
                        'last_daily_bonus': None,
                        'last_casino_time': 0,
                        'daily_robbery_earnings': 0
                    }
                
                user_data = users_data[user_id]
                balance = user_data.get('balance', 0)
                
                if amount <= 0:
                    return jsonify({'success': False, 'error': 'Ставка должна быть положительной'})
                
                if balance < amount:
                    return jsonify({'success': False, 'error': 'Недостаточно средств'})
                
                # Проверяем кулдаун (10 секунд)
                current_time = time.time()
                if current_time - user_data.get('last_casino_time', 0) < 10:
                    return jsonify({'success': False, 'error': 'Подождите 10 секунд'})
                
                # Шанс выигрыша 30%
                win = random.randint(1, 100) <= 30
                
                if win:
                    win_amount = amount * 2
                    user_data['balance'] = balance + win_amount
                    result = {
                        'success': True,
                        'win': True,
                        'win_amount': win_amount,
                        'new_balance': user_data['balance']
                    }
                else:
                    user_data['balance'] = balance - amount
                    result = {
                        'success': True,
                        'win': False,
                        'new_balance': user_data['balance']
                    }
                
                user_data['last_casino_time'] = current_time
                save_data()
                update_stats_message()
                
                return jsonify(result)
                
            except Exception as e:
                print(f"❌ Web App Error (play_casino): {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/daily_bonus', methods=['POST'])
        def daily_bonus():
            try:
                data = request.json
                user_id = str(data.get('user_id'))
                username = data.get('username', f'user_{user_id}')
                
                global users_data
                
                if user_id not in users_data:
                    users_data[user_id] = {
                        'username': username,
                        'balance': 0,
                        'business_level': 0,
                        'last_income': 0,
                        'robbery_count': 0,
                        'last_robbery_date': datetime.now().strftime("%Y-%m-%d"),
                        'last_robbery_time': 0,
                        'last_daily_bonus': None,
                        'last_casino_time': 0,
                        'daily_robbery_earnings': 0
                    }
                
                user_data = users_data[user_id]
                today = datetime.now().strftime("%Y-%m-%d")
                
                if user_data.get('last_daily_bonus') == today:
                    return jsonify({
                        'success': False,
                        'message': 'Бонус уже получен сегодня'
                    })
                
                bonus_amount = 5
                user_data['balance'] = user_data.get('balance', 0) + bonus_amount
                user_data['last_daily_bonus'] = today
                
                save_data()
                update_stats_message()
                
                return jsonify({
                    'success': True,
                    'bonus_amount': bonus_amount,
                    'new_balance': user_data['balance']
                })
                
            except Exception as e:
                print(f"❌ Web App Error (daily_bonus): {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/full_stats', methods=['GET'])
        def full_stats():
            try:
                user_id = request.args.get('user_id')
                
                global users_data, treasury, active_games
                
                total_balance = sum(user.get('balance', 0) for user in users_data.values())
                business_users = len([user for user in users_data.values() if user.get('business_level', 0) > 0])
                
                # Топ 5 пользователей
                top_users = sorted(
                    [(user.get('username', 'user'), user.get('balance', 0)) 
                     for user in users_data.values()],
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                # Рейтинг пользователя
                user_rank = None
                user_stats = {}
                
                if user_id and user_id in users_data:
                    sorted_users = sorted(
                        [(uid, ud.get('balance', 0)) for uid, ud in users_data.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )
                    
                    for rank, (uid, _) in enumerate(sorted_users, 1):
                        if uid == user_id:
                            user_rank = rank
                            break
                    
                    user_data = users_data[user_id]
                    user_stats = {
                        'balance': user_data.get('balance', 0),
                        'robbery_count': user_data.get('robbery_count', 0),
                        'business_level': user_data.get('business_level', 0),
                        'games_played': user_data.get('games_played', 0)
                    }
                
                return jsonify({
                    'success': True,
                    'total_users': len(users_data),
                    'total_balance': total_balance,
                    'business_users': business_users,
                    'treasury': treasury,
                    'active_games': len(active_games),
                    'top_users': [{'username': u[0], 'balance': u[1]} for u in top_users],
                    'user_rank': user_rank,
                    'user_stats': user_stats
                })
                
            except Exception as e:
                print(f"❌ Web App Error (full_stats): {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/transfer_money', methods=['POST'])
        def transfer_money():
            try:
                data = request.json
                from_user_id = str(data.get('from_user_id'))
                to_user_id = str(data.get('to_user_id'))
                amount = int(data.get('amount', 0))
                
                global users_data
                
                if from_user_id not in users_data:
                    return jsonify({'success': False, 'error': 'Отправитель не найден'})
                
                if to_user_id not in users_data:
                    return jsonify({'success': False, 'error': 'Получатель не найден'})
                
                if from_user_id == to_user_id:
                    return jsonify({'success': False, 'error': 'Нельзя переводить себе'})
                
                if amount <= 0:
                    return jsonify({'success': False, 'error': 'Сумма должна быть положительной'})
                
                from_user = users_data[from_user_id]
                to_user = users_data[to_user_id]
                
                if from_user.get('balance', 0) < amount:
                    return jsonify({'success': False, 'error': 'Недостаточно средств'})
                
                from_user['balance'] = from_user.get('balance', 0) - amount
                to_user['balance'] = to_user.get('balance', 0) + amount
                
                save_data()
                update_stats_message()
                
                return jsonify({
                    'success': True,
                    'from_balance': from_user['balance'],
                    'to_balance': to_user['balance'],
                    'message': f'Перевод {amount}₽ выполнен успешно'
                })
                
            except Exception as e:
                print(f"❌ Web App Error (transfer_money): {e}")
                return jsonify({'success': False, 'error': str(e)})
    
    def start(self, port=8080):
        """Запуск Flask сервера в отдельном потоке"""
        def run():
            self.server = make_server('0.0.0.0', port, self.app)
            self.server.serve_forever()
        
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        print(f"✅ Web App сервер запущен на порту {port}")
    
    def stop(self):
        """Остановка Flask сервера"""
        if self.server:
            self.server.shutdown()

# === ОСНОВНЫЕ ФУНКЦИИ ===
def is_command_for_me(text, command):
    """Проверяет, адресована ли команда боту"""
    if not text:
        return False

    clean_command = command.split('@')[0]
    variants = [
        clean_command,
        clean_command + f'@{BOT_USERNAME}',
        clean_command + f'@{BOT_USERNAME.lower()}'
    ]
    return any(text.startswith(variant) for variant in variants)

def has_admin_rights(user_id):
    """Проверяет права администратора"""
    return str(user_id) in ADMIN_IDS

def is_group_admin(chat_id, user_id):
    """Проверяет, является ли пользователь администратором группы"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getChatMember"
        payload = {
            'chat_id': chat_id,
            'user_id': user_id
        }
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            status = data.get('result', {}).get('status', '')
            return status in ['creator', 'administrator']
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки прав администратора: {e}")
        return False

def save_data():
    """Сохранение данных в файл"""
    global users_data, treasury, last_treasury_update, withdraw_codes, withdraw_requests, groups_data
    try:
        data = {
            'users_data': users_data,
            'treasury': treasury,
            'last_treasury_update': last_treasury_update,
            'withdraw_codes': withdraw_codes,
            'withdraw_requests': withdraw_requests,
            'groups_data': groups_data
        }
        with open('bot_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("💾 Данные сохранены")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения данных: {e}")
        return False

def load_data():
    """Загрузка данных из файла"""
    global users_data, treasury, last_treasury_update, withdraw_codes, withdraw_requests, groups_data, active_games
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            users_data = data.get('users_data', {})
            treasury = data.get('treasury', 25)
            last_treasury_update = data.get('last_treasury_update', time.time())
            withdraw_codes = data.get('withdraw_codes', {})
            withdraw_requests = data.get('withdraw_requests', {})
            groups_data = data.get('groups_data', {})
        active_games = {}  # Инициализируем пустые активные игры
        print("📂 Данные загружены")
        print(f"👥 Пользователей: {len(users_data)}")
        print(f"💰 Казна: {treasury}₽")
        print(f"👥 Групп: {len(groups_data)}")
        return True
    except FileNotFoundError:
        print("❌ Файл данных не найден, создаем новый...")
        users_data = {}
        treasury = 25
        last_treasury_update = time.time()
        withdraw_codes = {}
        withdraw_requests = {}
        groups_data = {}
        active_games = {}
        return True
    except Exception as e:
        print(f"❌ Ошибка при загрузке данных: {e}")
        users_data = {}
        treasury = 25
        last_treasury_update = time.time()
        withdraw_codes = {}
        withdraw_requests = {}
        groups_data = {}
        active_games = {}
        return False

def is_group_allowed(chat_id):
    """Проверяет, разрешена ли группа для использования бота"""
    return str(chat_id) in groups_data and groups_data[str(chat_id)].get('enabled', False)

def enable_group(chat_id, chat_title=None):
    """Включает бота для группы"""
    if chat_title is None:
        chat_title = f"Группа {chat_id}"

    groups_data[str(chat_id)] = {
        'title': chat_title,
        'enabled': True,
        'admin_actions_enabled': False,
        'added_by': "console",
        'added_date': datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_data()
    print(f"✅ Группа '{chat_title}' ({chat_id}) включена")

def disable_group(chat_id):
    """Выключает бота для группы"""
    if str(chat_id) in groups_data:
        groups_data[str(chat_id)]['enabled'] = False
        save_data()
        print(f"❌ Группа {chat_id} отключена")

def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Ошибка отправки в {chat_id}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")
        return False

def delete_message(chat_id, message_id):
    """Удаление сообщения"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id
        }

        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка удаления сообщения: {e}")
        return False

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Редактирование сообщения"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup

        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка редактирования сообщения: {e}")
        return False

def update_stats_message():
    """Обновление сообщения со статистикой"""
    try:
        stats_text = generate_stats_text()
        success = edit_message(STATS_CHANNEL_ID, STATS_MESSAGE_ID, stats_text)
        if success:
            print("✅ Статистика обновлена")
        else:
            print("❌ Не удалось обновить статистику")
        return success
    except Exception as e:
        print(f"❌ Ошибка обновления статистики: {e}")
        return False

def generate_stats_text():
    """Генерирует текст статистики"""
    total_users = len(users_data)
    total_balance = sum(user_data.get('balance', 0) for user_data in users_data.values())
    business_users = len([user_data for user_data in users_data.values() if user_data.get('business_level', 0) > 0])

    available_codes = len([c for c in withdraw_codes.values() if not c['used']])
    used_codes = len([c for c in withdraw_codes.values() if c['used']])

    # Топ 5 пользователей по балансу (исключая админов)
    top_users = []
    for user_id, user_data in users_data.items():
        if str(user_id) not in ADMIN_IDS:
            top_users.append({
                'username': user_data.get('username', 'user'),
                'balance': user_data.get('balance', 0),
                'business_level': user_data.get('business_level', 0)
            })

    # Сортируем по балансу (по убыванию)
    top_users.sort(key=lambda x: x['balance'], reverse=True)
    top_5_users = top_users[:5]

    # Список активных групп
    active_groups = [g for g in groups_data.values() if g.get('enabled')]
    inactive_groups = [g for g in groups_data.values() if not g.get('enabled')]

    stats_text = (
        f"📊 <b>СТАТИСТИКА БОТА РАКЕТА 3.0</b>\n\n"
        f"👥 <b>Общая статистика:</b>\n"
        f"• Пользователей: {total_users}\n"
        f"• Общий баланс: {total_balance}₽\n"
        f"• Владельцев бизнеса: {business_users}\n"
        f"• Казна: {treasury}₽\n"
        f"• Групп: {len(groups_data)} ({len(active_groups)} актив.)\n"
        f"• Активных игр: {len(active_games)}\n\n"
        f"🎫 <b>Коды вывода:</b>\n"
        f"• Доступно: {available_codes}\n"
        f"• Использовано: {used_codes}\n"
        f"• Сумма к выплате: {available_codes * 50}₽\n\n"
        f"🏆 <b>ТОП-5 ПОЛЬЗОВАТЕЛЕЙ:</b>\n"
    )

    if top_5_users:
        for i, user in enumerate(top_5_users, 1):
            medal = ""
            if i == 1: medal = "🥇"
            elif i == 2: medal = "🥈"
            elif i == 3: medal = "🥉"
            else: medal = f"{i}."

            business_info = ""
            if user['business_level'] > 0:
                business_info = f" | 🏢 Ур.{user['business_level']}"

            stats_text += f"{medal} @{user['username']} - {user['balance']}₽{business_info}\n"
    else:
        stats_text += "Пока нет активных пользователей\n"

    stats_text += f"\n🕒 <i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"

    return stats_text

def send_group_invite_message(chat_id):
    """Отправляет сообщение со ссылкой на группу"""
    message = (
        f"🚫 <b>Бот работает только в разрешенных группах!</b>\n\n"
        f"💎 <b>Присоединяйтесь к нашей основной группе:</b>\n"
        f"👉 {GROUP_INVITE_LINK}\n\n"
        f"🎮 <b>В группе вас ждут:</b>\n"
        f"• Заработок денег\n"
        f"• Игра в казино\n"
        f"• Ограбление казны\n"
        f"• Бизнес-система\n"
        f"• Вывод средств\n"
        f"• Крестики-нолики\n\n"
        f"⚡ <b>Начните зарабатывать прямо сейчас!</b>"
    )
    send_message(chat_id, message)

def send_bot_started_message():
    """Отправляет сообщение о запуске бота в группу и консоль"""
    # Сообщение в консоль
    console_message = f"""
╔══════════════════════════════╗
║         🤖 БОТ ЗАПУЩЕН!      ║
╠══════════════════════════════╣
║ 📍 Web App: {WEB_APP_URL}
║ 📍 Основная группа: {MAIN_GROUP_ID}
║ 👑 Админы: {ADMIN_IDS}
║ 🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}
║ 👥 Пользователей: {len(users_data)}
║ 💰 Казна: {treasury}₽
║ 👥 Групп: {len(groups_data)}
╚══════════════════════════════╝
⚡ Бот готов к работе!

🌐 Web App доступен по команде /webapp
    """
    print(console_message)

    # Сообщение в основную группу
    group_message = (
        f"🤖 <b>БОТ РАКЕТА 3.0 ЗАПУЩЕН!</b>\n\n"
        f"✅ <b>Система активирована и готова к работе!</b>\n\n"
        f"🌐 <b>НОВЫЙ WEB APP!</b>\n"
        f"• Откройте через команду /webapp\n"
        f"• Работает на любом устройстве\n"
        f"• Все функции бота в одном месте\n\n"
        f"📊 <b>Текущая статистика:</b>\n"
        f"• 👥 Пользователей: {len(users_data)}\n"
        f"• 💰 Казна: {treasury}₽\n"
        f"• 👥 Групп: {len(groups_data)}\n"
        f"• 🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"🎮 <b>Доступные команды:</b>\n"
        f"• /balance - ваш баланс\n"
        f"• /bonus - ежедневный бонус\n"
        f"• ограбить казну - ограбление\n"
        f"• казино [сумма] - игра в казино\n"
        f"• админка - привилегии\n"
        f"• играть [ставка] - крестики-нолики\n"
        f"• /webapp - открыть Web App\n\n"
        f"⚡ <b>Удачи в заработке!</b>"
    )

    # Отправляем сообщение в основную группу
    success = send_message(MAIN_GROUP_ID, group_message)
    if success:
        print("✅ Сообщение о запуске отправлено в основную группу")
    else:
        print("❌ Не удалось отправить сообщение в группу")

# === WEB APP КОМАНДА ===
def handle_webapp_command(chat_id, user_id, username):
    """Команда для открытия Web App"""
    keyboard = {
        "inline_keyboard": [[
            {"text": "🚀 Открыть Web App", "web_app": {"url": WEB_APP_URL}}
        ]]
    }
    
    send_message(chat_id,
                f"🌐 <b>Web App Ракета 3.0</b>\n\n"
                f"👤 <b>Для:</b> @{username}\n"
                f"📱 <b>Доступно:</b> На любом устройстве\n"
                f"🔗 <b>Ссылка:</b> {WEB_APP_URL}\n\n"
                f"🎮 <b>Возможности:</b>\n"
                f"• Полная статистика бота\n"
                f"• Ограбление казны\n"
                f"• Крестики-нолики (скоро)\n"
                f"• Казино 30%\n"
                f"• Бизнес-система\n"
                f"• Перевод денег\n"
                f"• Ежедневный бонус\n\n"
                f"👇 <b>Нажмите кнопку ниже чтобы открыть:</b>",
                keyboard)

# === ОСНОВНЫЕ КОМАНДЫ БОТА ===
def handle_start(chat_id, user_id, username):
    """Обработка команды /start"""
    print(f"👋 Обработка /start от @{username} в чате {chat_id}")

    if str(chat_id) == str(ADMIN_CHAT_ID):
        # Админское меню в ЛС
        if has_admin_rights(user_id):
            available_codes = len([c for c in withdraw_codes.values() if not c['used']])
            used_codes = len([c for c in withdraw_codes.values() if c['used']])

            # Список групп
            groups_list = ""
            for group_id, group_data in groups_data.items():
                status = "✅" if group_data.get('enabled') else "❌"
                admin_actions = "🛠️" if group_data.get('admin_actions_enabled') else "🚫"
                groups_list += f"{status} {admin_actions} {group_data.get('title', 'Неизвестно')} (<code>{group_id}</code>)\n"

            if not groups_list:
                groups_list = "Нет зарегистрированных групп"

            send_message(chat_id,
                        f"🛠️ <b>АДМИН ПАНЕЛЬ</b>\n\n"
                        f"🌐 <b>Web App:</b>\n"
                        f"• URL: {WEB_APP_URL}\n"
                        f"• Порт: {WEB_APP_PORT}\n\n"
                        f"🎫 <b>Коды вывода:</b>\n"
                        f"• Доступно: {available_codes}\n"
                        f"• Использовано: {used_codes}\n\n"
                        f"📊 <b>Статистика:</b>\n"
                        f"• Пользователей: {len(users_data)}\n"
                        f"• Общий баланс: {sum(user_data.get('balance', 0) for user_data in users_data.values())}₽\n"
                        f"• Групп: {len(groups_data)}\n"
                        f"• Активных игр: {len(active_games)}\n\n"
                        f"👥 <b>Группы:</b>\n{groups_list}\n\n"
                        f"💡 <b>Управление группами:</b>\n"
                        f"Используйте команды:\n"
                        f"• <code>группы</code> - управление группами\n"
                        f"• <code>список_групп</code> - список групп\n"
                        f"• <code>включить ID_группы</code> - включить группу\n"
                        f"• <code>выключить ID_группы</code> - выключить группу")
        else:
            send_message(chat_id, "❌ <b>У вас нет прав доступа!</b>")
    else:
        # Обычное меню в ЛС
        send_message(chat_id,
                    f"👋 <b>Добро пожаловать, {username}!</b>\n\n"
                    f"💼 <b>Бизнес-бот Ракета 3.0</b>\n\n"
                    f"🌐 <b>НОВЫЙ WEB APP!</b>\n"
                    f"Откройте через команду /webapp\n\n"
                    f"💎 <b>Присоединяйтесь к нашей группе:</b>\n"
                    f"👉 {GROUP_INVITE_LINK}\n\n"
                    f"🎮 <b>В группе вас ждут:</b>\n"
                    f"• Заработок денег\n"
                    f"• Игра в казино\n"
                    f"• Ограбление казны\n"
                    f"• Бизнес-система\n"
                    f"• Вывод средств\n"
                    f"• Крестики-нолики\n\n"
                    f"⚡ <b>Начните зарабатывать прямо сейчас!</b>")

def handle_balance_short(chat_id, user_id, username):
    """Показывает баланс пользователя (команда 'Б')"""
    print(f"💰 Запрос баланса (Б) от @{username}")

    # Создаем пользователя если не существует
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {
            'username': username,
            'balance': 0,
            'business_level': 0,
            'last_income': 0,
            'robbery_count': 0,
            'last_robbery_date': datetime.now().strftime("%Y-%m-%d"),
            'last_robbery_time': 0,
            'last_daily_bonus': None,
            'last_casino_time': 0,
            'daily_robbery_earnings': 0
        }
        save_data()

    user_data = users_data[str(user_id)]
    balance = user_data.get('balance', 0)
    business_level = user_data.get('business_level', 0)

    business_info = ""
    if business_level > 0:
        business_info = f"\n🏢 <b>Бизнес:</b> Ур.{business_level}"

    send_message(chat_id,
                f"💼 <b>БАЛАНС</b>\n\n"
                f"👤 <b>Игрок:</b> @{username}\n"
                f"💰 <b>Баланс:</b> {balance}₽"
                f"{business_info}\n\n"
                f"🌐 <b>Web App:</b> /webapp")

def handle_daily_bonus(chat_id, user_id, username):
    """Выдача ежедневного бонуса"""
    print(f"🎁 Обработка бонуса для @{username}")

    # Создаем пользователя если не существует
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {
            'username': username,
            'balance': 0,
            'business_level': 0,
            'last_income': 0,
            'robbery_count': 0,
            'last_robbery_date': datetime.now().strftime("%Y-%m-%d"),
            'last_robbery_time': 0,
            'last_daily_bonus': None,
            'last_casino_time': 0,
            'daily_robbery_earnings': 0
        }

    user_data = users_data[str(user_id)]
    today = datetime.now().strftime("%Y-%m-%d")

    if user_data.get('last_daily_bonus') == today:
        send_message(chat_id,
                    f"🎁 <b>Бонус уже получен!</b>\n\n"
                    f"💡 <b>Следующий бонус будет доступен завтра</b>")
        return

    bonus_amount = 5
    user_data['balance'] = user_data.get('balance', 0) + bonus_amount
    user_data['last_daily_bonus'] = today
    save_data()

    send_message(chat_id,
                f"🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n\n"
                f"👤 <b>Пользователь:</b> @{username}\n"
                f"💰 <b>Получено:</b> {bonus_amount}₽\n"
                f"💎 <b>Ваш баланс:</b> {user_data['balance']}₽\n\n"
                f"💡 <b>Возвращайтесь за новым бонусом завтра!</b>")

    print(f"✅ Бонус выдан @{username}")
    update_stats_message()

def handle_rob_treasury(chat_id, user_id, username):
    """Обработка ограбления казны"""
    global treasury, last_treasury_update

    print(f"🏦 Обработка ограбления от @{username}")

    # Создаем пользователя если не существует
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {
            'username': username,
            'balance': 0,
            'business_level': 0,
            'last_income': 0,
            'robbery_count': 0,
            'last_robbery_date': datetime.now().strftime("%Y-%m-%d"),
            'last_robbery_time': 0,
            'last_daily_bonus': None,
            'last_casino_time': 0,
            'daily_robbery_earnings': 0
        }
        save_data()

    user_data = users_data[str(user_id)]
    current_time = time.time()

    # Проверяем кулдаун (30 минут)
    if current_time - user_data.get('last_robbery_time', 0) < 1800:
        remaining_time = 1800 - (current_time - user_data['last_robbery_time'])
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)

        send_message(chat_id,
                    f"⏰ <b>Ограбление пока невозможно!</b>\n\n"
                    f"🕒 <b>До следующей попытки:</b> {minutes} мин {seconds} сек\n"
                    f"💡 <b>Попробуйте позже</b>")
        return

    # Проверяем дневной лимит (3 ограбления в день)
    today = datetime.now().strftime("%Y-%m-%d")
    if user_data.get('last_robbery_date') != today:
        user_data['robbery_count'] = 0
        user_data['daily_robbery_earnings'] = 0
        user_data['last_robbery_date'] = today

    if user_data.get('robbery_count', 0) >= 3:
        send_message(chat_id,
                    f"🚫 <b>Достигнут дневной лимит ограблений!</b>\n\n"
                    f"📊 <b>Лимит:</b> 3 ограбления в день\n"
                    f"💡 <b>Попробуйте завтра</b>")
        return

    # Обновляем казну (каждые 2 часа)
    if current_time - last_treasury_update > 7200:
        treasury = random.randint(25, 100)
        last_treasury_update = current_time
        save_data()

    # Шанс успеха 90%
    success = random.random() <= 0.9

    if success:
        stolen_amount = random.randint(1, min(20, treasury))
        treasury -= stolen_amount
        if treasury < 0:
            treasury = 0

        user_data['balance'] = user_data.get('balance', 0) + stolen_amount
        user_data['robbery_count'] = user_data.get('robbery_count', 0) + 1
        user_data['daily_robbery_earnings'] = user_data.get('daily_robbery_earnings', 0) + stolen_amount
        user_data['last_robbery_time'] = current_time

        save_data()

        send_message(chat_id,
                    f"🎯 <b>Ограбление успешно!</b>\n\n"
                    f"👤 <b>Грабитель:</b> @{username}\n"
                    f"💰 <b>Украдено:</b> {stolen_amount}₽\n"
                    f"🏦 <b>Остаток в казне:</b> {treasury}₽\n"
                    f"📊 <b>Ограблений сегодня:</b> {user_data['robbery_count']}/3\n"
                    f"💎 <b>Ваш баланс:</b> {user_data['balance']}₽")
        print(f"✅ Ограбление успешно: +{stolen_amount}₽")
    else:
        user_data['robbery_count'] = user_data.get('robbery_count', 0) + 1
        user_data['last_robbery_time'] = current_time
        save_data()

        send_message(chat_id,
                    f"🚨 <b>Ограбление провалилось!</b>\n\n"
                    f"👤 <b>Грабитель:</b> @{username}\n"
                    f"💂 <b>Охрана поймала вас!</b>\n"
                    f"🏦 <b>Казна осталась нетронутой:</b> {treasury}₽\n"
                    f"📊 <b>Ограблений сегодня:</b> {user_data['robbery_count']}/3\n\n"
                    f"💡 <b>Попробуйте снова через 30 минут</b>")
        print(f"❌ Ограбление провалилось")

    update_stats_message()

def handle_casino(chat_id, user_id, username, amount_text):
    """Игра в казино с 30% шансом выигрыша x2"""
    print(f"🎰 Обработка казино от @{username}: {amount_text}")

    # Создаем пользователя если не существует
    if str(user_id) not in users_data:
        users_data[str(user_id)] = {
            'username': username,
            'balance': 0,
            'business_level': 0,
            'last_income': 0,
            'robbery_count': 0,
            'last_robbery_date': datetime.now().strftime("%Y-%m-%d"),
            'last_robbery_time': 0,
            'last_daily_bonus': None,
            'last_casino_time': 0,
            'daily_robbery_earnings': 0
        }
        save_data()

    user_data = users_data[str(user_id)]

    # Проверяем кулдаун (10 секунд)
    current_time = time.time()
    last_casino_time = user_data.get('last_casino_time', 0)
    if current_time - last_casino_time < 10:
        remaining_time = 10 - (current_time - last_casino_time)
        send_message(chat_id,
                    f"⏰ <b>Казино пока недоступно!</b>\n\n"
                    f"🕒 <b>До следующей попытки:</b> {int(remaining_time)} сек\n"
                    f"💡 <b>Подождите немного</b>")
        return

    # Парсим сумму
    try:
        amount = int(amount_text)
        if amount <= 0:
            send_message(chat_id, "❌ <b>Сумма должна быть положительной!</b>")
            return
    except ValueError:
        send_message(chat_id, "❌ <b>Неверная сумма! Используйте: казино [число]</b>")
        return

    balance = user_data.get('balance', 0)

    if balance < amount:
        send_message(chat_id,
                    f"❌ <b>Недостаточно средств!</b>\n\n"
                    f"💰 <b>Нужно:</b> {amount}₽\n"
                    f"💎 <b>Ваш баланс:</b> {balance}₽")
        return

    # Обновляем время последней игры
    user_data['last_casino_time'] = current_time

    # Шанс выигрыша 30%
    win_chance = 30  # 30%
    win = random.randint(1, 100) <= win_chance

    if win:
        # Выигрыш - удваиваем ставку
        win_amount = amount * 2
        user_data['balance'] = balance + win_amount
        save_data()

        send_message(chat_id,
                    f"🎰 <b>ДЖЕКПОТ! ВЫ ВЫИГРАЛИ!</b>\n\n"
                    f"👤 <b>Игрок:</b> @{username}\n"
                    f"💰 <b>Ставка:</b> {amount}₽\n"
                    f"🎯 <b>Выигрыш:</b> {win_amount}₽ (x2)\n"
                    f"📊 <b>Шанс:</b> {win_chance}%\n"
                    f"💎 <b>Ваш баланс:</b> {user_data['balance']}₽\n\n"
                    f"🍀 <b>Повезло! Поздравляем с выигрышем!</b>")
        print(f"✅ @{username} выиграл в казино: {amount}₽ → {win_amount}₽")
    else:
        # Проигрыш - теряем ставку
        user_data['balance'] = balance - amount
        save_data()

        send_message(chat_id,
                    f"🎰 <b>ВЫ ПРОИГРАЛИ!</b>\n\n"
                    f"👤 <b>Игрок:</b> @{username}\n"
                    f"💰 <b>Ставка:</b> {amount}₽\n"
                    f"💸 <b>Потеряно:</b> {amount}₽\n"
                    f"📊 <b>Шанс был:</b> {win_chance}%\n"
                    f"💎 <b>Ваш баланс:</b> {user_data['balance']}₽\n\n"
                    f"💡 <b>Попробуйте еще раз! Удачи!</b>")
        print(f"❌ @{username} проиграл в казино: {amount}₽")

    # Обновляем статистику после игры в казино
    update_stats_message()

# === ОСНОВНОЙ ЦИКЛ ===
def main():
    global last_update_id

    # Загрузка данных
    load_data()

    # Автоматически включаем основную группу если ее нет
    if MAIN_GROUP_ID not in groups_data:
        enable_group(MAIN_GROUP_ID, "Основная группа")

    # Запуск Web App сервера
    web_app_server = WebAppServer()
    web_app_server.start(WEB_APP_PORT)

    # Отправка сообщения о запуске
    send_bot_started_message()

    # Обновление статистики
    update_stats_message()

    print("⚡ Бот готов к работе! Ожидание сообщений...")
    print("🌐 Web App доступен по адресу:", WEB_APP_URL)
    print("📡 API доступен по порту:", WEB_APP_PORT)

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            payload = {
                'offset': last_update_id + 1,
                'timeout': 30
            }

            response = requests.post(url, json=payload, timeout=35)

            if response.status_code == 200:
                data = response.json()

                if 'result' in data:
                    for update in data['result']:
                        last_update_id = update['update_id']

                        if 'message' in update and 'text' in update['message']:
                            message = update['message']
                            chat_id = message['chat']['id']
                            text = message['text'].strip()
                            user_id = message['from']['id']
                            username = message['from'].get('username', 'user')
                            text_lower = text.lower()

                            print(f"📨 Сообщение от @{username} в {chat_id}: {text}")

                            # Проверяем, разрешен ли чат
                            if str(chat_id) != str(ADMIN_CHAT_ID) and not is_group_allowed(chat_id):
                                send_group_invite_message(chat_id)
                                continue

                            # Основные команды
                            if is_command_for_me(text, '/start'):
                                handle_start(chat_id, user_id, username)
                                continue

                            elif is_command_for_me(text, '/balance'):
                                handle_balance_short(chat_id, user_id, username)
                                continue

                            elif is_command_for_me(text, '/bonus'):
                                handle_daily_bonus(chat_id, user_id, username)
                                continue

                            elif is_command_for_me(text, '/webapp'):
                                handle_webapp_command(chat_id, user_id, username)
                                continue

                            # Команды без упоминания бота
                            elif text_lower == 'б' or text_lower == 'баланс':
                                handle_balance_short(chat_id, user_id, username)
                                continue

                            elif text_lower in ['ограбить казну', 'ограбить', 'грабить казну', 'ограбление']:
                                handle_rob_treasury(chat_id, user_id, username)
                                continue

                            elif text_lower.startswith('казино '):
                                try:
                                    amount_text = text_lower.split()[1]
                                    handle_casino(chat_id, user_id, username, amount_text)
                                except IndexError:
                                    send_message(chat_id, "❌ <b>Укажите сумму! Используйте: казино [сумма]</b>")
                                continue

                            elif text_lower == 'казино':
                                send_message(chat_id,
                                    f"🎰 <b>КАЗИНО 30%</b>\n\n"
                                    f"📊 <b>Правила игры:</b>\n"
                                    f"• Шанс выигрыша: 30%\n"
                                    f"• При выигрыше: x2 от ставки\n"
                                    f"• При проигрыше: теряете ставку\n"
                                    f"• Кулдаун: 10 секунд\n\n"
                                    f"🎯 <b>Как играть:</b>\n"
                                    f"<code>казино [сумма]</code>\n\n"
                                    f"💡 <b>Пример:</b> <code>казино 100</code>\n\n"
                                    f"🌐 <b>Web App:</b> /webapp")
                                continue

            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен пользователем")
            save_data()
            web_app_server.stop()
            break
        except Exception as e:
            print(f"❌ Критическая ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
