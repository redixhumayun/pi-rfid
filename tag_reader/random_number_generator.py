from multiprocessing import Process, Queue
import logging
import time
from random import randint, choice
from string import ascii_uppercase

from tag_reader.tag_reader_enums import TagReaderEnums
from carton.carton_type import CartonType


class RandomNumberGenerator(Process):
    def __init__(self, queue: Queue, main_queue: Queue):
        Process.__init__(self)
        self.queue = queue
        self.main_queue = main_queue
        self.random_numbers_list: list = []
        self.return_string: str = ""
        self.logger = logging.getLogger('random_number_generator')

    def run(self):
        while True:
            random_number: float = self.generate_random_epc_tag()
            self.random_numbers_list.append(random_number)
            if self.queue.qsize() > 0:
                queue_value: Union[str, None] = self.queue.get()
                self.logger.log(
                    logging.DEBUG, f"Received {queue_value} from queue")

                if queue_value is None:
                    break

                if queue_value == TagReaderEnums.START_READING_TAGS.value:
                    self.return_string = str(len(self.random_numbers_list)) + " "
                    for random_number in self.random_numbers_list:
                        self.return_string += str(random_number) + " "
                    self.logger.log(
                        logging.DEBUG, f"Returning {self.return_string} to main queue")
                    self.main_queue.put({
                        'type': TagReaderEnums.DONE_READING_TAGS.value,
                        'data': {
                            'tags': self.return_string,
                            'carton_type': CartonType.SOLID.value
                        }
                    })
                    self.return_string = ""
                    self.random_numbers_list = []

            time.sleep(1)

    def generate_random_value(self):
        return ''.join(["{}".format(randint(0, 9)) for num in range(0, 24)])

    def generate_random_epc_tag(self) -> str:
        random_epc_code = '303ACA4782' + self.generate_random_character() + str(randint(10**(13-1), (10**13)-1))
        return random_epc_code

    def generate_random_character(self) -> str:
        return choice(ascii_uppercase)

    def generate_random_number_of_length(self, length: int) -> int:
        return
