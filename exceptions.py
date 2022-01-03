"""
This file contains custom exceptions
"""


class ApiError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


