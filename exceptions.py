"""
This file contains custom exceptions
"""


class ApiError(Exception):
    """This is a custom error for API calls that fail"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class UnknownCartonTypeError(Exception):
    """This is a custom error for an unknown carton type"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class WriteToFileError(Exception):
    """This is a custom error when writing to a file fails"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
