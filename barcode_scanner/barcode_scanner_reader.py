import sys
from multiprocessing import Process, Queue

from barcode_scanner_enums import BarcodeScannerEnums
from scanner import Scanner


class BarcodeScannerReader(Process):
    """
    This class is used to read the data from the
    barcode scanner connected to the client
    """
    def __init__(self, queue: Queue, main_queue: Queue):
        Process.__init__(self)
        self.queue = queue
        self.main_queue = main_queue
        self.scanner = Scanner('/dev/hidraw0')
        self.value = ''

    def run(self):
        should_exit_loop = False
        while should_exit_loop is False:
            if self.queue.qsize() > 0:
                input_queue_value = self.queue.get()
                if input_queue_value is None:
                    should_exit_loop = True

                if input_queue_value == BarcodeScannerEnums.SEND_VALUE_TO_MAIN_PROCESS:
                    self.main_queue.put({
                        'type': BarcodeScannerEnums.SENDING_WEIGHT_VALUE_TO_MAIN_PROCESS,
                        'data': {
                            'barcode': self.value
                        }
                    })

            self.value = self.scanner.read()
