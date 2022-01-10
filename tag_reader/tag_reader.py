from multiprocessing import Process, Queue
import logging
import time
import serial
import sys
from make_api_request import MakeApiRequest
from carton.decide_carton_type import decide_carton_type, get_carton_perforation
from tag_reader.Entities.rfid_tag import RFIDTagEntity
from tag_reader.tag_reader_enums import TagReaderEnums
from exceptions import ApiError
from common_enums import CommonEnums


class TagReader(Process):
    """
    This class is used to read values from the RFID reader connected via USB

    Attributes
    ----------
    queue: Queue
      A multiprocessing queue that is used by the main process to send instructions to this process
    main_queue: Queue
      A multiprocessing queue that is used by this process to communicate information back to the main process
    serial_device: Object
      The serial device port that will be read from will be stored in this variable
    should_read_tags: Boolean
      This variable is used to determine when this process should start reading tags
    should_send_back_tag_values: Boolean
      This variable is used to determine when this process will send tags read back to the main process
    tag_bytes_list: List
      This will be used to store all the bytes belonging to one RFID tag
    tag_hex_list: List
      This will be used to store the hex value of a specific RFID tag
    string_of_tags: String
      This will store all the tag values read during a given session
    """

    def __init__(self, queue: Queue, main_queue: Queue):
        Process.__init__(self)
        self.queue = queue
        self.main_queue = main_queue
        self.serial_device_1 = None
        self.serial_device_2 = None
        self.should_send_back_tag_values = False
        self.tag_hex_list = []  # The hex value of the RFID tag will be stored in this list
        self.string_of_tags = ""
        self.start_time = 0
        self.logger = logging.getLogger('tag_reader')
        self.carton_barcode = None
        self.carton_type = None

    def send_tag_details_to_main_process(self, carton_type):
        """
        This method is called to return the list of tags to the main process
        """
        if carton_type is None:
            return
        
        self.string_of_tags = str(len(self.tag_hex_list)) + " "
        for tag_value in self.tag_hex_list:
            self.string_of_tags += tag_value + " "

        self.main_queue.put({
            'type': TagReaderEnums.DONE_READING_TAGS.value,
            'data': {
                'carton_type': carton_type,
                'tags': self.string_of_tags
            }
        })

        self.string_of_tags = ""
        self.start_time = time.time()
    
    def send_api_error_to_main_process(self, message):
        """
        This method is called to return the API error message to the main process
        """
        self.main_queue.put({
            'type': CommonEnums.API_ERROR.value,
            'message': message
            })

    def decode_epc_tags_into_product_details(self):
        """
        This method is called to convert the EPC into product details via API request
        """
        api_request = MakeApiRequest('/fabship/product/rfid')
        decoded_product_details = None
        self.main_queue.put(CommonEnums.API_PROCESSING.value)
        try:
            decoded_product_details = api_request.get_request_with_body(
                {'epc': self.tag_hex_list})
        except ApiError as err:
            self.queue.put_nowait(TagReaderEnums.CLEAR_TAG_DATA.value)
            self.send_api_error_to_main_process(err.message)
        self.main_queue.put(CommonEnums.API_COMPLETED.value)

        carton_perforation = get_carton_perforation(self.carton_barcode)
        carton_type = None
        try:
            carton_type = decide_carton_type(
                decoded_product_details, carton_perforation)
        except Exception as e:
            self.logger.log(logging.ERROR, f"There was an error while deciding the carton type")
        return carton_type

    def read_tag_data(self, tag_bytes_list):
        """This method is called to convert EPC bytes to hex values and add them to the list if valid"""
        rfid_tag_entity = RFIDTagEntity()
        tag_hex_value = rfid_tag_entity.convert_tag_from_bytes_to_hex(tag_bytes_list=tag_bytes_list)

        if tag_hex_value in self.tag_hex_list:
            #   Do nothing if the tag is already listed
            return
        
        if rfid_tag_entity.is_tag_valid(tag_hex_value=tag_hex_value) is True:
            self.tag_hex_list.append(tag_hex_value)
        else:
            self.logger.log(logging.ERROR, f"This tag value {tag_hex_value} is not a valid EPC")

    def read_tag_bytes(self):
        """
        This method is called to start reading the byte strings from the serial
        device connected via USB

        Raises
        ------
        serial.serialutil.SerialException
          If the USB device is not connected properly and cannot be read from
        """
        try:
            self.logger.log(
                logging.DEBUG, "Starting the serial ports for RFID reading")
            self.serial_device_1 = serial.Serial(
                '/dev/ttyUSB0', 57600, timeout=0.5)
            self.serial_device_2 = serial.Serial(
                '/dev/ttyUSB1', 57600, timeout=0.5)
        except serial.serialutil.SerialException as err:
            self.logger.log(
                logging.ERROR, f"There was an error while opening ports for the RFID readers: {err}")
            raise err

        should_exit_loop = False

        should_read_tags_from_device_1 = False
        should_read_tags_from_device_2 = False

        tag_bytes_list_for_device_1 = []
        tag_bytes_list_for_device_2 = []

        while should_exit_loop is False:
            # Check if the queue has any elements in it
            # Do this because queue.get() is a blocking call
            if self.queue.qsize() > 0:
                input_queue_string = self.queue.get()
                if input_queue_string == TagReaderEnums.START_READING_TAGS.value:
                    # When the user clicks the scan button, clear the buffer
                    # clear the bytes list and also clear previously stored EPC's
                    self.logger.log(
                        logging.DEBUG, "Clearing the bytes list for tags in preparation for another scan")
                    tag_bytes_list_for_device_1.clear()
                    tag_bytes_list_for_device_2.clear()
                    self.serial_device_1.reset_input_buffer()
                    self.serial_device_2.reset_input_buffer()
                    self.tag_hex_list.clear()
                    self.should_send_back_tag_values = True
                    self.start_time = time.time()
                elif input_queue_string == TagReaderEnums.CLEAR_TAG_DATA.value:
                    self.logger.log(
                        logging.DEBUG, "Clearing the bytes list for tags")
                    tag_bytes_list_for_device_1.clear()
                    tag_bytes_list_for_device_2.clear()
                    self.serial_device_1.reset_input_buffer()
                    self.serial_device_2.reset_input_buffer()
                    self.tag_hex_list.clear()
                    self.should_send_back_tag_values = False
                    self.start_time = time.time()
                    self.carton_barcode = None
                    self.carton_type = None
                elif isinstance(input_queue_string, dict):
                    if input_queue_string['type'] == TagReaderEnums.RECEIVED_CARTON_BARCODE_VALUE.value:
                        self.logger.log(
                            logging.DEBUG, "Received the carton barcode value")
                        self.carton_barcode = input_queue_string['data']['carton_code']
                elif input_queue_string is None:
                    self.logger.log(
                        logging.DEBUG, "Exiting the tag_reader process")
                    should_exit_loop = True

            read_bytes_from_device_1 = self.serial_device_1.read()
            int_value_from_device_1 = int.from_bytes(
                read_bytes_from_device_1, "big")

            read_bytes_from_device_2 = self.serial_device_2.read()
            int_value_from_device_2 = int.from_bytes(
                read_bytes_from_device_2, "big")

            sys.stdout.flush()

            # The starting byte of any tag id is 0x11 (which is 17)
            if int_value_from_device_1 == 0x11:
                should_read_tags_from_device_1 = True

            if should_read_tags_from_device_1 is True:
                tag_bytes_list_for_device_1.append(int_value_from_device_1)

                # One RFID tag has a sequence of 18 bytes
                if len(tag_bytes_list_for_device_1) == 18:
                    should_read_tags_from_device_1 = False
                    self.read_tag_data(
                        tag_bytes_list=tag_bytes_list_for_device_1)
                    # Clear the bytes from the RFID tag read in preparation for the next one
                    tag_bytes_list_for_device_1.clear()

            # The starting byte of any tag id is 0x11 (which is 17)
            if int_value_from_device_2 == 0x11:
                should_read_tags_from_device_2 = True

            if should_read_tags_from_device_2 is True:
                tag_bytes_list_for_device_2.append(int_value_from_device_2)

                # One RFID tag has a sequence of 18 bytes
                if len(tag_bytes_list_for_device_2) == 18:
                    should_read_tags_from_device_2 = False
                    self.read_tag_data(
                        tag_bytes_list=tag_bytes_list_for_device_2)
                    # Clear the bytes from the RFID tag read in preparation for the next one
                    tag_bytes_list_for_device_2.clear()

            #   Before sending tag values to the main process, check the following:
            #   1. The boolean for this is set to True
            #   2. The tag hex list actually has values
            #   3. The time lapsed has been at least 2 seconds
            if self.should_send_back_tag_values is True and len(self.tag_hex_list) > 0 and time.time() - self.start_time > 2:
                if self.carton_type is None:
                    self.carton_type = self.decode_epc_tags_into_product_details()
                self.send_tag_details_to_main_process(carton_type=self.carton_type)

        # Once the loop exits, perform clean up and close serial ports
        self.serial_device_1.flush()
        self.serial_device_1.reset_input_buffer()
        self.serial_device_1.close()

        self.serial_device_2.flush()
        self.serial_device_2.reset_input_buffer()
        self.serial_device_2.close()

    def run(self):
        """
        This method is required to be implemented by any class
        that sub-classes multiprocessing.Process
        """
        self.read_tag_bytes()
