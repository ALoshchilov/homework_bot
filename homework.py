from datetime import datetime, timedelta
import logging
from os import getenv
import time
from pprint import pprint
import requests
from sys import stdout

from dotenv import load_dotenv
from telegram import Bot

from exceptions import NetworkError, HttpResponseError

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
    logger = logging.getLogger('homework_status_checker_bot')
    format = logging.Formatter('%(asctime)s [%(levelname)s]  %(message)s')
    handlers = [
        logging.StreamHandler(stdout),
        logging.FileHandler(__file__ + '.log'),
    ]
    for handler in handlers:
        handler.setFormatter(format)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


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
    response_json = response.json()
    if isinstance(response_json, list):
        response_json = response_json[0]
    # pprint(response_json)
    if ('error' or 'code') in response_json:
        raise Exception((
            'An error detected from json response. RESPONSE DETAILS: '
            f'{response_details}. Error text: {response_json.get("error")} '
            f'Error code: {response_json.get("code")} '
        ))
    return response_json


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
                f'Got: {type(response)}. Expected: dict or list.'
            )
        )
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Booooooooooooooooom')
    if homeworks is None:
        raise KeyError(
            'Key "homeworks" is not found in response from get_api_answer'
        )
    if response.get('current_date') is None:
        raise KeyError(
            'Key "current_date" is not found in response from get_api_answer'
        )
    if isinstance(homeworks, list):
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
        # в автотестах захардкожен KeyError (╯ ° □ °) ╯ (┻━┻)
        raise KeyError('А ЭТО НЕ СЛОВАРЬ!!!')
    homework_status = homework['status']
    homework_name = homework['homework_name']
    if homework_status not in HOMEWORK_VERDICTS:
        # в автотестах захардкожен KeyError (╯ ° □ °) ╯ (┻━┻)
        raise KeyError(f'Status "{homework_status}" is unknown')
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
    try:
        logger
    except NameError:
        logger = logger_init()
    for name in ENV_VARS:
        value = globals().get(name)
        if value is None:
            logger.critical(BAD_ENV_VAR_ERROR_TEMPLATE.format(name=name))
            env_vars_correct = False
    return env_vars_correct


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
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework))
            else:
                logger.debug('No new checked homeworks were found')
        except Exception as error:
            logger.exception(error)
            if last_error != str(error):
                send_message(bot, str(error))
                last_error = str(error)
        else:
            last_error = None
            current_timestamp = response.get('current_date', current_timestamp)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logger_init()
    main()

# if __name__ == '__main__':
#     from unittest import TestCase, mock, main as uni_main
#     ReqEx = requests.RequestException           # Короткое имя для ожидаемого исключения

# #   main()                                      # Старый вызов
#     class TestReq(TestCase):                    # Часть трюка
#         @mock.patch('requests.get')             # Указание, что будем подменять requests.get
#         def test_raised(self, rq_get):          # Второй параметр - это подмена для requests.get
#             rq_get.side_effect = mock.Mock(     # Главный трюк - настраиваем подмену, чтобы
#                 side_effect=ReqEx('testing'))   #   бросалось это исключение
#             main()                              # Все подготовили, запускаем
#     uni_main()


# if __name__ == '__main__':
#     from unittest import TestCase, mock, main as uni_main
#     JSON = {'error': 'testing', 'code': 404, 'code1': 'someshit'}
#     class TestReq(TestCase):            # Часть трюка
#         @mock.patch('requests.get')     # Указание, что будем подменять requests.get
#         def test_error(self, rq_get):   # Второй параметр - это подмена для requests.get
#             resp = mock.Mock()          # Главный трюк
#             resp.status_code = 200
#             resp.json = mock.Mock(      #   настраиваем подмену, чтобы
#                 return_value=JSON)      #   при вызове .json() возвращался
#             rq_get.return_value = resp  #   такой JSON
#             main()                      # Все подготовили, запускаем
#     uni_main()
