import sys
import logging
from multiprocessing import Process, Queue

from barcode_scanner.barcode_scanner_enums import BarcodeScannerEnums
from barcode_scanner.scanner import Scanner
from make_api_request import MakeApiRequest


class BarcodeScannerReaderTest(Process):
    """
    This class is used to read the data from the
    barcode scanner connected to the client
    """

    def __init__(self, queue: Queue, main_queue: Queue):
        Process.__init__(self)
        self.queue = queue
        self.main_queue = main_queue
        self.logger = logging.getLogger('barcode_scanner_reader')
        try:
            self.scanner = Scanner('/dev/usb-barcode-scanner')
        except PermissionError as err:
            self.logger.log(logging.ERROR, f"There was an error while opening the barcode scanner reader: {err}")

    def run(self):
        should_exit_loop = False
        while should_exit_loop is False:
            if self.queue.qsize() > 0:
                input_queue_value = self.queue.get()
                if input_queue_value is None:
                    self.logger.log(
                        logging.DEBUG, "Exiting the scanning process")
                    should_exit_loop = True

                # if input_queue_value == BarcodeScannerEnums.SEND_VALUE_TO_MAIN_PROCESS.value:
                #     self.main_queue.put({
                #         'type': BarcodeScannerEnums.CARTON_BARCODE_SCAN_VALUE.value,
                #         'data': {
                #             'barcode': self.value
                #         }
                #     })

            #   Assuming self.scanner.read() is a blocking call that will only send
            #   a value back to the main process after reading something
            # value = 'HM0001'
            barcode = self.scanner.read()
            carton_code = self.decode_barcode_into_carton_code(barcode)
            self.send_value_to_main_process(carton_code)

    def send_value_to_main_process(self, barcode):
        self.main_queue.put({
            'type': BarcodeScannerEnums.CARTON_BARCODE_SCAN_VALUE.value,
            'data': {
                'barcode': barcode
            }
        })

    def decode_barcode_into_carton_code(self, barcode):
        api_request = MakeApiRequest(f"/fabship/product/rfid/carton/barcode/{barcode}")
        carton_code = api_request.get()
        return carton_code
