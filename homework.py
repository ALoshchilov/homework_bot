import logging
from os import getenv
from sys import stdout
import time

from dotenv import load_dotenv
import requests
from telegram import Bot

from exceptions import JsonDetectedResponseError, WrongHttpCodeError


load_dotenv(override=True)
PRACTICUM_TOKEN = getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')
ENV_VARS = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']
RETRY_TIME = 20
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
BAD_ENV_VAR_ERROR_TEMPLATE = (
    'Unexisting or empty environment variables were found: {vars}'
)
BAD_SEND_MESSAGE_TEMPLATE = (
    'Cannot send message: "{message}" to chat ({chat_id}). Error: {error}.'
)
CHANGED_HOMEWORK_STATUS_TEMPLATE = (
    'Изменился статус проверки работы "{homework_name}". {verdict}'
)
CONNECTION_ERROR_TEMPLATE = (
    'An error occured during request {url}.'
    'DETAILS. Headers: {headers}. Params: {params}. '
    'Error message: {error}'
)
LAST_FRONTIER_ERROR_TEMPLATE = (
    'An error occured during the itteration. Error text: {error}'
)
OK_SEND_MESSAGE_TEMPLATE = (
    'Message: "{message}" successfully send to chat ({chat_id})'
)
RESPONSE_ERROR_IN_JSON_TEMPLATE = (
    'An error was found in json response from {url} '
    'DETAILS: Headers: {headers}. Parameters: {params} '
    'The error detected in key: {error_key}. Error description: "{error}"'
)
UNKNOWN_HOMEWORK_STATUS_TEMPLATE = 'Status "{homework_status}" is unknown'
WRONG_HTTP_RESPONSE_ERROR_TEMPLATE = (
    'Wrong HTTP response code from {url}. '
    'Got: {code}. Expected: {expected_code}. '
    'Details. HEADERS: {headers}, PARAMETERS: {params}'
)
WRONG_TYPE_MESSAGE_TEMPLATE = (
    'Wrong datatype for {object} '
    'Got: {got}. Expected: {expected}.'
)

BOT_INIT_ERR_MESSAGE = 'Error durining bot initializing. Check telegram token'
NO_CHECKED_WORKS_MESSAGE = 'No new checked homeworks were found'
NO_GET_API_ANSWER_RESPONSE = 'Null or empty response from get_api_answer.'
NO_HOMEWORKS_KEY_IN_RESPONSE = (
    'Key "homeworks" not found in check_response argument'
)
SEND_ERROR_INFO_EXCEPTION = (
    f'An error occured during send error info to chat ({TELEGRAM_CHAT_ID})'
)
START_BOT_MESSAGE = 'Starting bot...'
STOP_BOT_MESSAGE = ' Stoping bot... Reasone: Bad environment variables'
# текстовое описание объектов для подстановки в сообщение
CHECK_RESPONSE_ARGUMENT_OBJECT = 'check_response argument'
HOMEWORKS_INFO_OBJECT = 'homeworks info'


def logger_init():
    """Инициализация настроек логирования..."""
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s]  %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(stdout),
            logging.FileHandler(LOG_PATH),
        ],
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
    except Exception as error:
        logging.exception(BAD_SEND_MESSAGE_TEMPLATE.format(
            message=message,
            chat_id=TELEGRAM_CHAT_ID,
            error=error
        ))
    return True


def get_api_answer(current_timestamp: int):
    """
    Делает запрос к единственному эндпоинту API-сервиса. В качестве...
    параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата
    JSON к типам данных Python.
    """
    params = {'from_date': current_timestamp}
    request_details = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }
    try:
        response = requests.get(**request_details)
    except requests.RequestException as error:
        raise ConnectionError(CONNECTION_ERROR_TEMPLATE.format(
            error=error,
            **request_details
        ))
    if response.status_code != SUCCESS_RESPONSE_CODE:
        raise WrongHttpCodeError(WRONG_HTTP_RESPONSE_ERROR_TEMPLATE.format(
            **request_details,
            code=response.status_code,
            expected_code=SUCCESS_RESPONSE_CODE
        ))
    response_json = response.json()
    for error_key in ['error', 'code']:
        if error_key in response_json:
            raise JsonDetectedResponseError(
                RESPONSE_ERROR_IN_JSON_TEMPLATE.format(
                    **request_details,
                    error_key=error_key,
                    error=response_json.get(error_key)
                )
            )
    return response_json


def check_response(response: dict):
    """Проверяет ответ API на корректность. В качестве параметра функция...
    получает ответ API, приведенный к типам данных Python. Если ответ API
    соответствует ожиданиям, то функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'
    """
    if not response:
        raise ValueError(NO_GET_API_ANSWER_RESPONSE)
    if not isinstance(response, dict):
        raise TypeError(WRONG_TYPE_MESSAGE_TEMPLATE.format(
            object=CHECK_RESPONSE_ARGUMENT_OBJECT,
            got=type(response),
            expected='dict'
        ))
    if 'homeworks' not in response:
        raise KeyError(NO_HOMEWORKS_KEY_IN_RESPONSE)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(WRONG_TYPE_MESSAGE_TEMPLATE.format(
            object=HOMEWORKS_INFO_OBJECT,
            got=type(homeworks),
            expected='list'
        ))
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
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(UNKNOWN_HOMEWORK_STATUS_TEMPLATE.format(
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
    missing_vars = [name for name in ENV_VARS if globals().get(name) is None]
    if missing_vars:
        logging.critical(BAD_ENV_VAR_ERROR_TEMPLATE.format(vars=missing_vars))
        return False
    return True


def main():
    """Основная логика работы бота..."""
    logging.info(START_BOT_MESSAGE)
    if not check_tokens():
        logging.critical(STOP_BOT_MESSAGE)
        raise EnvironmentError(STOP_BOT_MESSAGE)
    bot = Bot(token=TELEGRAM_TOKEN)
    last_error = None
    current_timestamp = 0
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                continue
            if send_message(bot, parse_status(homeworks[0])):
                current_timestamp = response.get(
                    'current_date', current_timestamp
                )
        except Exception as error:
            logging.exception(LAST_FRONTIER_ERROR_TEMPLATE.format(error=error))
            if last_error == str(error):
                continue
            if send_message(bot, LAST_FRONTIER_ERROR_TEMPLATE.format(
                    error=error
            )):
                last_error = str(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger_init()
    main()
