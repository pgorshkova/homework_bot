import os
import time
import logging
from http import HTTPStatus

from dotenv import load_dotenv
import requests
import telegram

from exceptions import APIErrException

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
formatter = '%(asctime)s, %(levelname)s, %(message)s'
handler = logging.StreamHandler()
logger.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в чат"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Бот отправил сообщение : {message}')
    except telegram.error.TelegramError(message):
        logger.error(f'Ошибка при отправке сообщения: {message}')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту Practicum.Homeworks API"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException:
        message = 'Эндпоинт не найден.'
        raise APIErrException(message)

    if response.status_code != HTTPStatus.OK:
        message = (f'Эндпоинт {ENDPOINT} недоступен, '
                   f'http status: {response.status_code}')
        raise APIErrException(message)

    return response.json()


def check_response(response):
    """Проверка ответа API на корректность"""
    if isinstance(response, list):
        response = response[0]
        logger.info('API передал список')
    if not isinstance(response, dict):
        logger.error('API передал не словарь')
        raise TypeError('API передал не словарь')
    homework = response.get('homeworks')
    if homework is None:
        logger.error('API не содержит ключа homeworks')
        raise KeyError('API не содержит ключа homeworks')
    if not isinstance(homework, list):
        logger.error('Содержимое не список')
        raise TypeError('Содержимое не список')
    return homework


def parse_status(homework):
    """Извлекает статус работы из ответа ЯндексПрактикум."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.error('В ответе API нет ключа homework_name')
        raise KeyError('В ответе API нет ключа homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        logger.error('В ответе API нет ключа homework_status')
        raise KeyError('В ответе API нет ключа homework_status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logger.error('Неизвестный статус')
        raise KeyError('Неизвестный статус')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие токенов"""
    variables = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for variable in variables:

        if not variable:
            logger.critical(
                f'Переменная {variable} не определена.'
            )
            return False

    return True


def main():
    """Основная логика работы бота."""

    if not check_tokens():
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    prev_upd_time = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            hw_list = check_response(response)

            for homework in hw_list:
                upd_time = homework.get('date_updated')

                if upd_time != prev_upd_time:
                    prev_upd_time = upd_time
                    message = parse_status(homework)
                    send_message(bot, message)
            current_timestamp = int(time.time())

        except APIErrException as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)

        except Exception as error:
            logger.exception(error)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
