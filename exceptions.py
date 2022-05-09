class WrongHttpResponseCodeError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return str(self.message)

    def __eq__(self, other):
        if not isinstance(other, WrongHttpResponseCodeError):
            return False
        return self.message == self.message

class WrongTypeError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return str(self.message)

    def __eq__(self, other):
        if not isinstance(other, WrongTypeError):
            return False
        return self.message == self.message

class EmptyDictonaryError(LookupError):
    def __init__(self, message='Empty dictionary in response was found'):
        self.message = message

    def __str__(self):
        return str(self.message)

    def __eq__(self, other):
        if not isinstance(other, EmptyDictonaryError):
            return False
        return self.message == self.message


class UnknownHomeworkStatusError(LookupError):
    def __init__(self, message='Unknown homework status was found'):
        self.message = message

    def __str__(self):
        return str(self.message)

    def __eq__(self, other):
        if not isinstance(other, UnknownHomeworkStatusError):
            return False
        return self.message == self.message

class KeyNotFound(LookupError):
    def __init__(self, message='Key not found'):
        self.message = message

    def __str__(self):
        return str(self.message)

    def __eq__(self, other):
        if not isinstance(other, KeyNotFound):
            return False
        return self.message == self.message