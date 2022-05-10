from dataclasses import dataclass


@dataclass
class WrongHttpResponseCodeError(Exception):
    """Кастомный класс для исключений, возникающих в ходе HTTP-запросов..."""

    code: int
    expected_code: int
    url: str
    headers: dict
    params: dict

    def __str__(self):
        """
        Метод для вывода на печать объектов...
        класса WrongHttpResponseCodeError
        """
        return (
            f'Wrong HTTP response code from {self.url}. '
            f'Got: {self.code}. Expected: {self.expected_code}. '
            f'Details. HEADERS: {self.headers}, PARAMETERS: {self.params}'
        )

    def __eq__(self, other):
        """
        Метод для сравнения объектов с объектами...
        класса WrongHttpResponseCodeError
        """
        if not isinstance(other, WrongHttpResponseCodeError):
            return False
        return (
            self.code == other.code
            and self.expected_code == other.expected_code
            and self.url == other.url
            and self.headers == other.headers
            and self.params == other.params
        )