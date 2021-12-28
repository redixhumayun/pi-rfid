#!/usr/bin/python

# Inspired by https://www.piddlerintheroot.com/barcode-scanner/
# https://www.raspberrypi.org/forums/viewtopic.php?f=45&t=55100
# from 'brechmos' - thank-you!
import os
import time


class Scanner:
    def __init__(self, file: str):
        self.file = file
        self.CHARMAP_LOWERCASE = {4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e', 9: 'f', 10: 'g', 11: 'h', 12: 'i', 13: 'j', 14: 'k',
                     15: 'l', 16: 'm', 17: 'n', 18: 'o', 19: 'p', 20: 'q', 21: 'r', 22: 's', 23: 't', 24: 'u', 25: 'v',
                     26: 'w', 27: 'x', 28: 'y', 29: 'z', 30: '1', 31: '2', 32: '3', 33: '4', 34: '5', 35: '6', 36: '7',
                     37: '8', 38: '9', 39: '0', 44: ' ', 45: '-', 46: '=', 47: '[', 48: ']', 49: '\\', 51: ';',
                     52: '\'', 53: '~', 54: ',', 55: '.', 56: '/'}
        self.CHARMAP_UPPERCASE = {4: 'A', 5: 'B', 6: 'C', 7: 'D', 8: 'E', 9: 'F', 10: 'G', 11: 'H', 12: 'I', 13: 'J', 14: 'K',
                     15: 'L', 16: 'M', 17: 'N', 18: 'O', 19: 'P', 20: 'Q', 21: 'R', 22: 'S', 23: 'T', 24: 'U', 25: 'V',
                     26: 'W', 27: 'X', 28: 'Y', 29: 'Z', 30: '!', 31: '@', 32: '#', 33: '$', 34: '%', 35: '^', 36: '&',
                     37: '*', 38: '(', 39: ')', 44: ' ', 45: '_', 46: '+', 47: '{', 48: '}', 49: '|', 51: ':', 52: '"',
                     53: '~', 54: '<', 55: '>', 56: '?'}
        self.CR_CHAR = 40
        self.SHIFT_CODE = 2
        self.SHIFT_CODE_LIST = [2, 2]
        self.ERROR_CHARACTER = '?'
        self.codes = []
    
    def is_shift_valid(self, index) -> bool:
        if index < 2:
            return False
        if self.codes[index - 2 : index] == self.SHIFT_CODE_LIST:
            return True
        return False
    
    def reset(self) -> None:
        self.codes = []

    def read_char_codes(self) -> None:
        with open(self.file, 'rb') as fp:
            print('begin')
            os.set_blocking(fp.fileno(), False)
            while True:
                print('read loop', self.codes)
                # content = fp.read(8)
                for char_code in [element for element in fp.read(8) if element > 0]:
                    print('scanner', char_code, '=?', self.CR_CHAR)
                    if char_code == self.CR_CHAR:
                        return
                    self.codes.append(char_code)

    def parse_char_codes(self) -> str:
        string_to_return = ""
        for index, code in enumerate(self.codes):
            if code == self.SHIFT_CODE:
                pass
            elif self.is_shift_valid(index) is True:
                string_to_return += self.CHARMAP_UPPERCASE.get(code, self.ERROR_CHARACTER)
            elif self.is_shift_valid(index) is False:
                string_to_return += self.CHARMAP_LOWERCASE.get(code, self.ERROR_CHARACTER)
        return string_to_return

    def read(self):
        self.read_char_codes()
        print('main scan', self.codes)
        parsed_string:str = self.parse_char_codes()
        print('main scan parse', parsed_string)
        self.reset()
        return parsed_string