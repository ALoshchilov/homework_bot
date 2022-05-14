class WrongHttpCodeError(ConnectionError):
    """
    Кастомный класс для исключений, вызываемых при ...
    неверном коде HTTP-ответа
    """


class JsonDetectedResponseError(ConnectionError):
    """
    Кастомный класс для исключений, связанных с наличием в ...
    json ключей, указывающих на ошибки
    """
