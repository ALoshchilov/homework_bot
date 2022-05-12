from datetime import datetime, timedelta
import logging
from os import getenv
import requests
import time
from sys import stdout

from dotenv import load_dotenv
from telegram import Bot

from exceptions import NetworkError, HttpResponseError

load_dotenv(override=True)
PRACTICUM_TOKEN = str(getenv('PRACTICUM_TOKEN'))
TELEGRAM_TOKEN = str(getenv('TELEGRAM_TOKEN'))
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
SUCCESS_RESPONSE_CODE = 200
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
LOG_PATH = __file__ + '.log'
# Шаблоны сообщений и записей лога
OK_SEND_MESSAGE_TEMPLATE = (
    'Message: "{message}" successfully send '
    'to chat ({chat_id})'
)
BAD_SEND_MESSAGE_TEMPLATE = (
    'Cannot send message: "{message}" to chat ({chat_id})'
)
CHANGED_HOMEWORK_STATUS_TEMPLATE = (
    'Изменился статус проверки работы "{homework_name}". {verdict}'
)
BAD_ENV_VAR_ERROR_TEMPLATE = (
    'Unexisting or empty environment variable ({name}) was found'
)
WRONG_TYPE_MESSAGE_TEMPLATE = (
    'Wrong datatype for {object} '
    'Got: {got}. Expected: {expected}.'
)
UNKNOWN_HOMEWORK_STATUS_TEMPLATE = 'Status "{homework_status}" is unknown'
STOP_BOT_MESSAGE = 'Stoping bot...'
START_BOT_MESSAGE = 'Starting bot...'
BOT_INIT_ERR_MESSAGE = 'Error durining bot initializing. Check telegram token'
NO_CHECKED_WORKS_MESSAGE = 'No new checked homeworks were found'
NO_GET_API_ANSWER_RESPONSE = 'Empty response from get_api_answer.'


def logger_init():
    """Инициализация настроек логирования..."""
    handlers = [
        logging.StreamHandler(stdout),
        logging.FileHandler(LOG_PATH),
    ]
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s]  %(message)s',
        level=logging.DEBUG,
        handlers=handlers,
    )


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram чат, определяемый переменной окружения...
    TELEGRAM_CHAT_ID. Принимает на вход два параметра: экземпляр класса
    Bot и строку с текстом сообщения.
    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.info(OK_SEND_MESSAGE_TEMPLATE.format(
            message=message,
            chat_id=TELEGRAM_CHAT_ID
        ))
    except Exception:
        logging.exception(BAD_SEND_MESSAGE_TEMPLATE.format(
            message=message,
            chat_id=TELEGRAM_CHAT_ID
        ))


def get_api_answer(current_timestamp: int):
    """
    Делает запрос к единственному эндпоинту API-сервиса. В качестве...
    параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата
    JSON к типам данных Python.
    """
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        raise NetworkError(url=ENDPOINT, headers=HEADERS, params=params)
    response_details = {
        'code': response.status_code,
        'expected_code': SUCCESS_RESPONSE_CODE,
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params,
    }
    if response.status_code != SUCCESS_RESPONSE_CODE:
        raise HttpResponseError(**response_details)
    if isinstance(response, list):
        response = response[0]
    if ('error' or 'code') in response.json():
        raise HttpResponseError(**response_details)
    return response.json()


def check_response(response: dict):
    """Проверяет ответ API на корректность. В качестве параметра функция...
    получает ответ API, приведенный к типам данных Python. Если ответ API
    соответствует ожиданиям, то функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'
    """
    if not response:
        raise IndexError(NO_GET_API_ANSWER_RESPONSE)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(WRONG_TYPE_MESSAGE_TEMPLATE.format(
            object='homeworks info',
            got=type(response),
            expected='dict'
        ))
    # проверка current_date
    response['current_date']
    if homeworks:
        homeworks = homeworks[0]
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы...
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_VERDICTS.
    """
    if not isinstance(homework, dict):
        raise KeyError(WRONG_TYPE_MESSAGE_TEMPLATE.format(
            object='parse_status argument',
            got=type(homework),
            expected='dict'
        ))
    homework_status = homework['status']
    homework_name = homework['homework_name']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(UNKNOWN_HOMEWORK_STATUS_TEMPLATE.format(
            homework_status=homework_status
        ))
    return CHANGED_HOMEWORK_STATUS_TEMPLATE.format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы для работы...
    программы. Если отсутствует хотя бы одна переменная окружения — функция
    должна вернуть False, иначе — True.
    """
    ENV_VARS = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']
    env_vars_correct = True
    for name in ENV_VARS:
        value = globals().get(name)
        if value is None:
            logging.critical(BAD_ENV_VAR_ERROR_TEMPLATE.format(name=name))
            env_vars_correct = False
    return env_vars_correct


def main():
    """Основная логика работы бота..."""
    logging.info(START_BOT_MESSAGE)
    if not check_tokens():
        logging.info(STOP_BOT_MESSAGE)
        exit()
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except Exception:
        logging.critical(BOT_INIT_ERR_MESSAGE)
        logging.info(STOP_BOT_MESSAGE)
        exit()
    last_error = None
    current_timestamp = int(
        (datetime.today() - timedelta(seconds=RETRY_TIME)).timestamp()
    )
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework))
        except Exception as error:
            logging.exception(error)
            if last_error != str(error):
                send_message(bot, str(error))
                last_error = str(error)
        else:
            last_error = None
            current_timestamp = response.get('current_date', current_timestamp)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger_init()
    main()
