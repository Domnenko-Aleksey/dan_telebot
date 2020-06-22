# dan_bot / coursera_dan_bot
# 1236969954:AAFFYd_E4RgUPCyOqJfvd33I8q5E0TQ22JM
# Google Api AIzaSyBJ0kAFsa3hA61MVpbPbtdqjkGuhaay1kg
# ------- ПРИНЦИП РАБОТЫ -------
# Бот обрабатывает 3 состояни запросов
# 1. Команды /add /list /reset /help
# 2. Прочие сообщения (default_answer) - выдавая текстовую заглушку
# 3. Шаги из памяти (default_answer + функция шага)
# ADD_NAME - "Добавить наименование места", вызов функции add_name
# ADD_LOCATION - "Добавить локацию места", вызов функции add_location
# ADD_PHOTO - "Добавить фото", вызов функции add_photo
# Шшаги хранятся в словаре USER_STATE, где находятся временные данные - до нажатия кнопки "Сохранить" = сохранить в БД:
# {'chat_id': {
#       'step': 'ADD_NAME',
#       'add_name': 'Название локации',
#       'add_location': {
#           'longitude': 50.216169,
#           'latitude': 53.234108
#       },
#       'add_photo': ''
#   }
# }
# user_init - инициализация пользователя - добавление в словарь или обнуление данных
# --- REDUS ---
# В REDUS записываем данные в формате
# time_id = datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
# {chat_id: {
#       time_id: {
#           'name': 'Место 1',
#           'location': '50.216169;53.234108',
#           'photo': '111_222_333.jpg'   
#       },
#       time_id: {
#           'name': 'Место 1',
#           'location': '50.216169;53.234108',
#           'photo': '111_222_333.jpg'   
#       },
#   } 
# } 
#
#

import datetime
import telebot
from telebot import types

token = '1236969954:AAFFYd_E4RgUPCyOqJfvd33I8q5E0TQ22JM'
bot = telebot.TeleBot(token)
print('--- BOT START---')

# REDIS (не используем БД - все храним в словаре STORAGE)
# r = redis.StrictRedis(host='localhost', port=6379, db=1)

STORAGE = {}  # Хранилищем данных
USER_STATE = {}  # Временный словарь пользователя
STEPS = ['ADD_NAME', 'ADD_LOCATION', 'ADD_PHOTO']  # Шаги


# Приём прочих сообщений.
@bot.message_handler(func=lambda message: message.text not in ['/add', '/list', '/reset', '/help'])
@bot.message_handler(commands=['start'])
@bot.message_handler(content_types=['location'])
@bot.message_handler(content_types=['photo'])
def default_answer(message):
    # Если нет пользователя - создаём словарь пользователя
    if message.chat.id not in USER_STATE:
        user_init(message.chat.id)

    print("\n======= default_answer(), USER_STATE:", USER_STATE)

    # Проверка на шаги . вывод default текста
    if USER_STATE[message.chat.id]['step'] in STEPS:
        # Для каждого шага есть своя функция, пример: ADD_NAME -> def add_name(message)
        func = USER_STATE[message.chat.id]['step'].lower()
        # Вызов функции по её строковому наименованию
        globals()[func](message)
    else:
        t = "Привет, я <b>учебный бот</b>. Могу соханять и выводить списком геолокации с описанием и фотографиями:\n"
        # Создаём клавиатуру

        keyboard = create_keyboard()
        bot.send_message(chat_id=message.chat.id, text=t,
                         parse_mode='HTML', reply_markup=keyboard)


# --- КОМАНДЫ ---
# Помощь
@bot.message_handler(commands=['help'])
def commands_help(message):
    user_init(message.chat.id)
    t = "Бот сохраняет название места, фото и геолокацию. Выводит списком сохранённые места. \n\n"
    t += "<b><u>Команды:</u></b> \n"
    t += "/add - добавить новоe место \n"
    t += "/list - отображение добавленых мест \n"
    t += "/reset - удалить все локации \n"
    t += "/help - помощь \n"
    bot.send_message(chat_id=message.chat.id, text=t, parse_mode='HTML')
    print(message.text)


# Добавить новое место.
@bot.message_handler(commands=['add'])
def commands_add(message):
    user_init(message.chat.id)

    # Отпраляем сообщение
    t = "Добавьте название нового места:"
    bot.send_message(chat_id=message.chat.id, text=t)
    USER_STATE[message.chat.id]['step'] = 'ADD_NAME'
    print("\n======= commands_add(), USER_STATE:", USER_STATE)


# Список мест.
@bot.message_handler(commands=['list'])
def commands_list(message):
    user_init(message.chat.id)
    location_list = db_get_list(message.chat.id)

    t = "<b>Список последних 10 мест:</b> \n"
    bot.send_message(chat_id=message.chat.id, text=t, parse_mode='HTML')

    if message.chat.id in STORAGE:
        storage_chat = STORAGE[message.chat.id][-1:-11:-1]
        for item in storage_chat:
            # t = item['name'] + "\n"
            t = "\n------------------------------------\n\n"

            image_path = 'photo/' + item['photo']
            image_file = open(image_path, 'rb')
            longitude, latitude = item['location'].split(';')

            bot.send_photo(message.chat.id, image_file, caption=item['name'])
            bot.send_location(message.chat.id, latitude, longitude)
            bot.send_message(chat_id=message.chat.id, text=t, parse_mode='HTML')
            
            t = "Выберите команду:\n"
    else:
        t = "<i>Список пуст</i>\n"

    keyboard = create_keyboard()
    bot.send_message(chat_id=message.chat.id, text=t, parse_mode='HTML', reply_markup=keyboard)


# Удалить все локации.
@bot.message_handler(commands=['reset'])
def commands_reset(message):
    user_init(message.chat.id)

    if message.chat.id in STORAGE:
        del STORAGE[message.chat.id]

    t = "Все локации удалены. \n"
    bot.send_message(chat_id=message.chat.id, text=t)
    default_answer(message)


# --- ПОЛЬЗОВАТЕЛЬ ---
# Инициализация пользователя
def user_init(chat_id):
    USER_STATE[chat_id] = {
        'step': '',
        'add_name': '',
        'add_location': {
            'longitude': 0,
            'latitude': 0
        },
        'add_photo': ''
    }


# --- ШАГИ ---
# Добавляем наименование локации
def add_name(message):
    if (len(message.text) < 1):
        t = "Укажите название места:"
        bot.send_message(chat_id=message.chat.id, text=t)
        return

    if (len(message.text) > 255):
        t = "Название слишком длинное, укажите корректное название:"
        bot.send_message(chat_id=message.chat.id, text=t)
        return

    USER_STATE[message.chat.id]['add_name'] = message.text
    USER_STATE[message.chat.id]['step'] = 'ADD_LOCATION'
    t = "Выберите локацию:"
    bot.send_message(chat_id=message.chat.id, text=t)
    print("\n======= add_name(), USER_STATE:", USER_STATE)


# Добавляем локацию
def add_location(message):
    if not message.location:
        t = "Ошибка, не указана локация. \n"
        t += "Локация доступна только в телефоне. Что бы добавить локацию совершите следующие действия: \n"
        t += "1. Нажмите скрепку \n"
        t += "2. Выбертие иконку <b>Геопозиция</b> \n"
        t += "3. Нажмите <b>Отправить свою геопозиция</b> \n"
        bot.send_message(chat_id=message.chat.id, text=t, parse_mode='HTML')
        return

    t = "Добавить фото:"
    bot.send_message(chat_id=message.chat.id, text=t)
    USER_STATE[message.chat.id]['add_location'] = {'longitude':message.location.longitude, 'latitude':message.location.latitude}
    USER_STATE[message.chat.id]['step'] = 'ADD_PHOTO'
    print("\n======= add_location(), USER_STATE:", USER_STATE)


# Добавляем фото
def add_photo(message):
    if not message.photo:
        t = "Ошибка, не выбрано фото. \n"
        t += "Добавьте фото. \n"
        bot.send_message(chat_id=message.chat.id, text=t, parse_mode='HTML')
        return

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)

    dt = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = str(message.chat.id) + '_' + dt + '.jpg'

    downloaded_file = bot.download_file(file_info.file_path)
    with open('photo/' + file_name, 'wb') as file_new:
        file_new.write(downloaded_file)
    
    USER_STATE[message.chat.id]['add_photo'] = file_name
    USER_STATE[message.chat.id]['step'] = ''

    # Записываем мето в БД
    db_add(message.chat.id)
    t = "Место добавлено"
    bot.send_message(chat_id=message.chat.id, text=t)
    print("\n======= add_photo(), USER_STATE:", USER_STATE)
    default_answer(message)


# --- КЛАВИАТУРА ---
# Создание клавиатуры
def create_keyboard():
    buttons_data = {
        'Добавить место': 'commands_add',
        'Список мест': 'commands_list',
        'Удалить всё': 'commands_reset',
        'Помощь': 'commands_help'
    }
    # Создаём inline клавиатуру c количеством кнопок в ряду = 2
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    # Создаём кнопки - наименование 'key' и передаваемая строка 'callback_data[key]'
    buttons = [types.InlineKeyboardButton(
        text=key, callback_data=buttons_data[key]) for key in buttons_data]
    keyboard.add(*buttons)
    return keyboard


# Обработка нажатий клавиатуры
@bot.callback_query_handler(func=lambda x: True)  # Всегда
def keyboard_handler(callback_query):
    message = callback_query.message
    command = callback_query.data  # Команда, полученая с кнопки
    globals()[command](message)  # Вызываемфункцию по имени команды


# --- БАЗА ДАННЫХ ---
# Добавить новую точку
def db_add(chat_id):
    name = USER_STATE[chat_id]['add_name']
    location = str(USER_STATE[chat_id]['add_location']['longitude']) + ';' + str(USER_STATE[chat_id]['add_location']['latitude'])
    photo = USER_STATE[chat_id]['add_photo']

    data = {}
    time_id = datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
    data = {
        'name': name,
        'location': location,
        'photo': photo  
    }
    data_list = []
    data_list.append(data)

    if chat_id not in STORAGE:
        # Создаём запись        
        STORAGE[chat_id] = data_list
    else:
        # Добавляем запись
        STORAGE[chat_id].append(data)

    print("\n======= db_add():\nchat_id:", chat_id, "\nname:", name, "\nlocation:", location, "\nphoto:", photo, "\n")
    print("\n======= db_add(), STORAGE", STORAGE)


# Получаем список мест
def db_get_list(chat_id):
    print("\n======= db_list(), rows:")


# Получаем информацию о месте
def db_get_item(id):
    print("\n======= db_get_item(), row:")


# Удаляем все локации для chat_id
def db_delete(chat_id):
    print("\n======= db_delete()")


# --- ЗАПУСК ---
bot.polling()

"""
# Отправляем локацию
latitude, longitude = 53.213245, 50.183825
bot.send_location(message.chat.id, latitude, longitude)
print('LOCATION', message.location)


# Принимаем изображение
file_id = message.photo[-1].file_id
file_info = bot.get_file(file_id)
print('PHOTO file_id', file_id)
downloaded_file = bot.download_file(file_info.file_path)
with open("downloads/image.jpg", 'wb') as new_file:
    new_file.write(downloaded_file)

# Отправляем изображение
image = open('logo.png', 'rb')
bot.send_photo(message.chat.id, image, caption="Союз")
"""
