import logging
import requests
import time
import os
import telegram
import sys
from dotenv import load_dotenv
from requests.exceptions import RequestException


"""Создаем, добавляем секретные ключи и проверяем на наличие в окружении."""
load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

"""Создаем логгирование."""
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logging.info('Информационное уведомление')
logging.error('Ошибка')
logging.critical('Критическая ошибка')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


class ResponseNot200(Exception):
    """Создание кастомного исключения."""

    pass


class RequestExceptionError(RequestException):
    """Создание кастомного исключения род-кого класса RequestException."""

    pass


def check_token():
    """Проверяем наличие токенов."""
    messgae = ('Отсутствует обязательная переменная окружения: '
               'Программа принудительно остановлена.')
    token = True
    if PRACTICUM_TOKEN is None:
        token = False
        logging.critical(messgae)
    if TELEGRAM_TOKEN is None:
        token = False
        logging.critical(messgae)
    if TELEGRAM_CHAT_ID is None:
        token = False
        logging.critical(messgae)
    return token


def get_api_answer(url, current_timestamp):
    """Запрашиваем АПИ и проверяем соеденение."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    from_date = {'from_date': current_timestamp}
    try:
        response = requests.get(url, from_date, headers=headers)
        if response.status_code != 200:
            message = ('Запрошенный адрес недоступен.'
                       f'Код ответа API: {response.status_code}')
            logging.error(message)
            raise ResponseNot200(message)
        response = response.json()
    except requests.exceptions.RequestException as request_error:
        message = f'Код ответа API (RequestException): {request_error}'
        logging.error(message)
        raise RequestExceptionError(message)
    except ValueError as value_error:
        logging.error('Получен аргумент с некорректным значением')
        raise value_error
    return response


def check_response(response):
    """Проверяем наличие заполненности ответа и возможной ошибки статуса."""
    message = 'Ошибка {}'
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(message.format('типа'))
    if not homeworks:
        logging.error('Получено пустое значение.')
        return False
    homework = homeworks[0]
    if homework.get('status') not in HOMEWORK_STATUSES:
        logging.error(message.format('ключа'))
        raise KeyError('Статус домашней работы ошибочен')
    return homework


def parse_status(homework):
    """Исполняем веррдикт по работе."""
    message = 'Ошибка {}'
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_status is None:
        logging.error(message.format('значения'))
        raise ValueError('отсутсвует значение')
    if homework_name is None:
        logging.error(message.format('значения'))
        raise ValueError('отсутсвует значение')
    if homework_status not in HOMEWORK_STATUSES:
        logging.error(message.format('ключа'))
        raise KeyError(message.format('ключа'))
    verdict = HOMEWORK_STATUSES[homework_status]
    message = (f'Изменился статус проверки работы "{homework_name}". '
               f'{verdict}')
    return message


def send_message(bot, message):
    """Отправляем сообщение клиенту."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logging.info('Сообщение успешно отправлено')
    except telegram.TelegramError:
        logging.error('Сбой при отправке сообщения', exc_info=True)


def main():
    """Исполнительная функция, соеденяет все вышеописанное."""
    if not check_token():
        sys.exit()
    current_timestamp = int(time.time())
    bot = telegram.Bot(TELEGRAM_TOKEN)
    errors = True
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            time.sleep(RETRY_TIME)
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logging.error(message, exc_info=True)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
