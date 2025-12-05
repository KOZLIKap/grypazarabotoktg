import requests
import time
import json
import random
from datetime import datetime, timedelta

# Настройки
TOKEN = "8466725404:AAFsxikWr8541rgTZcpxZdBXqdO-1qra4Mo"
ADMIN_CHAT_ID = "6319679398"
WITHDRAW_BOT_USERNAME = "OksajdShop_Raketa_bot"
BOT_USERNAME = "Raketa_oxide_bot"
STATS_CHANNEL_ID = "-1003002379769"
STATS_MESSAGE_ID = 832
MAIN_GROUP_ID = "-1003117157578"
GROUP_INVITE_LINK = "https://t.me/+bjAMAhtua9xmNzgy"

# Права доступа
ADMIN_IDS = ["6319679398", "6999365345"]

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
    global users_data, treasury, last_treasury_update, withdraw_codes, withdraw_requests, groups_data, active_games
    try:
        data = {
            'users_data': users_data,
            'treasury': treasury,
            'last_treasury_update': last_treasury_update,
            'withdraw_codes': withdraw_codes,
            'withdraw_requests': withdraw_requests,
            'groups_data': groups_data
            # active_games не сохраняем, так как это временные данные
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
        'admin_actions_enabled': False,  # По умолчанию админ-действия выключены
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

def set_admin_actions(chat_id, enabled):
    """Включает/выключает админ-действия для группы"""
    if str(chat_id) in groups_data:
        groups_data[str(chat_id)]['admin_actions_enabled'] = enabled
        save_data()
        status = "включены" if enabled else "выключены"
        print(f"⚙️ Админ-действия {status} для группы {chat_id}")

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

def restrict_chat_member(chat_id, user_id, until_date=None):
    """Ограничение пользователя (мут)"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/restrictChatMember"
        payload = {
            'chat_id': chat_id,
            'user_id': user_id,
            'permissions': {
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_polls': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False,
                'can_change_info': False,
                'can_invite_users': False,
                'can_pin_messages': False
            }
        }
        if until_date:
            payload['until_date'] = until_date

        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка ограничения пользователя: {e}")
        return False

def promote_chat_member(chat_id, user_id):
    """Снятие ограничений с пользователя (размут)"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/restrictChatMember"
        payload = {
            'chat_id': chat_id,
            'user_id': user_id,
            'permissions': {
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True,
                'can_change_info': False,
                'can_invite_users': False,
                'can_pin_messages': False
            }
        }

        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка снятия ограничений: {e}")
        return False

def kick_chat_member(chat_id, user_id):
    """Кик пользователя с удалением из черного списка"""
    try:
        # Сначала баним (кикаем)
        url_ban = f"https://api.telegram.org/bot{TOKEN}/banChatMember"
        payload_ban = {
            'chat_id': chat_id,
            'user_id': user_id
        }

        response_ban = requests.post(url_ban, json=payload_ban, timeout=10)

        if response_ban.status_code == 200:
            # Затем сразу разбаниваем (удаляем из черного списка)
            url_unban = f"https://api.telegram.org/bot{TOKEN}/unbanChatMember"
            payload_unban = {
                'chat_id': chat_id,
                'user_id': user_id,
                'only_if_banned': True
            }

            response_unban = requests.post(url_unban, json=payload_unban, timeout=10)
            return response_unban.status_code == 200
        else:
            return False

    except Exception as e:
        print(f"❌ Ошибка кика пользователя: {e}")
        return False

def unban_chat_member(chat_id, user_id):
    """Разбан пользователя"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/unbanChatMember"
        payload = {
            'chat_id': chat_id,
            'user_id': user_id,
            'only_if_banned': True
        }

        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка разбана пользователя: {e}")
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
║ 📍 Основная группа: {MAIN_GROUP_ID}
║ 👑 Админы: {ADMIN_IDS}
║ 🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}
║ 👥 Пользователей: {len(users_data)}
║ 💰 Казна: {treasury}₽
║ 👥 Групп: {len(groups_data)}
╚══════════════════════════════╝
⚡ Бот готов к работе!

💡 <b>Команды управления группами:</b>
• включить [ID_группы] - включить бота для группы
• выключить [ID_группы] - выключить бота для группы
• админ_действия [ID_группы] [вкл/выкл] - управление админ-командами
• список_групп - показать все группы
• статус [ID_группы] - информация о группе
    """
    print(console_message)

    # Сообщение в основную группу
    group_message = (
        f"🤖 <b>БОТ РАКЕТА 3.0 ЗАПУЩЕН!</b>\n\n"
        f"✅ <b>Система активирована и готова к работе!</b>\n\n"
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
        f"• играть [ставка] - крестики-нолики\n\n"
        f"⚡ <b>Удачи в заработке!</b>"
    )

    # Отправляем сообщение в основную группу
    success = send_message(MAIN_GROUP_ID, group_message)
    if success:
        print("✅ Сообщение о запуске отправлено в основную группу")
    else:
        print("❌ Не удалось отправить сообщение в группу")

# === КОМАНДЫ УПРАВЛЕНИЯ ГРУППАМИ ЧЕРЕЗ ЛС ===
def handle_group_management(chat_id, user_id, username, text):
    """Обработка команд управления группами через ЛС"""
    if not has_admin_rights(user_id):
        send_message(chat_id, "❌ <b>У вас нет прав для управления группами!</b>")
        return

    text_lower = text.lower()

    if text_lower.startswith('включить '):
        group_id = text.split(' ')[1]
        enable_group(group_id)
        send_message(chat_id, f"✅ <b>Группа {group_id} включена!</b>")

    elif text_lower.startswith('выключить '):
        group_id = text.split(' ')[1]
        disable_group(group_id)
        send_message(chat_id, f"❌ <b>Группа {group_id} выключена!</b>")

    elif text_lower.startswith('админ_действия '):
        parts = text.split(' ')
        if len(parts) == 3:
            group_id = parts[1]
            action = parts[2].lower()
            if action in ['вкл', 'включить']:
                set_admin_actions(group_id, True)
                send_message(chat_id, f"✅ <b>Админ-действия включены для группы {group_id}</b>")
            elif action in ['выкл', 'выключить']:
                set_admin_actions(group_id, False)
                send_message(chat_id, f"❌ <b>Админ-действия выключены для группы {group_id}</b>")
            else:
                send_message(chat_id, "❌ <b>Неверный формат. Используйте: админ_действия [ID_группы] [вкл/выкл]</b>")
        else:
            send_message(chat_id, "❌ <b>Неверный формат. Используйте: админ_действия [ID_группы] [вкл/выкл]</b>")

    elif text_lower == 'список_групп':
        send_groups_list(chat_id)

    elif text_lower.startswith('статус '):
        group_id = text.split(' ')[1]
        send_group_status(chat_id, group_id)

    elif text_lower in ['группы', 'управление группами']:
        send_group_management_help(chat_id)

    else:
        send_message(chat_id, "❌ <b>Неизвестная команда. Используйте 'группы' для справки</b>")

def send_groups_list(chat_id):
    """Отправляет список групп"""
    if not groups_data:
        send_message(chat_id, "📭 <b>Нет зарегистрированных групп</b>")
        return

    message = "📋 <b>СПИСОК ГРУПП:</b>\n\n"

    for group_id, group_data in groups_data.items():
        status = "✅ ВКЛ" if group_data.get('enabled') else "❌ ВЫКЛ"
        admin_actions = "🛠️ ВКЛ" if group_data.get('admin_actions_enabled') else "🚫 ВЫКЛ"
        title = group_data.get('title', 'Неизвестно')
        added_date = group_data.get('added_date', 'Неизвестно')

        message += f"{status} | {admin_actions}\n"
        message += f"<b>Название:</b> {title}\n"
        message += f"<b>ID:</b> <code>{group_id}</code>\n"
        message += f"<b>Добавлена:</b> {added_date}\n\n"

    send_message(chat_id, message)

def send_group_status(chat_id, group_id):
    """Отправляет информацию о группе"""
    group_data = groups_data.get(str(group_id))
    if not group_data:
        send_message(chat_id, f"❌ <b>Группа {group_id} не найдена</b>")
        return

    status = "✅ Включена" if group_data.get('enabled') else "❌ Выключена"
    admin_actions = "✅ Включены" if group_data.get('admin_actions_enabled') else "❌ Выключены"
    title = group_data.get('title', 'Неизвестно')
    added_date = group_data.get('added_date', 'Неизвестно')
    added_by = group_data.get('added_by', 'Неизвестно')

    message = (
        f"📊 <b>ИНФОРМАЦИЯ О ГРУППЕ</b>\n\n"
        f"📝 <b>Название:</b> {title}\n"
        f"🆔 <b>ID:</b> <code>{group_id}</code>\n"
        f"🔧 <b>Статус:</b> {status}\n"
        f"🛠️ <b>Админ-действия:</b> {admin_actions}\n"
        f"👤 <b>Добавлена:</b> {added_by}\n"
        f"📅 <b>Дата:</b> {added_date}"
    )

    send_message(chat_id, message)

def send_group_management_help(chat_id):
    """Отправляет справку по управлению группами"""
    help_text = (
        f"🎮 <b>КОМАНДЫ УПРАВЛЕНИЯ ГРУППАМИ</b>\n\n"
        f"• <code>включить [ID_группы]</code> - включить бота для группы\n"
        f"• <code>выключить [ID_группы]</code> - выключить бота для группы\n"
        f"• <code>админ_действия [ID_группы] [вкл/выкл]</code> - управление админ-командами\n"
        f"• <code>список_групп</code> - показать все группы\n"
        f"• <code>статус [ID_группы]</code> - информация о группе\n\n"
        f"💡 <b>Примеры:</b>\n"
        f"• <code>включить -100123456789</code>\n"
        f"• <code>выключить -100123456789</code>\n"
        f"• <code>админ_действия -100123456789 вкл</code>\n"
        f"• <code>статус -100123456789</code>\n\n"
        f"📝 <b>Как получить ID группы:</b>\n"
        f"1. Добавьте бота в группу\n"
        f"2. Отправьте любое сообщение\n"
        f"3. ID группы будет в логах бота"
    )

    send_message(chat_id, help_text)

def send_group_not_enabled_message(chat_id, group_id):
    """Отправляет сообщение о том, что группа не включена"""
    message = (
        f"🚫 <b>Бот не активирован в этой группе!</b>\n\n"
        f"💡 <b>Для активации бота обратитесь к администратору:</b>\n"
        f"👤 @apathy_DSR\n\n"
        f"🆔 <b>ID группы для включения:</b>\n"
        f"<code>{group_id}</code>\n\n"
        f"⚡ <b>После активации в группе станут доступны:</b>\n"
        f"• Заработок денег\n"
        f"• Игра в казино\n"
        f"• Ограбление казны\n"
        f"• Бизнес-система\n"
        f"• Вывод средств\n"
        f"• Крестики-нолики"
    )
    send_message(chat_id, message)

# === КОМАНДЫ УПРАВЛЕНИЯ ГРУППАМИ ЧЕРЕЗ КОНСОЛЬ ===
def handle_console_command():
    """Обработка команд из консоли"""
    while True:
        try:
            command = input("\n🎮 Введите команду: ").strip().lower()

            if command.startswith('включить '):
                group_id = command.split(' ')[1]
                enable_group(group_id)
                print(f"✅ Группа {group_id} включена")

            elif command.startswith('выключить '):
                group_id = command.split(' ')[1]
                disable_group(group_id)
                print(f"❌ Группа {group_id} выключена")

            elif command.startswith('админ_действия '):
                parts = command.split(' ')
                if len(parts) == 3:
                    group_id = parts[1]
                    action = parts[2]
                    if action in ['вкл', 'включить']:
                        set_admin_actions(group_id, True)
                        print(f"✅ Админ-действия включены для группы {group_id}")
                    elif action in ['выкл', 'выключить']:
                        set_admin_actions(group_id, False)
                        print(f"❌ Админ-действия выключены для группы {group_id}")
                    else:
                        print("❌ Неверный формат. Используйте: админ_действия [ID_группы] [вкл/выкл]")
                else:
                    print("❌ Неверный формат. Используйте: админ_действия [ID_группы] [вкл/выкл]")

            elif command == 'список_групп':
                print_groups_list()

            elif command.startswith('статус '):
                group_id = command.split(' ')[1]
                print_group_status(group_id)

            elif command in ['помощь', 'help', '?']:
                print_help()

            elif command in ['выход', 'exit', 'quit']:
                print("👋 Завершение работы...")
                break

            else:
                print("❌ Неизвестная команда. Введите 'помощь' для списка команд")

        except KeyboardInterrupt:
            print("\n👋 Завершение работы...")
            break
        except Exception as e:
            print(f"❌ Ошибка выполнения команды: {e}")

def print_groups_list():
    """Выводит список всех групп"""
    if not groups_data:
        print("📭 Нет зарегистрированных групп")
        return

    print("\n📋 Список групп:")
    print("-" * 80)
    for group_id, group_data in groups_data.items():
        status = "✅ ВКЛ" if group_data.get('enabled') else "❌ ВЫКЛ"
        admin_actions = "🛠️ ВКЛ" if group_data.get('admin_actions_enabled') else "🚫 ВЫКЛ"
        title = group_data.get('title', 'Неизвестно')
        added_date = group_data.get('added_date', 'Неизвестно')

        print(f"{status} | {admin_actions} | {title}")
        print(f"    ID: {group_id}")
        print(f"    Добавлена: {added_date}")
        print("-" * 80)

def print_group_status(group_id):
    """Выводит информацию о группе"""
    group_data = groups_data.get(str(group_id))
    if not group_data:
        print(f"❌ Группа {group_id} не найдена")
        return

    status = "✅ Включена" if group_data.get('enabled') else "❌ Выключена"
    admin_actions = "✅ Включены" if group_data.get('admin_actions_enabled') else "❌ Выключены"
    title = group_data.get('title', 'Неизвестно')
    added_date = group_data.get('added_date', 'Неизвестно')
    added_by = group_data.get('added_by', 'Неизвестно')

    print(f"\n📊 Информация о группе:")
    print(f"📝 Название: {title}")
    print(f"🆔 ID: {group_id}")
    print(f"🔧 Статус: {status}")
    print(f"🛠️ Админ-действия: {admin_actions}")
    print(f"👤 Добавлена: {added_by}")
    print(f"📅 Дата: {added_date}")

def print_help():
    """Выводит справку по командам"""
    help_text = """
🎮 Команды управления группами:

• включить [ID_группы] - включить бота для группы
  Пример: включить -100123456789

• выключить [ID_группы] - выключить бота для группы
  Пример: выключить -100123456789

• админ_действия [ID_группы] [вкл/выкл] - управление админ-командами
  Пример: админ_действия -100123456789 вкл

• список_групп - показать все группы

• статус [ID_группы] - информация о группе
  Пример: статус -100123456789

• помощь - показать эту справку

• выход - завершить работу

💡 Как получить ID группы:
1. Добавьте бота в группу
2. Отправьте любое сообщение
3. ID группы будет в логах бота
    """
    print(help_text)

# === ИГРА В КРЕСТИКИ-НОЛИКИ ===
def create_tic_tac_toe_board(game_id):
    """Создает клавиатуру для игры в крестики-нолики"""
    game = active_games.get(game_id)
    if not game:
        return None

    board = game['board']
    keyboard = []

    for i in range(3):
        row = []
        for j in range(3):
            cell_index = i * 3 + j
            if board[cell_index] == ' ':
                row.append({"text": "ㅤ", "callback_data": f"tictac_{game_id}_{cell_index}"})
            elif board[cell_index] == 'X':
                row.append({"text": "❌", "callback_data": f"tictac_view_{game_id}"})
            elif board[cell_index] == 'O':
                row.append({"text": "⭕", "callback_data": f"tictac_view_{game_id}"})
        keyboard.append(row)

    return {"inline_keyboard": keyboard}

def check_tic_tac_toe_winner(board):
    """Проверяет победителя в крестики-нолики"""
    # Проверка строк
    for i in range(0, 9, 3):
        if board[i] == board[i+1] == board[i+2] != ' ':
            return board[i]

    # Проверка столбцов
    for i in range(3):
        if board[i] == board[i+3] == board[i+6] != ' ':
            return board[i]

    # Проверка диагоналей
    if board[0] == board[4] == board[8] != ' ':
        return board[0]
    if board[2] == board[4] == board[6] != ' ':
        return board[2]

    # Проверка на ничью
    if ' ' not in board:
        return 'Draw'

    return None

def handle_tic_tac_toe_invite(chat_id, user_id, target_user_id, username, target_username, bet_amount):
    """Обработка приглашения в игру крестики-нолики"""
    print(f"🎮 Приглашение в игру от @{username} для @{target_username}, ставка: {bet_amount}₽")

    # Проверяем баланс обоих игроков
    if str(user_id) not in users_data:
        send_message(chat_id, f"❌ <b>@{username}, вы не зарегистрированы в системе!</b>")
        return

    if str(target_user_id) not in users_data:
        send_message(chat_id, f"❌ <b>@{target_username} не зарегистрирован в системе!</b>")
        return

    user_balance = users_data[str(user_id)].get('balance', 0)
    target_balance = users_data[str(target_user_id)].get('balance', 0)

    if user_balance < bet_amount:
        send_message(chat_id,
                    f"❌ <b>Недостаточно средств для создания игры!</b>\n\n"
                    f"💰 <b>Нужно:</b> {bet_amount}₽\n"
                    f"💎 <b>Ваш баланс:</b> {user_balance}₽")
        return

    if target_balance < bet_amount:
        send_message(chat_id,
                    f"❌ <b>У @{target_username} недостаточно средств!</b>\n\n"
                    f"💰 <b>Нужно:</b> {bet_amount}₽\n"
                    f"💎 <b>Баланс @{target_username}:</b> {target_balance}₽")
        return

    # Создаем игру
    game_id = f"{chat_id}_{int(time.time())}"
    active_games[game_id] = {
        'chat_id': chat_id,
        'player_x': user_id,  # Игрок X (тот, кто создал игру)
        'player_o': target_user_id,  # Игрок O (тот, кому предложили)
        'player_x_username': username,
        'player_o_username': target_username,
        'current_player': user_id,  # Первым ходит создатель игры
        'board': [' '] * 9,  # Пустая доска 3x3
        'bet_amount': bet_amount,
        'status': 'waiting',  # waiting, active, finished
        'created_time': time.time()
    }

    # Блокируем ставку у создателя игры
    users_data[str(user_id)]['balance'] -= bet_amount
    save_data()

    message_text = (
        f"🎮 <b>ПРИГЛАШЕНИЕ В ИГРУ КРЕСТИКИ-НОЛИКИ</b>\n\n"
        f"❌ <b>Игрок X:</b> @{username}\n"
        f"⭕ <b>Игрок O:</b> @{target_username}\n"
        f"💰 <b>Ставка:</b> {bet_amount}₽\n\n"
        f"💡 <b>@{target_username}, чтобы принять игру, нажмите кнопку ниже:</b>"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Принять игру", "callback_data": f"tictac_accept_{game_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"tictac_decline_{game_id}"}]
        ]
    }

    send_message(chat_id, message_text, keyboard)
    print(f"✅ Создана игра {game_id}")

def handle_tic_tac_toe_accept(callback_data, user_id, username):
    """Обработка принятия игры"""
    game_id = callback_data.split('_')[2]
    game = active_games.get(game_id)

    if not game:
        send_message(game['chat_id'], "❌ <b>Игра не найдена или уже завершена!</b>")
        return

    if game['player_o'] != user_id:
        send_message(game['chat_id'], "❌ <b>Эта игра не для вас!</b>")
        return

    if game['status'] != 'waiting':
        send_message(game['chat_id'], "❌ <b>Игра уже начата или завершена!</b>")
        return

    # Блокируем ставку у второго игрока
    users_data[str(user_id)]['balance'] -= game['bet_amount']
    save_data()

    # Начинаем игру
    game['status'] = 'active'
    board_keyboard = create_tic_tac_toe_board(game_id)

    message_text = (
        f"🎮 <b>НАЧАЛАСЬ ИГРА КРЕСТИКИ-НОЛИКИ!</b>\n\n"
        f"❌ <b>Игрок X:</b> @{game['player_x_username']}\n"
        f"⭕ <b>Игрок O:</b> @{game['player_o_username']}\n"
        f"💰 <b>Ставка:</b> {game['bet_amount']}₽\n\n"
        f"🎯 <b>Сейчас ходит:</b> @{game['player_x_username']} (❌)"
    )

    # Редактируем сообщение с приглашением
    edit_message(game['chat_id'], callback_data['message']['message_id'], message_text, board_keyboard)
    print(f"✅ Игра {game_id} начата")

def handle_tic_tac_toe_decline(callback_data, user_id, username):
    """Обработка отклонения игры"""
    game_id = callback_data.split('_')[2]
    game = active_games.get(game_id)

    if not game:
        return

    if game['player_o'] != user_id:
        send_message(game['chat_id'], "❌ <b>Эта игра не для вас!</b>")
        return

    # Возвращаем деньги создателю игры
    users_data[str(game['player_x'])]['balance'] += game['bet_amount']
    save_data()

    # Удаляем игру
    del active_games[game_id]

    message_text = (
        f"🎮 <b>ИГРА ОТКЛОНЕНА</b>\n\n"
        f"❌ <b>Игрок @{username} отклонил приглашение в игру!</b>\n\n"
        f"💰 <b>Ставка возвращена @{game['player_x_username']}</b>"
    )

    # Редактируем сообщение
    edit_message(game['chat_id'], callback_data['message']['message_id'], message_text)
    print(f"❌ Игра {game_id} отклонена")

def handle_tic_tac_toe_move(callback_data, user_id, username):
    """Обработка хода в игре"""
    parts = callback_data.split('_')
    game_id = parts[2]
    cell_index = int(parts[3])

    game = active_games.get(game_id)

    if not game:
        return

    if game['status'] != 'active':
        return

    if user_id != game['current_player']:
        send_message(game['chat_id'], f"❌ <b>@{username}, сейчас не ваш ход!</b>")
        return

    if game['board'][cell_index] != ' ':
        send_message(game['chat_id'], f"❌ <b>@{username}, эта клетка уже занята!</b>")
        return

    # Делаем ход
    symbol = 'X' if user_id == game['player_x'] else 'O'
    game['board'][cell_index] = symbol

    # Проверяем победителя
    winner = check_tic_tac_toe_winner(game['board'])

    if winner:
        # Игра завершена
        game['status'] = 'finished'
        handle_tic_tac_toe_finish(game, winner)
    else:
        # Передаем ход следующему игроке
        game['current_player'] = game['player_o'] if user_id == game['player_x'] else game['player_x']

        # Обновляем доску
        board_keyboard = create_tic_tac_toe_board(game_id)
        current_player_username = game['player_x_username'] if game['current_player'] == game['player_x'] else game['player_o_username']
        current_symbol = '❌' if game['current_player'] == game['player_x'] else '⭕'

        message_text = (
            f"🎮 <b>ИГРА КРЕСТИКИ-НОЛИКИ</b>\n\n"
            f"❌ <b>Игрок X:</b> @{game['player_x_username']}\n"
            f"⭕ <b>Игрок O:</b> @{game['player_o_username']}\n"
            f"💰 <b>Ставка:</b> {game['bet_amount']}₽\n\n"
            f"🎯 <b>Сейчас ходит:</b> @{current_player_username} ({current_symbol})"
        )

        # Редактируем сообщение с новой доской
        edit_message(game['chat_id'], callback_data['message']['message_id'], message_text, board_keyboard)

def handle_tic_tac_toe_finish(game, winner):
    """Завершение игры и распределение выигрыша"""
    total_pot = game['bet_amount'] * 2

    if winner == 'Draw':
        # Ничья - возвращаем деньги обоим игрокам
        users_data[str(game['player_x'])]['balance'] += game['bet_amount']
        users_data[str(game['player_o'])]['balance'] += game['bet_amount']

        message_text = (
            f"🎮 <b>ИГРА ЗАВЕРШЕНА - НИЧЬЯ!</b>\n\n"
            f"❌ <b>Игрок X:</b> @{game['player_x_username']}\n"
            f"⭕ <b>Игрок O:</b> @{game['player_o_username']}\n"
            f"💰 <b>Ставка:</b> {game['bet_amount']}₽\n\n"
            f"🤝 <b>Ничья! Деньги возвращены обоим игрокам.</b>"
        )
    else:
        # Есть победитель
        if winner == 'X':
            winner_id = game['player_x']
            winner_username = game['player_x_username']
            loser_id = game['player_o']
            loser_username = game['player_o_username']
        else:
            winner_id = game['player_o']
            winner_username = game['player_o_username']
            loser_id = game['player_x']
            loser_username = game['player_x_username']

        # Выдаем выигрыш победителю
        users_data[str(winner_id)]['balance'] += total_pot

        message_text = (
            f"🎮 <b>ИГРА ЗАВЕРШЕНА!</b>\n\n"
            f"❌ <b>Игрок X:</b> @{game['player_x_username']}\n"
            f"⭕ <b>Игрок O:</b> @{game['player_o_username']}\n"
            f"💰 <b>Ставка:</b> {game['bet_amount']}₽\n\n"
            f"🏆 <b>ПОБЕДИТЕЛЬ:</b> @{winner_username}\n"
            f"🎯 <b>Выигрыш:</b> {total_pot}₽"
        )

    save_data()

    # Показываем финальную доску
    board_keyboard = create_tic_tac_toe_board(game_id)

    # Редактируем сообщение с результатом
    edit_message(game['chat_id'], game.get('last_message_id'), message_text, board_keyboard)

    # Удаляем игру из активных
    del active_games[game_id]

    print(f"✅ Игра {game_id} завершена, победитель: {winner}")
    update_stats_message()

def handle_callback_query(update):
    """Обработка callback запросов от кнопок"""
    try:
        callback_query = update.get('callback_query', {})
        callback_data = callback_query.get('data', '')
        user_id = callback_query['from']['id']
        username = callback_query['from'].get('username', 'user')
        message = callback_query.get('message', {})

        print(f"🔄 Callback от @{username}: {callback_data}")

        # Сохраняем ID последнего сообщения игры
        if 'tictac_' in callback_data and 'message' in callback_query:
            game_id_parts = callback_data.split('_')
            if len(game_id_parts) >= 3:
                game_id = game_id_parts[2]
                if game_id in active_games:
                    active_games[game_id]['last_message_id'] = message['message_id']

        if callback_data.startswith('tictac_accept_'):
            handle_tic_tac_toe_accept(callback_data, user_id, username)

        elif callback_data.startswith('tictac_decline_'):
            handle_tic_tac_toe_decline(callback_data, user_id, username)

        elif callback_data.startswith('tictac_') and len(callback_data.split('_')) == 4:
            # Ход в игре (tictac_gameId_cellIndex)
            if not callback_data.startswith('tictac_view_'):
                handle_tic_tac_toe_move(callback_data, user_id, username)

        # Отправляем ответ на callback, чтобы убрать "часики" у кнопки
        url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
        payload = {
            'callback_query_id': callback_query['id']
        }
        requests.post(url, json=payload, timeout=5)

    except Exception as e:
        print(f"❌ Ошибка обработки callback: {e}")

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
                f"💎 <b>Для вывода:</b> 50₽")

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

def handle_casino_info(chat_id):
    """Информация о казино"""
    message = (
        f"🎰 <b>КАЗИНО РАКЕТА</b>\n\n"
        f"📊 <b>Правила игры:</b>\n"
        f"• Ставка: любая сумма от 1₽\n"
        f"• Шанс выигрыша: 30%\n"
        f"• При выигрыше: x2 от ставки\n"
        f"• При проигрыше: теряете ставку\n"
        f"• Кулдаун: 10 секунд\n\n"
        f"🎯 <b>Как играть:</b>\n"
        f"<code>казино [сумма]</code>\n\n"
        f"💡 <b>Примеры:</b>\n"
        f"• <code>казино 10</code> - ставка 10₽\n"
        f"• <code>казино 50</code> - ставка 50₽\n"
        f"• <code>казино 100</code> - ставка 100₽\n\n"
        f"💰 <b>Математика:</b>\n"
        f"• Ставка 10₽ → выигрыш 20₽ (30% шанс)\n"
        f"• Ставка 50₽ → выигрыш 100₽ (30% шанс)\n"
        f"• Ставка 100₽ → выигрыш 200₽ (30% шанс)\n\n"
        f"⚠️ <b>Внимание:</b>\n"
        f"• Играйте ответственно!\n"
        f"• Не ставьте больше чем можете позволить себе потерять"
    )

    send_message(chat_id, message)

# === КОМАНДА "ДАТЬ ПИЗДЫ" ===
def handle_give_pizdy(chat_id, user_id, target_user_id, username, target_username):
    """Команда 'дать пизды' для развлечения"""
    print(f"👊 @{username} дает пизды @{target_username}")

    # Случайный выбор результата
    results = [
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Легкий поджопник",
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Серьезные фингалы",
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Полный разгром",
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Отбитые почки",
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Выбитые зубы",
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Расшибан в лепешку",
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Отправлен в нокаут",
        f"🥊 <b>@{username} дал пизды @{target_username}!</b>\n💥 Результат: Получил по первое число",
    ]

    result = random.choice(results)
    send_message(chat_id, result)
    print(f"✅ @{username} дал пизды @{target_username}")

# === ПЛАТНЫЕ АДМИН КОМАНДЫ ===
def handle_admin_help(chat_id, user_id, username):
    """Показывает информацию о платных админ-командах"""
    user_balance = users_data.get(str(user_id), {}).get('balance', 0)

    # Проверяем, включены ли админ-действия в группе
    admin_actions_enabled = groups_data.get(str(chat_id), {}).get('admin_actions_enabled', False)

    status_text = "✅ Включены" if admin_actions_enabled else "❌ Выключены"

    message = (
        f"🛠️ <b>ПЛАТНЫЕ АДМИН-КОМАНДЫ</b>\n\n"
        f"📊 <b>Статус в этой группе:</b> {status_text}\n\n"
        f"💰 <b>Стоимость услуг:</b>\n"
        f"• 🔇 Мут на 30 минут - {ADMIN_PRICES['mute']}₽\n"
        f"• 🚫 Бан на 1 день - {ADMIN_PRICES['ban']}₽\n"
        f"• 👢 Кик - {ADMIN_PRICES['kick']}₽\n"
        f"• 🗑️ Удалить сообщение - {ADMIN_PRICES['delete']}₽\n"
        f"• 🔊 Размут - {ADMIN_PRICES['unmute']}₽\n"
        f"• ✅ Разбан - {ADMIN_PRICES['unban']}₽\n\n"
        f"💎 <b>Ваш баланс:</b> {user_balance}₽\n\n"
        f"🎯 <b>Как использовать:</b>\n"
        f"1. Ответьте на сообщение пользователя\n"
        f"2. Напишите команду:\n"
        f"   • <code>мут</code> - мут на 30 минут\n"
        f"   • <code>бан</code> - бан на 1 день\n"
        f"   • <code>кик</code> - кикнуть\n"
        f"   • <code>удалить</code> - удалить сообщение\n"
        f"   • <code>размут</code> - снять мут\n"
        f"   • <code>разбан</code> - снять бан\n\n"
        f"💡 <b>Пример:</b> Ответьте на сообщение и напишите <code>мут</code>"
    )

    send_message(chat_id, message)

def check_balance_and_deduct(user_id, price, action_name):
    """Проверяет баланс и списывает деньги"""
    if str(user_id) not in users_data:
        return False, "❌ <b>Вы не зарегистрированы в системе!</b>"

    user_data = users_data[str(user_id)]
    balance = user_data.get('balance', 0)

    if balance < price:
        return False, f"❌ <b>Недостаточно средств!</b>\n\n💰 <b>Нужно:</b> {price}₽\n💎 <b>Ваш баланс:</b> {balance}₽"

    # Списываем деньги
    user_data['balance'] = balance - price
    save_data()

    return True, f"✅ <b>Списано {price}₽ за {action_name}</b>"

def handle_paid_mute(chat_id, user_id, target_user_id, username, target_username):
    """Платный мут на 30 минут"""
    print(f"🔇 Платный мут от @{username} для @{target_username}")

    # Проверяем, включены ли админ-действия в группе
    if not groups_data.get(str(chat_id), {}).get('admin_actions_enabled', False):
        send_message(chat_id, "❌ <b>Админ-действия выключены в этой группе!</b>\n\nОбратитесь к администратору группы.")
        return False

    # Проверяем баланс и списываем деньги
    success, message = check_balance_and_deduct(user_id, ADMIN_PRICES['mute'], "мут на 30 минут")
    if not success:
        send_message(chat_id, message)
        return False

    # Выполняем мут
    duration_minutes = 30
    until_date = int(time.time()) + (duration_minutes * 60)
    success = restrict_chat_member(chat_id, target_user_id, until_date)

    if success:
        send_message(chat_id,
                    f"🔇 <b>ПОЛЬЗОВАТЕЛЬ ЗАМУЧЕН!</b>\n\n"
                    f"👤 <b>Покупатель:</b> @{username}\n"
                    f"🔇 <b>Замучен:</b> @{target_username}\n"
                    f"💰 <b>Стоимость:</b> {ADMIN_PRICES['mute']}₽\n"
                    f"⏰ <b>Длительность:</b> {duration_minutes} минут\n"
                    f"💎 <b>Остаток баланса:</b> {users_data[str(user_id)]['balance']}₽\n\n"
                    f"✅ <b>Мут успешно применен!</b>")
        print(f"✅ Платный мут: @{username} замутил @{target_username} за {ADMIN_PRICES['mute']}₽")
        update_stats_message()
        return True
    else:
        # Возвращаем деньги если не удалось
        users_data[str(user_id)]['balance'] += ADMIN_PRICES['mute']
        save_data()
        send_message(chat_id, "❌ <b>Не удалось замутить пользователя! Деньги возвращены.</b>")
        return False

def handle_paid_unmute(chat_id, user_id, target_user_id, username, target_username):
    """Платный размут"""
    print(f"🔊 Платный размут от @{username} для @{target_username}")

    # Проверяем, включены ли админ-действия в группе
    if not groups_data.get(str(chat_id), {}).get('admin_actions_enabled', False):
        send_message(chat_id, "❌ <b>Админ-действия выключены в этой группе!</b>\n\nОбратитесь к администратору группы.")
        return False

    # Проверяем баланс и списываем деньги
    success, message = check_balance_and_deduct(user_id, ADMIN_PRICES['unmute'], "размут")
    if not success:
        send_message(chat_id, message)
        return False

    # Выполняем размут (снимаем ограничения)
    success = promote_chat_member(chat_id, target_user_id)

    if success:
        send_message(chat_id,
                    f"🔊 <b>ПОЛЬЗОВАТЕЛЬ РАЗМУЧЕН!</b>\n\n"
                    f"👤 <b>Покупатель:</b> @{username}\n"
                    f"🔊 <b>Размучен:</b> @{target_username}\n"
                    f"💰 <b>Стоимость:</b> {ADMIN_PRICES['unmute']}₽\n"
                    f"💎 <b>Остаток баланса:</b> {users_data[str(user_id)]['balance']}₽\n\n"
                    f"✅ <b>Размут успешно выполнен!</b>")
        print(f"✅ Платный размут: @{username} размутил @{target_username} за {ADMIN_PRICES['unmute']}₽")
        update_stats_message()
        return True
    else:
        # Возвращаем деньги если не удалось
        users_data[str(user_id)]['balance'] += ADMIN_PRICES['unmute']
        save_data()
        send_message(chat_id, "❌ <b>Не удалось размутить пользователя! Деньги возвращены.</b>")
        return False

def handle_paid_ban(chat_id, user_id, target_user_id, username, target_username):
    """Платный бан на 1 день"""
    print(f"🚫 Платный бан от @{username} для @{target_username}")

    # Проверяем, включены ли админ-действия в группе
    if not groups_data.get(str(chat_id), {}).get('admin_actions_enabled', False):
        send_message(chat_id, "❌ <b>Админ-действия выключены в этой группе!</b>\n\nОбратитесь к администратору группы.")
        return False

    # Проверяем баланс и списываем деньги
    success, message = check_balance_and_deduct(user_id, ADMIN_PRICES['ban'], "бан на 1 день")
    if not success:
        send_message(chat_id, message)
        return False

    # Выполняем бан на 1 день
    duration_days = 1
    until_date = int(time.time()) + (duration_days * 24 * 60 * 60)
    success = restrict_chat_member(chat_id, target_user_id, until_date)

    if success:
        send_message(chat_id,
                    f"🚫 <b>ПОЛЬЗОВАТЕЛЬ ЗАБАНЕН!</b>\n\n"
                    f"👤 <b>Покупатель:</b> @{username}\n"
                    f"🚫 <b>Забанен:</b> @{target_username}\n"
                    f"💰 <b>Стоимость:</b> {ADMIN_PRICES['ban']}₽\n"
                    f"⏰ <b>Длительность:</b> {duration_days} день\n"
                    f"💎 <b>Остаток баланса:</b> {users_data[str(user_id)]['balance']}₽\n\n"
                    f"✅ <b>Бан успешно применен!</b>")
        print(f"✅ Платный бан: @{username} забанил @{target_username} за {ADMIN_PRICES['ban']}₽")
        update_stats_message()
        return True
    else:
        # Возвращаем деньги если не удалось
        users_data[str(user_id)]['balance'] += ADMIN_PRICES['ban']
        save_data()
        send_message(chat_id, "❌ <b>Не удалось забанить пользователя! Деньги возвращены.</b>")
        return False

def handle_paid_unban(chat_id, user_id, target_user_id, username, target_username):
    """Платный разбан"""
    print(f"✅ Платный разбан от @{username} для @{target_username}")

    # Проверяем, включены ли админ-действия в группе
    if not groups_data.get(str(chat_id), {}).get('admin_actions_enabled', False):
        send_message(chat_id, "❌ <b>Админ-действия выключены в этой группе!</b>\n\nОбратитесь к администратору группы.")
        return False

    # Проверяем баланс и списываем деньги
    success, message = check_balance_and_deduct(user_id, ADMIN_PRICES['unban'], "разбан")
    if not success:
        send_message(chat_id, message)
        return False

    # Выполняем разбан
    success = unban_chat_member(chat_id, target_user_id)

    if success:
        send_message(chat_id,
                    f"✅ <b>ПОЛЬЗОВАТЕЛЬ РАЗБАНЕН!</b>\n\n"
                    f"👤 <b>Покупатель:</b> @{username}\n"
                    f"✅ <b>Разбанен:</b> @{target_username}\n"
                    f"💰 <b>Стоимость:</b> {ADMIN_PRICES['unban']}₽\n"
                    f"💎 <b>Остаток баланса:</b> {users_data[str(user_id)]['balance']}₽\n\n"
                    f"✅ <b>Разбан успешно выполнен!</b>")
        print(f"✅ Платный разбан: @{username} разбанил @{target_username} за {ADMIN_PRICES['unban']}₽")
        update_stats_message()
        return True
    else:
        # Возвращаем деньги если не удалось
        users_data[str(user_id)]['balance'] += ADMIN_PRICES['unban']
        save_data()
        send_message(chat_id, "❌ <b>Не удалось разбанить пользователя! Деньги возвращены.</b>")
        return False

def handle_paid_kick(chat_id, user_id, target_user_id, username, target_username):
    """Платный кик с удалением из черного списка"""
    print(f"👢 Платный кик от @{username} для @{target_username}")

    # Проверяем, включены ли админ-действия в группе
    if not groups_data.get(str(chat_id), {}).get('admin_actions_enabled', False):
        send_message(chat_id, "❌ <b>Админ-действия выключены в этой группе!</b>\n\nОбратитесь к администратору группы.")
        return False

    # Проверяем баланс и списываем деньги
    success, message = check_balance_and_deduct(user_id, ADMIN_PRICES['kick'], "кик")
    if not success:
        send_message(chat_id, message)
        return False

    # Выполняем кик (с удалением из черного списка)
    success = kick_chat_member(chat_id, target_user_id)

    if success:
        send_message(chat_id,
                    f"👢 <b>ПОЛЬЗОВАТЕЛЬ КИКНУТ!</b>\n\n"
                    f"👤 <b>Покупатель:</b> @{username}\n"
                    f"👢 <b>Кикнут:</b> @{target_username}\n"
                    f"💰 <b>Стоимость:</b> {ADMIN_PRICES['kick']}₽\n"
                    f"💎 <b>Остаток баланса:</b> {users_data[str(user_id)]['balance']}₽\n"
                    f"♻️ <b>Статус:</b> Удален из черного списка\n\n"
                    f"✅ <b>Кик успешно выполнен!</b>")
        print(f"✅ Платный кик: @{username} кикнул @{target_username} за {ADMIN_PRICES['kick']}₽")
        update_stats_message()
        return True
    else:
        # Возвращаем деньги если не удалось
        users_data[str(user_id)]['balance'] += ADMIN_PRICES['kick']
        save_data()
        send_message(chat_id, "❌ <b>Не удалось кикнуть пользователя! Деньги возвращены.</b>")
        return False

def handle_paid_delete(chat_id, user_id, message_id, username):
    """Платное удаление сообщения"""
    print(f"🗑️ Платное удаление сообщения {message_id} от @{username}")

    # Проверяем, включены ли админ-действия в группе
    if not groups_data.get(str(chat_id), {}).get('admin_actions_enabled', False):
        send_message(chat_id, "❌ <b>Админ-действия выключены в этой группе!</b>\n\nОбратитесь к администратору группы.")
        return False

    # Проверяем баланс и списываем деньги
    success, message = check_balance_and_deduct(user_id, ADMIN_PRICES['delete'], "удаление сообщения")
    if not success:
        send_message(chat_id, message)
        return False

    # Выполняем удаление
    success = delete_message(chat_id, message_id)

    if success:
        send_message(chat_id,
                    f"🗑️ <b>СООБЩЕНИЕ УДАЛЕНО!</b>\n\n"
                    f"👤 <b>Покупатель:</b> @{username}\n"
                    f"💰 <b>Стоимость:</b> {ADMIN_PRICES['delete']}₽\n"
                    f"💎 <b>Остаток баланса:</b> {users_data[str(user_id)]['balance']}₽\n\n"
                    f"✅ <b>Сообщение успешно удалено!</b>")
        print(f"✅ Платное удаление: @{username} удалил сообщение за {ADMIN_PRICES['delete']}₽")
        update_stats_message()
        return True
    else:
        # Возвращаем деньги если не удалось
        users_data[str(user_id)]['balance'] += ADMIN_PRICES['delete']
        save_data()
        send_message(chat_id, "❌ <b>Не удалось удалить сообщение! Деньги возвращены.</b>")
        return False

# === КОМАНДЫ ПЕРЕДАЧИ ДЕНЕГ ===
def handle_give_money(chat_id, user_id, target_user_id, amount, username, target_username):
    """Выдача денег пользователю (админ)"""
    print(f"💰 Админ @{username} выдает {amount}₽ пользователю @{target_username}")

    if not has_admin_rights(user_id):
        send_message(chat_id, "❌ <b>У вас нет прав для этой команды!</b>")
        return

    if amount <= 0:
        send_message(chat_id, "❌ <b>Сумма должна быть положительной!</b>")
        return

    # Создаем пользователя если не существует
    if str(target_user_id) not in users_data:
        users_data[str(target_user_id)] = {
            'username': target_username,
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

    # Выдаем деньги
    old_balance = users_data[str(target_user_id)].get('balance', 0)
    users_data[str(target_user_id)]['balance'] = old_balance + amount
    save_data()

    new_balance = users_data[str(target_user_id)]['balance']

    send_message(chat_id,
                f"💰 <b>ДЕНЬГИ ВЫДАНЫ!</b>\n\n"
                f"👤 <b>Администратор:</b> @{username}\n"
                f"🎁 <b>Получатель:</b> @{target_username}\n"
                f"💸 <b>Сумма:</b> {amount}₽\n"
                f"📊 <b>Было:</b> {old_balance}₽\n"
                f"💎 <b>Стало:</b> {new_balance}₽\n\n"
                f"✅ <b>Операция успешно выполнена!</b>")

    print(f"✅ Деньги выданы успешно")
    update_stats_message()

def handle_give_money_user(chat_id, user_id, target_user_id, amount, username, target_username):
    """Передача денег между пользователями (команда ДАТЬ)"""
    print(f"💰 @{username} передает {amount}₽ пользователю @{target_username}")

    # Проверяем отправителя
    if str(user_id) not in users_data:
        send_message(chat_id, "❌ <b>Вы не зарегистрированы в системе!</b>")
        return

    # Создаем получателя если не существует
    if str(target_user_id) not in users_data:
        users_data[str(target_user_id)] = {
            'username': target_username,
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

    if amount <= 0:
        send_message(chat_id, "❌ <b>Сумма должна быть положительной!</b>")
        return

    user_data = users_data[str(user_id)]
    target_data = users_data[str(target_user_id)]

    # Нельзя переводить самому себе
    if user_id == target_user_id:
        send_message(chat_id, "❌ <b>Нельзя переводить деньги самому себе!</b>")
        return

    if user_data.get('balance', 0) < amount:
        send_message(chat_id,
                    f"❌ <b>Недостаточно средств!</b>\n\n"
                    f"💰 <b>Нужно:</b> {amount}₽\n"
                    f"💎 <b>Ваш баланс:</b> {user_data.get('balance', 0)}₽")
        return

    # Передача денег
    old_balance_sender = user_data.get('balance', 0)
    old_balance_receiver = target_data.get('balance', 0)

    user_data['balance'] = old_balance_sender - amount
    target_data['balance'] = old_balance_receiver + amount
    save_data()

    send_message(chat_id,
                f"💰 <b>ДЕНЬГИ ПЕРЕВЕДЕНЫ!</b>\n\n"
                f"👤 <b>От:</b> @{username}\n"
                f"👥 <b>Кому:</b> @{target_username}\n"
                f"💸 <b>Сумма:</b> {amount}₽\n\n"
                f"📊 <b>Было у отправителя:</b> {old_balance_sender}₽\n"
                f"💎 <b>Стало у отправителя:</b> {user_data['balance']}₽\n"
                f"📊 <b>Было у получателя:</b> {old_balance_receiver}₽\n"
                f"💎 <b>Стало у получателя:</b> {target_data['balance']}₽")

    print(f"✅ Перевод выполнен успешно: @{username} → @{target_username} {amount}₽")
    update_stats_message()

def handle_take_money(chat_id, user_id, target_user_id, amount, username, target_username):
    """Забрать деньги у пользователя (админ)"""
    print(f"💰 Админ @{username} забирает {amount}₽ у пользователя @{target_username}")

    if not has_admin_rights(user_id):
        send_message(chat_id, "❌ <b>У вас нет прав для этой команды!</b>")
        return

    if amount <= 0:
        send_message(chat_id, "❌ <b>Сумма должна быть положительной!</b>")
        return

    # Проверяем существование пользователя
    if str(target_user_id) not in users_data:
        send_message(chat_id, f"❌ <b>Пользователь @{target_username} не найден!</b>")
        return

    # Проверяем баланс
    old_balance = users_data[str(target_user_id)].get('balance', 0)
    if old_balance < amount:
        send_message(chat_id,
                    f"❌ <b>Недостаточно средств у пользователя!</b>\n\n"
                    f"💸 <b>Хотите забрать:</b> {amount}₽\n"
                    f"💰 <b>Баланс пользователя:</b> {old_balance}₽")
        return

    # Забираем деньги
    users_data[str(target_user_id)]['balance'] = old_balance - amount
    save_data()

    new_balance = users_data[str(target_user_id)]['balance']

    send_message(chat_id,
                f"💰 <b>ДЕНЬГИ ЗАБРАНЫ!</b>\n\n"
                f"👤 <b>Администратор:</b> @{username}\n"
                f"🎯 <b>Пользователь:</b> @{target_username}\n"
                f"💸 <b>Сумма:</b> {amount}₽\n"
                f"📊 <b>Было:</b> {old_balance}₽\n"
                f"💎 <b>Стало:</b> {new_balance}₽\n\n"
                f"✅ <b>Операция успешно выполнена!</b>")

    print(f"✅ Деньги забраны успешно")
    update_stats_message()

def handle_user_info_reply(chat_id, user_id, target_user_id, username, target_username):
    """Информация о пользователе (в ответ на сообщение)"""
    print(f"📊 Запрос информации о пользователе @{target_username} от @{username}")

    if not has_admin_rights(user_id):
        send_message(chat_id, "❌ <b>У вас нет прав для этой команды!</b>")
        return

    # Создаем пользователя если не существует
    if str(target_user_id) not in users_data:
        users_data[str(target_user_id)] = {
            'username': target_username,
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

    user_data = users_data[str(target_user_id)]

    # Форматируем даты
    last_daily_bonus = user_data.get('last_daily_bonus', 'Никогда')
    last_robbery_date = user_data.get('last_robbery_date', 'Никогда')

    # Время последнего ограбления
    last_robbery_time = user_data.get('last_robbery_time', 0)
    if last_robbery_time > 0:
        robbery_cooldown = time.time() - last_robbery_time
        if robbery_cooldown < 1800:
            remaining = 1800 - robbery_cooldown
            robbery_info = f"{int(remaining // 60)} мин {int(remaining % 60)} сек назад"
        else:
            robbery_info = "Доступно"
    else:
        robbery_info = "Доступно"

    message = (
        f"👤 <b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ</b>\n\n"
        f"🆔 <b>ID:</b> {target_user_id}\n"
        f"📛 <b>Username:</b> @{target_username}\n"
        f"💰 <b>Баланс:</b> {user_data.get('balance', 0)}₽\n"
        f"🏢 <b>Уровень бизнеса:</b> {user_data.get('business_level', 0)}\n"
        f"🎯 <b>Ограблений сегодня:</b> {user_data.get('robbery_count', 0)}/3\n"
        f"💸 <b>Заработано ограблениями сегодня:</b> {user_data.get('daily_robbery_earnings', 0)}₽\n"
        f"⏰ <b>Ограбление:</b> {robbery_info}\n"
        f"📅 <b>Последний бонус:</b> {last_daily_bonus}\n"
        f"🏦 <b>Последнее ограбление:</b> {last_robbery_date}\n\n"
        f"💡 <b>Команды управления:</b>\n"
        f"• <code>выдать 100</code> - выдать деньги (админ)\n"
        f"• <code>дать 100</code> - передать деньги\n"
        f"• <code>забрать 50</code> - забрать деньги (админ)"
    )

    send_message(chat_id, message)

# === ОСНОВНОЙ ЦИКЛ ===
def main():
    global last_update_id

    # Загрузка данных
    load_data()

    # Автоматически включаем основную группу если ее нет
    if MAIN_GROUP_ID not in groups_data:
        enable_group(MAIN_GROUP_ID, "Основная группа")
        set_admin_actions(MAIN_GROUP_ID, True)  # Включаем админ-действия для основной группы

    # Отправка сообщения о запуске
    send_bot_started_message()

    # Обновление статистики
    update_stats_message()

    print("⚡ Бот готов к работе! Ожидание сообщений...")

    # Запускаем обработчик команд консоли в отдельном потоке
    import threading
    console_thread = threading.Thread(target=handle_console_command, daemon=True)
    console_thread.start()

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

                        # Обработка callback запросов (кнопки)
                        if 'callback_query' in update:
                            handle_callback_query(update)
                            continue

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
                                send_group_not_enabled_message(chat_id, chat_id)
                                continue

                            # Обработка команд управления группами в ЛС
                            if str(chat_id) == str(ADMIN_CHAT_ID) and has_admin_rights(user_id):
                                if (text_lower.startswith('включить ') or
                                    text_lower.startswith('выключить ') or
                                    text_lower.startswith('админ_действия ') or
                                    text_lower == 'список_групп' or
                                    text_lower.startswith('статус ') or
                                    text_lower in ['группы', 'управление группами']):
                                    handle_group_management(chat_id, user_id, username, text)
                                    continue

                            # Обработка команд с ответом на сообщение
                            if 'reply_to_message' in message and str(chat_id) != str(ADMIN_CHAT_ID):
                                reply_message = message['reply_to_message']
                                target_user_id = reply_message['from']['id']
                                target_username = reply_message['from'].get('username', 'user')
                                target_message_id = reply_message['message_id']

                                print(f"🔁 Ответ на сообщение от @{target_username}")

                                # Команда ИГРАТЬ (крестики-нолики)
                                if text_lower.startswith('играть '):
                                    try:
                                        bet_amount = int(text_lower.split()[1])
                                        if bet_amount <= 0:
                                            send_message(chat_id, "❌ <b>Ставка должна быть положительной!</b>")
                                            continue

                                        if bet_amount < 5:
                                            send_message(chat_id, "❌ <b>Минимальная ставка: 5₽</b>")
                                            continue

                                        handle_tic_tac_toe_invite(chat_id, user_id, target_user_id, username, target_username, bet_amount)
                                    except (ValueError, IndexError):
                                        send_message(chat_id, "❌ <b>Неверный формат! Используйте: играть [ставка]</b>")
                                    continue

                                # Команда ВЫДАТЬ (админ)
                                elif text_lower.startswith('выдать '):
                                    try:
                                        amount = int(text_lower.split()[1])
                                        if has_admin_rights(user_id):
                                            handle_give_money(chat_id, user_id, target_user_id, amount, username, target_username)
                                        else:
                                            send_message(chat_id, "❌ <b>У вас нет прав для этой команды!</b>")
                                    except (ValueError, IndexError):
                                        send_message(chat_id, "❌ <b>Неверный формат! Используйте: выдать [сумма]</b>")
                                    continue

                                # Команда ДАТЬ (для всех пользователей)
                                elif text_lower.startswith('дать '):
                                    try:
                                        amount = int(text_lower.split()[1])
                                        handle_give_money_user(chat_id, user_id, target_user_id, amount, username, target_username)
                                    except (ValueError, IndexError):
                                        send_message(chat_id, "❌ <b>Неверный формат! Используйте: дать [сумма]</b>")
                                    continue

                                # Команда ЗАБРАТЬ (админ)
                                elif text_lower.startswith('забрать '):
                                    try:
                                        amount = int(text_lower.split()[1])
                                        if has_admin_rights(user_id):
                                            handle_take_money(chat_id, user_id, target_user_id, amount, username, target_username)
                                        else:
                                            send_message(chat_id, "❌ <b>У вас нет прав для этой команды!</b>")
                                    except (ValueError, IndexError):
                                        send_message(chat_id, "❌ <b>Неверный формат! Используйте: забрать [сумма]</b>")
                                    continue

                                # Команда ИНФО (админ)
                                elif text_lower == 'инфо':
                                    if has_admin_rights(user_id):
                                        handle_user_info_reply(chat_id, user_id, target_user_id, username, target_username)
                                    else:
                                        send_message(chat_id, "❌ <b>У вас нет прав для этой команды!</b>")
                                    continue

                                # Команда ДАТЬ ПИЗДЫ (для всех) - ИСПРАВЛЕННАЯ ПРОВЕРКА
                                elif 'дать пизды' in text_lower or text_lower == 'пизды':
                                    handle_give_pizdy(chat_id, user_id, target_user_id, username, target_username)
                                    continue

                                # ПЛАТНЫЕ АДМИН КОМАНДЫ (для всех пользователей)
                                elif text_lower == 'мут':
                                    handle_paid_mute(chat_id, user_id, target_user_id, username, target_username)
                                    continue

                                elif text_lower == 'размут':
                                    handle_paid_unmute(chat_id, user_id, target_user_id, username, target_username)
                                    continue

                                elif text_lower == 'бан':
                                    handle_paid_ban(chat_id, user_id, target_user_id, username, target_username)
                                    continue

                                elif text_lower == 'разбан':
                                    handle_paid_unban(chat_id, user_id, target_user_id, username, target_username)
                                    continue

                                elif text_lower == 'кик':
                                    handle_paid_kick(chat_id, user_id, target_user_id, username, target_username)
                                    continue

                                elif text_lower == 'удалить':
                                    handle_paid_delete(chat_id, user_id, target_message_id, username)
                                    continue

                            # Основные команды в группах
                            if str(chat_id) != str(ADMIN_CHAT_ID):
                                # Команда Б (баланс)
                                if text_lower == 'б' or text_lower == 'баланс':
                                    handle_balance_short(chat_id, user_id, username)
                                    continue

                                # Команда админка (помощь по платным командам)
                                elif text_lower == 'админка':
                                    handle_admin_help(chat_id, user_id, username)
                                    continue

                                # Ограбление казны
                                elif text_lower in ['ограбить казну', 'ограбить', 'грабить казну', 'ограбление']:
                                    handle_rob_treasury(chat_id, user_id, username)
                                    continue

                                # Казино
                                elif text_lower.startswith('казино '):
                                    try:
                                        amount_text = text_lower.split()[1]
                                        handle_casino(chat_id, user_id, username, amount_text)
                                    except IndexError:
                                        send_message(chat_id, "❌ <b>Укажите сумму! Используйте: казино [сумма]</b>")
                                    continue

                                elif text_lower == 'казино':
                                    handle_casino_info(chat_id)
                                    continue

                            # Команды с упоминанием бота
                            if is_command_for_me(text, '/start'):
                                handle_start(chat_id, user_id, username)
                                continue

                            elif is_command_for_me(text, '/balance'):
                                handle_balance_short(chat_id, user_id, username)
                                continue

                            elif is_command_for_me(text, '/bonus'):
                                handle_daily_bonus(chat_id, user_id, username)
                                continue

            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен пользователем")
            save_data()
            break
        except Exception as e:
            print(f"❌ Критическая ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
