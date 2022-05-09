from datetime import datetime, timedelta
import logging
from os import getenv, environ
from pprint import pprint
import requests
import time

from dotenv import load_dotenv
from telegram import Bot

from exceptions import (
    EmptyDictonaryError, UnknownHomeworkStatusError, WrongHttpResponseCodeError,
    WrongTypeError, KeyNotFound
)


load_dotenv(override=True)


PRACTICUM_TOKEN = str(getenv('PRACTICUM_TOKEN'))
TELEGRAM_TOKEN = str(getenv('TELEGRAM_TOKEN'))
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s [%(levelname)s]  %(message)s',
    level=logging.DEBUG,
    filename='homework_status_checker.log',
    filemode='a'
)

def send_message(bot, message):
    """
    Отправляет сообщение в Telegram чат, определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot и строку с текстом сообщения.
    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,        
        )
        logging.info(f'Message: "{message}" successfully send to chat ({TELEGRAM_CHAT_ID})')
    except:
        logging.error(f'Cannot send message: "{message}" to chat ({TELEGRAM_CHAT_ID})')


def get_api_answer(current_timestamp):
    """
     Делает запрос к единственному эндпоинту API-сервиса. В качестве параметра функция
     получает временную метку. В случае успешного запроса должна вернуть ответ API, 
     преобразовав его из формата JSON к типам данных Python.
    """
    SUCCESS_RESPONSE_CODE = 200
    print(0)
    timestamp = int(current_timestamp) or int(time.time())
    print(timestamp)
    params = {'from_date': timestamp}
    print(current_timestamp)
    print(params['from_date'])

    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != SUCCESS_RESPONSE_CODE:        
        raise WrongHttpResponseCodeError(
            f'Wrong HTTP-response. Got: {response.status_code}. Expected: {SUCCESS_RESPONSE_CODE}.'
        )
    if not isinstance(response.json(), dict):
        raise WrongTypeError(
            f'Wrong datatype for response json data. Got: {type(response.json())}. Expected: dict.'
        )

    print(1)
    homeworks = response.json().get('homeworks')
    if homeworks is None:
        raise KeyNotFound('Key "homeworks" is not found in json format of response')
    print(2)
    all_homeworks = []
    for homework in homeworks:
        if not isinstance(homework, dict):
            raise WrongTypeError(
                f'Wrong datatype for homework info data. Got: {type(homework)}. Expected: dict.'
            )
        else:    
            homework_info = {
                'homework_name': homework.get('homework_name'),
                'status': homework.get('status')
            }
            all_homeworks.append(homework_info)

    data = {
        "homeworks": all_homeworks,
        "current_date": response.json().get('current_date')
    }
    print(data.get('current_date'))
    return data


def check_response(response):
    """
    Проверяет ответ API на корректность. В качестве параметра функция получает ответ API,
    приведенный к типам данных Python. Если ответ API соответствует ожиданиям, то функция
    должна вернуть список домашних работ (он может быть и пустым), доступный в ответе API
    по ключу 'homeworks'
    """
    if not response:
        raise EmptyDictonaryError(
            f'Empty response from get_api_answer.'
        )
    if not isinstance(response, dict):
        raise WrongTypeError(
            f'Wrong datatype for response from get_api_answer. Got: {type(response)}. Expected: dict.'
        )
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyNotFound('Key "homeworks" is not found in response from get_api_answer')
    return homeworks


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы. В качестве
    параметра функция получает только один элемент из списка домашних работ. В случае успеха,
    функция возвращает подготовленную для отправки в Telegram строку, содержащую один из
    вердиктов словаря HOMEWORK_STATUSES.
    """
        
    homework_status = homework.get('status')
    if not homework_status:
        raise KeyNotFound('Key "homework_status" is not found in homework info')
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyNotFound('Key "homework_name" is not found in homework info')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise KeyNotFound(f'Verdict "{homework_status}" is unknown')        
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """
    Проверяет доступность переменных окружения, которые необходимы для работы программы.
    Если отсутствует хотя бы одна переменная окружения — функция должна вернуть 
    False, иначе — True.
    """
    ENV_VARS = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    for variable in ENV_VARS:
        if variable is None:
            logging.critical(f'Ошибка. Обнаружена пустая или несуществующая переменная окружения {variable}')
            return False
    return True

def is_error_changed(error, last_error, bot):
    """    
    Логирует текст ошибки error и проверяет равна ли ошибка error ошибке last_error. 
    В случае различия отправляет сообщение с текстом ошибки error через телеграм-бот bot
    и возвращает True. В случае совпадения возвращает False
    """
    logging.error(error)
    if last_error == error:        
        return False
    send_message(bot, str(error))
    return True


def main():
    """Основная логика работы бота."""
    logging.info('Starting bot...')
    if not check_tokens():        
        logging.info('Stoping bot...')
        exit()
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except:
        logging.critical('Error durining bot initializing. Check telegram token')
        logging.info('Stoping bot...')
        exit()
    last_error = None
    current_timestamp = (datetime.today() - timedelta(days=60)).timestamp()
    while True:
        print(current_timestamp)
        print(last_error)
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    print(message)
                    if message:
                        send_message(bot, message)
            else:
                logging.debug('No new checked homeworks were found')
            current_timestamp = response.get('current_date')

        except WrongHttpResponseCodeError as error:
            if is_error_changed(error, last_error, bot):
                last_error = error
        except WrongTypeError as error:            
            if is_error_changed(error, last_error, bot):
                last_error = error
        except EmptyDictonaryError as error:
            if is_error_changed(error, last_error, bot):
                last_error = error
        except KeyNotFound as error:
            if is_error_changed(error, last_error, bot):
                last_error = error
        except Exception as error:
            if is_error_changed(error, last_error, bot):
                last_error = error
        else:
            last_error = None
        finally:
            logging.debug(f'Sleep {RETRY_TIME} seconds and go to next loop')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
