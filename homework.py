from datetime import datetime, timedelta
import logging
from os import getenv
import time
# from pprint import pprint
import requests
from sys import stdout

from dotenv import load_dotenv
from telegram import Bot

from exceptions import WrongHttpResponseCodeError

load_dotenv(override=True)
PRACTICUM_TOKEN = str(getenv('PRACTICUM_TOKEN'))
TELEGRAM_TOKEN = str(getenv('TELEGRAM_TOKEN'))
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 20
SUCCESS_RESPONSE_CODE = 200
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
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


def logger_init():
    """Инициирование логгера..."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    format = logging.Formatter('%(asctime)s [%(levelname)s]  %(message)s')
    stream_handler = logging.StreamHandler(stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(format)
    logger.addHandler(stream_handler)
    file_handler = logging.FileHandler(__file__ + '.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(format)
    logger.addHandler(file_handler)
    return logger


logger = logger_init()


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
        logger.info(OK_SEND_MESSAGE_TEMPLATE.format(
            message=message,
            chat_id=TELEGRAM_CHAT_ID
        ))
    except Exception:
        logger.exception(BAD_SEND_MESSAGE_TEMPLATE.format(
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
    timestamp = float(current_timestamp) or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != SUCCESS_RESPONSE_CODE:
        raise WrongHttpResponseCodeError(
            code=response.status_code,
            expected_code=SUCCESS_RESPONSE_CODE,
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
    response_json = response.json()
    if not isinstance(response_json, (dict, list)):
        raise TypeError(
            (
                'Wrong datatype for response json data. '
                f'Got: {type(response.json())}. Expected: dict.'
            )
        )
    if isinstance(response_json, list):
        response_json = response_json[0]
    homeworks = response_json.get('homeworks')
    if homeworks is None:
        data = {
            "homeworks": None,
            "current_date": response_json.get('current_date')
        }
        return data
    all_homeworks = []
    for homework in homeworks:
        if isinstance(homework, dict):
            homework_info = {
                'homework_name': homework.get('homework_name'),
                'status': homework.get('status')
            }
            all_homeworks.append(homework_info)
    data = {
        "homeworks": all_homeworks,
        "current_date": response_json.get('current_date')
    }
    return data


def check_response(response: dict):
    """Проверяет ответ API на корректность. В качестве параметра функция...
    получает ответ API, приведенный к типам данных Python. Если ответ API
    соответствует ожиданиям, то функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'
    """
    if not response:
        raise IndexError('Empty response from get_api_answer.')
    if not isinstance(response, dict):
        raise TypeError(
            (
                'Wrong datatype for response from get_api_answer. '
                f'Got: {type(response)}. Expected: dict.'
            )
        )
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError(
            'Key "homeworks" is not found in response from get_api_answer'
        )
    if response.get('current_date') is None:
        raise KeyError(
            'Key "current_date" is not found in response from get_api_answer'
        )
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы...
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_VERDICTS.
    """
    homework_status = homework['status']
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise KeyError(f'Verdict "{homework_status}" is unknown')
    return CHANGED_HOMEWORK_STATUS_TEMPLATE.format(
        homework_name=homework_name,
        verdict=verdict
    )


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы для работы...
    программы. Если отсутствует хотя бы одна переменная окружения — функция
    должна вернуть False, иначе — True.
    """
    ENV_VARS = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']
    is_env_vars_correct = True
    for name in ENV_VARS:
        value = globals().get(name)
        if value is None:
            logger.critical(BAD_ENV_VAR_ERROR_TEMPLATE.format(name=name))
            is_env_vars_correct = False
    return is_env_vars_correct


def main():
    """Основная логика работы бота..."""
    logger.info('Starting bot...')
    if not check_tokens():
        logger.info('Stoping bot...')
        exit()
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except Exception:
        logger.critical(
            'Error durining bot initializing. Check telegram token'
        )
        logger.info('Stoping bot...')
        exit()
    last_error = None
    current_timestamp = int(
        # (datetime.today() - timedelta(seconds=RETRY_TIME)).timestamp()
        (datetime.today() - timedelta(days=90)).timestamp()
    )
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    send_message(bot, parse_status(homework))
            else:
                logger.debug('No new checked homeworks were found')
            current_timestamp = response.get('current_date')
        except Exception as error:
            logger.exception(error)
            if last_error != str(error):
                send_message(bot, str(error))
                last_error = str(error)
        else:
            last_error = None
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
