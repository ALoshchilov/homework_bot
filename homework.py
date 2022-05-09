from datetime import datetime, timedelta
import logging
from os import getenv
import requests
import time

from dotenv import load_dotenv
from telegram import Bot

load_dotenv(override=True)
PRACTICUM_TOKEN = str(getenv('PRACTICUM_TOKEN'))
TELEGRAM_TOKEN = str(getenv('TELEGRAM_TOKEN'))
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
last_error = None
logging.basicConfig(
    format='%(asctime)s [%(levelname)s]  %(message)s',
    level=logging.DEBUG,
    filename='homework_status_checker.log',
    filemode='a'
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
        logging.info(
            (
                f'Message: "{message}" successfully send to chat '
                f'({TELEGRAM_CHAT_ID})'
            )
        )
    except Exception:
        logging.error(
            f'Cannot send message: "{message}" to chat ({TELEGRAM_CHAT_ID})'
        )


def get_api_answer(current_timestamp: int):
    """
    Делает запрос к единственному эндпоинту API-сервиса. В качестве...
    параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата
    JSON к типам данных Python.
    """
    SUCCESS_RESPONSE_CODE = 200
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != SUCCESS_RESPONSE_CODE:
        response.raise_for_status()
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
    HOMEWORK_STATUSES.
    """
    homework_status = homework.get('status')
    if not homework_status:
        raise KeyError('Key "homework_status" is not found in homework info')
    homework_name = homework.get('homework_name')
    print(homework_name)
    if not homework_name:
        raise KeyError('Key "homework_name" is not found in homework info')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logging.error(f'Verdict "{homework_status}" is unknown')
        raise KeyError(f'Verdict "{homework_status}" is unknown')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы для работы...
    программы. Если отсутствует хотя бы одна переменная окружения — функция
    должна вернуть False, иначе — True.
    """
    ENV_VARS = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    for variable in ENV_VARS:
        if variable is None:
            logging.critical(
                'Ошибка. Обнаружена пустая или несуществующая '
                f'переменная окружения {variable}'
            )
            return False
    return True


def error_handler(error, bot):
    """Логирует текст ошибки error и проверяет равна ли ошибка error ошибке...
    last_error. В случае различия отправляет сообщение с текстом ошибки
    error через телеграм-бот bot и возвращает True. В случае совпадения
    возвращает False.
    """
    logging.error(error)
    global last_error
    if last_error == str(error):
        return False
    send_message(bot, str(error))
    last_error = str(error)
    return True


def bot_init():
    """Инициирование бота..."""
    logging.info('Starting bot...')
    if not check_tokens():
        logging.info('Stoping bot...')
        exit()
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except Exception:
        logging.critical(
            'Error durining bot initializing. Check telegram token'
        )
        logging.info('Stoping bot...')
        exit()
    return bot


def main():
    """Основная логика работы бота..."""
    global last_error
    bot = bot_init()
    current_timestamp = int(
        (datetime.today() - timedelta(seconds=RETRY_TIME)).timestamp()
    )
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    send_message(bot, parse_status(homework))
            else:
                logging.debug('No new checked homeworks were found')
            current_timestamp = response.get('current_date')
        except Exception as error:
            error_handler(error, bot)
        else:
            last_error = None
        finally:
            logging.debug(f'Sleep {RETRY_TIME} seconds and go to next loop')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
