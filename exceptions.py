from dataclasses import dataclass


@dataclass
class NetworkError(Exception):
    """Кастомный класс для исключений, связанных с ошибками сети..."""

    url: str
    headers: dict
    params: dict

    def __str__(self):
        """Метод для вывода на печать объектов класса NetworkError..."""
        return (
            f'A network error has occured. Details: URL: {self.url}. '
            f'HEADERS: {self.headers}, PARAMETERS: {self.params}'
        )

    def __eq__(self, other):
        """Метод для сравнения объектов с объектами класса NetworkError..."""
        if not isinstance(other, NetworkError):
            return False
        return (
            self.url == other.url
            and self.headers == other.headers
            and self.params == other.params
        )


@dataclass
class HttpResponseError(NetworkError):
    """Кастомный класс для исключений, возникающих в ходе HTTP-запросов..."""

    code: int
    expected_code: int

    def __str__(self):
        """
        Метод для вывода на печать объектов...
        класса HttpResponseError
        """
        return (
            f'Wrong HTTP response code from {self.url}. '
            f'Got: {self.code}. Expected: {self.expected_code}. '
            f'Details. HEADERS: {self.headers}, PARAMETERS: {self.params}'
        )

    def __eq__(self, other):
        """
        Метод для сравнения объектов с объектами...
        класса HttpResponseError
        """
        if not isinstance(other, HttpResponseError):
            return False
        return (
            self.code == other.code
            and self.expected_code == other.expected_code
            and self.url == other.url
            and self.headers == other.headers
            and self.params == other.params
        )
