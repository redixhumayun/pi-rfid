"""
This file contains the base message class that is used to pass messages between processes
"""

class Message:
    """This is the base message class which has all data types"""
    def __init__(self, type_value, data=None, message=None):
        self.type = type_value
        self.data = data
        self.message = message