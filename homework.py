import logging
import os
import sys
import time
from contextlib import suppress
from http import HTTPStatus
from json.decoder import JSONDecodeError

import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException
from telebot import TeleBot
from telebot.apihelper import ApiException


# Загрузка переменных окружения
load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


def check_tokens():
    """Проверяет наличие необходимых переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for key, value in tokens.items():
        if not value:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {key}')
            raise EnvironmentError(
                f'Отсутствует обязательная переменная окружения: {key}')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except ApiException as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API сервиса Практикум Домашка."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
        if not response.status_code == HTTPStatus.OK:
            logging.error(f'Ошибка при запросе к API: {response.status_code}')
            raise Exception('Ошибка доступа')
        return response.json()
    except JSONDecodeError:
        logging.error('Ответ от API не является JSON')
        raise
    except RequestException as e:
        logging.error(f'Ошибка при запросе к API: {e}')
        error_message = 'Дополнительная информация:' + e
        raise error_message


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError('В ответе API нет ключа "homeworks"')
    except TypeError:
        raise TypeError('Ответ API должен быть словарём')

    if not isinstance(homeworks, list):
        raise TypeError('По ключу "homeworks" должно быть значение типа list')

    current_date = response.get('current_date')
    if current_date is None:
        logging.warning('Ответ API не содержит ключа "current_date"')

    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы из информации о ней."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as e:
        raise KeyError(f'В ответе API нет ключа "{e.args[0]}"')

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы: {homework_status}')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    new_status_found = False

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
                new_status_found = False
            else:
                if not new_status_found:
                    logging.debug('Нет новых статусов для домашек.')
                    new_status_found = True
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
            with suppress(Exception):
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
