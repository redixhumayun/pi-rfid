import sys
import logging
from multiprocessing import Process, Queue

from barcode_scanner.barcode_scanner_enums import BarcodeScannerEnums
from barcode_scanner.scanner import Scanner
from make_api_request import MakeApiRequest
from exceptions import ApiError
from common_enums import CommonEnums

class BarcodeScannerReader(Process):
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
            message = 'Unable to open barcode scanner reader'
            self.main_queue.put({
                'type': BarcodeScannerEnums.BARCODE_SCANNER_PERMISSION_ERROR.value,
                'message': message
                })

    def run(self):
        should_exit_loop = False
        while should_exit_loop is False:
            if self.queue.qsize() > 0:
                input_queue_value = self.queue.get()
                if input_queue_value is None:
                    self.logger.log(logging.DEBUG, "Exiting the barcode scanning process")
                    should_exit_loop = True

            # self.scanner.read() is a non-blocking call
            barcode = self.scanner.read()
            if barcode:
                try:
                    self.main_queue.put(CommonEnums.API_PROCESSING.value)
                    carton_code = self.decode_barcode_into_carton_code(barcode)
                    self.main_queue.put(CommonEnums.API_COMPLETED.value)
                    self.send_value_to_main_process(carton_code, barcode)
                except ApiError as err:
                    self.main_queue.put(CommonEnums.API_COMPLETED.value)
                    self.send_api_error_to_main_process(err.message)

    def send_value_to_main_process(self, carton_code, barcode):
        self.main_queue.put({
            'type': BarcodeScannerEnums.CARTON_BARCODE_SCAN_VALUE.value,
            'data': {
                'carton_code': carton_code,
                'carton_barcode': barcode
            }
        })

    def decode_barcode_into_carton_code(self, barcode):
        api_request = MakeApiRequest(f"/fabship/product/rfid/carton/barcode/{barcode}")
        self.main_queue.put(CommonEnums.API_PROCESSING.value)
        try:
            carton_code = api_request.get()
            return carton_code
        except ApiError as err:
            raise err

    def send_api_error_to_main_process(self, message):
        """
        This method is called to return the API error message to the main process
        """
        self.main_queue.put({
            'type': CommonEnums.API_ERROR.value,
            'message': message 
            })

