"""
This file contains custom exceptions
"""


class ApiError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnknownCartonTypeError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class WeighmentError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class BarcodeError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class RFIDError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
