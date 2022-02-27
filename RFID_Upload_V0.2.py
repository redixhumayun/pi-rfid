#!/usr/bin/python3
from os import path
import sys
from multiprocessing import Process, Queue
import argparse
import logging
import logging.handlers
import watchtower
from message import Message

from get_aws_secrets import get_secret, write_secrets_to_env_file
from display.display_tag_id_gui import DisplayTagIdGUI
from tag_reader.tag_reader import TagReader
from tag_reader.tag_reader_enums import TagReaderEnums
from weighing_scale.weighing_scale import WeighingScale
from weighing_scale.weighing_scale_enums import WeighingScaleEnums
from barcode_scanner.barcode_scanner_enums import BarcodeScannerEnums
from display.display_enums import DisplayEnums
from barcode_scanner.barcode_scanner_reader import BarcodeScannerReader
from upload_carton_details import upload_carton_details
from decode_carton_type import decode_epc_tags_into_product_details, get_carton_pack_type
from common_enums import CommonEnums
from exceptions import ApiError, UnknownCartonTypeError, WriteToFileError

def listener_configurer():
    """This method is meant to configure the Watchtower handler which will be used to log the events to AWS CloudWatch"""
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    try:
        with open(filename, 'r', encoding='utf-8') as location_file:
            system_location = location_file.readline()
    except FileNotFoundError:
        print("The location.txt file was not found. Cannot start logging")
    root = logging.getLogger()
    watchtower_handler = watchtower.CloudWatchLogHandler(
        log_group=f"{system_location}-rfid-logs")
    formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)-8s %(message)s')
    watchtower_handler.setFormatter(formatter)
    root.addHandler(watchtower_handler)

def listener_process(queue, configurer):
    """This is the listener process which will watch the multiprocessing Queue for all records
    that are sent by the remaining processes"""
    configurer()
    while True:
        try:
            record = queue.get()
            if record is None:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)
        except Exception:
            import sys
            import traceback
            traceback.print_exc(file=sys.stderr)


def worker_configurer(queue):
    """This is the configurer process which configures the handlers"""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not root.hasHandlers():
        console_handler = logging.StreamHandler()
        queue_handler = logging.handlers.QueueHandler(queue)

        formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)-8s %(message)s')

        console_handler.setFormatter(formatter)

        root.addHandler(queue_handler)
        root.addHandler(console_handler)

def close_queues(queues_to_close):
    """This is a general method to close all queues"""
    for queue in queues_to_close:
        queue.put_nowait(None)
        queue.close()
        queue.join_thread()

def close_processes(processes_to_close):
    """This is a general method to close processes"""
    for process in processes_to_close:
        process.join()


def create_argument_parser():
    """This method will create the argument parser and return it"""
    parser = argparse.ArgumentParser(
        description='Start the RFID process in either dev or prod mode')
    parser.add_argument('--env', action='store', type=str, dest='environment')
    parser.add_argument('--location', action='store', type=str, dest='location')
    return parser

def get_environment_value(parser):
    """This method will retrieve the environment value from the parser"""
    environment = parser.parse_args().environment
    return environment

def get_location_value(parser):
    """This method will retrieve the location value from the parser"""
    location = parser.parse_args().location
    return location

def retrieve_secrets_and_write_to_file(environment):
    """This method will try to retrieve the secrets, if not found it will fetch secrets from AWS
    and write them to a file called .env"""
    env_file = path.join(path.dirname(__file__), '.env')
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            pass
    except FileNotFoundError:
        secrets = get_secret(environment=environment)

    if secrets is None:
        sys.exit('The secrets retrieved are a None value')

    try:
        write_secrets_to_env_file(secrets)
    except WriteToFileError as error:
        sys.exit(f'There was an error while writing the secrets to an env file: {error}')

class GlobalVariablesStruct:
    """This class is meant to hold all global variables"""
    def __init__(self):
        self._list_of_tags_to_upload = None
        self._carton_weight = None
        self._carton_code = None
        self._carton_barcode = None
        self._carton_pack_type = None
        self._shipment_id = None

    def reset_values(self):
        """This method is meant to reset all the values"""
        self._list_of_tags_to_upload = None
        self._carton_weight = None
        self._carton_code = None
        self._carton_barcode = None
        self._carton_pack_type = None
        self._shipment_id = None

    @property
    def list_of_tags_to_upload(self):
        """Getter method for list of tags"""
        return self._list_of_tags_to_upload

    @list_of_tags_to_upload.setter
    def list_of_tags_to_upload(self, list_of_tags):
        self._list_of_tags_to_upload = list_of_tags

    def clear_list_of_tags(self):
        """This method will clear the list of tags"""
        self._list_of_tags_to_upload = []

    @property
    def carton_weight(self):
        """Getter method for carton weight"""
        return self._carton_weight

    @carton_weight.setter
    def carton_weight(self, weight):
        self._carton_weight = weight

    @property
    def carton_code(self):
        """Getter method for carton code"""
        return self._carton_code

    @carton_code.setter
    def carton_code(self, code):
        self._carton_code = code

    @property
    def carton_barcode(self):
        """Getter method for carton barcode"""
        return self._carton_barcode

    @carton_barcode.setter
    def carton_barcode(self, barcode):
        self._carton_barcode = barcode

    @property
    def carton_pack_type(self):
        """Getter method for carton pack type"""
        return self._carton_pack_type

    @carton_pack_type.setter
    def carton_pack_type(self, pack_type):
        self._carton_pack_type = pack_type

    @property
    def shipment_id(self):
        """Getter method for shipment id"""
        return self._shipment_id

    @shipment_id.setter
    def shipment_id(self, id):
        self.shipment_id = id

if __name__ == "__main__":
    global_variables = GlobalVariablesStruct()
    parser = create_argument_parser()
    environment_value = get_environment_value(parser)
    location = get_location_value(parser)

    retrieve_secrets_and_write_to_file(environment=environment_value)


    #   Define a list to hold all the processes
    processes: list = []

    #   Define a list to hold all the sub-process queues
    queues: list = []

    #   Define a main queue
    main_queue: list = []

    # Create a queue and process for logging purposes
    logging_queue = Queue(-1)
    logging_listener_process = Process(target=listener_process, args=(
        logging_queue, listener_configurer))
    queues.append(logging_queue)

    # NOTE: I have no idea why doing a start here versus adding this process to a list and starting
    # later works, but it does. If you add this process to a list and start it later in a for loop
    # it will cause the same line to log thousands of times
    logging_listener_process.start()

    # Start the worker process that will implement all required handlers
    worker_configurer(logging_queue)

    # Create the GUI and associated queue to allow the user to view the scanned tags
    display_tag_id_gui_queue = Queue()
    display_tag_id_gui_process = DisplayTagIdGUI(
        display_tag_id_gui_queue, main_queue)
    processes.append(display_tag_id_gui_process)
    queues.append(display_tag_id_gui_queue)

    #   Create the tag reader process and queue
    read_tags_queue = Queue()
    read_tags_process = TagReader(read_tags_queue, main_queue)
    processes.append(read_tags_process)
    queues.append(read_tags_queue)

    #   Create the weighing process and the queue
    weighing_queue = Queue()
    weighing_process = WeighingScale(weighing_queue, main_queue)
    processes.append(weighing_process)
    queues.append(weighing_queue)

    #   Create the barcode scanner process and queue
    barcode_scanner_queue = Queue()
    barcode_scanner_process = BarcodeScannerReader(barcode_scanner_queue, main_queue)
    processes.append(barcode_scanner_process)
    queues.append(barcode_scanner_queue)
   
    for process in processes:
        process.start()

    while True:
        main_queue_value: Message = main_queue.get(block=True)
        enum_type = main_queue_value.type
        queue_data = main_queue_value.data

        if enum_type == DisplayEnums.SCAN.value:
            global_variables.clear_list_of_tags()
            read_tags_queue.put(
                Message(type_value=TagReaderEnums.START_READING_TAGS.value, data=None, message=None)
            )
            weighing_queue.put(
                Message(type_value=WeighingScaleEnums.START_WEIGHING.value, data=None, message=None)
            )
            
        elif enum_type == DisplayEnums.RESET.value:
            global_variables.clear_list_of_tags()
            read_tags_queue.put(
                Message(type_value=TagReaderEnums.CLEAR_TAG_DATA.value, data=None, message=None)
            )

        elif enum_type == BarcodeScannerEnums.CARTON_BARCODE_SCAN_VALUE.value:
            global_variables.carton_barcode = queue_data['carton_barcode']
            global_variables.carton_code = queue_data['carton_code']
            display_tag_id_gui_queue.put(
                Message(type_value=DisplayEnums.SHOW_SCANNED_BARCODE.value, data={ 'barcode': global_variables.carton_code })
            )

        elif enum_type == TagReaderEnums.DONE_READING_TAGS.value:
            tags_list = queue_data['tags']
            split_string = tags_list.split()
            number_of_tags = split_string[0]
            display_tag_id_gui_queue.put(
                Message(type_value=DisplayEnums.SHOW_NUMBER_OF_TAGS.value, data={ 'tags': number_of_tags }, message=None)
            )

            # Save list of tags to the appropriate variable and make it unique
            list_of_tags = split_string[1:]
            global_variables.list_of_tags_to_upload.extend(list_of_tags)
            global_variables.list_of_tags_to_upload = list(set(global_variables.list_of_tags_to_upload))

        elif enum_type == WeighingScaleEnums.WEIGHT_VALUE_READ.value:
            global_variables.carton_weight = queue_data['weight']
            display_tag_id_gui_queue.put(
                Message(type_value=DisplayEnums.SHOW_WEIGHT.value, data={ 'weight': global_variables.carton_weight })
            )

        elif enum_type == DisplayEnums.GET_CARTON_TYPE.value:
            try:
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=CommonEnums.API_PROCESSING.value
                    )
                )
                product_details = decode_epc_tags_into_product_details(global_variables.list_of_tags_to_upload)
                CARTON_PACK_TYPE = get_carton_pack_type(product_details, global_variables.carton_code)
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=DisplayEnums.SHOW_CARTON_TYPE.value,
                        data={
                            'carton_type': CARTON_PACK_TYPE
                        }
                    )
                )
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=CommonEnums.API_COMPLETED.value
                    )
                )
            except ApiError as err:
                read_tags_queue.put(
                    Message(
                        type_value=TagReaderEnums.CLEAR_TAG_DATA.value
                    )
                )
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=CommonEnums.API_COMPLETED.value
                    )
                )
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=CommonEnums.API_ERROR.value,
                        message=err.message
                    )
                )
            except UnknownCartonTypeError as err:
                read_tags_queue.put(
                    Message(
                        type_value=TagReaderEnums.CLEAR_TAG_DATA.value
                    )
                )
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=CommonEnums.API_COMPLETED.value
                    )
                )
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=DisplayEnums.CUSTOM_ERROR.value,
                        message='There was an error while getting the carton type'
                    )
                )
                
        elif enum_type == DisplayEnums.UPLOAD.value:
            read_tags_queue.put(
                Message(
                    type_value=TagReaderEnums.CLEAR_TAG_DATA.value
                )
            )
            display_tag_id_gui_queue.put(
                Message(
                    type_value=CommonEnums.API_PROCESSING.value
                )
            )

            global_variables.shipment_id = queue_data['shipment_id']
            try:
                upload_carton_details(
                    location,
                    global_variables.list_of_tags_to_upload, 
                    global_variables.carton_weight,
                    global_variables.carton_code,
                    global_variables.carton_barcode, 
                    global_variables.carton_pack_type,
                    global_variables.shipment_id
                )
                display_tag_id_gui_queue.put(
                    Message(
                        CommonEnums.API_COMPLETED.value
                    )
                )
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=DisplayEnums.UPLOAD_SUCCESS.value
                    )
                )

                global_variables.reset_values()
            except ApiError as err:
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=CommonEnums.API_COMPLETED.value
                    )
                )
                error_message = err.message
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=DisplayEnums.CUSTOM_ERROR.value,
                        message=error_message
                    )
                )
                display_tag_id_gui_queue.put(
                    Message(
                        type_value=DisplayEnums.UPLOAD_FAIL.value
                    )
                )

        elif enum_type == CommonEnums.API_PROCESSING.value:
            display_tag_id_gui_queue.put(
                Message(
                    type_value=CommonEnums.API_PROCESSING.value
                )
            )
        
        elif enum_type == CommonEnums.API_COMPLETED.value:
            display_tag_id_gui_queue.put(
                Message(
                    type_value=CommonEnums.API_COMPLETED.value
                )
            )

        elif enum_type == DisplayEnums.QUIT.value:
            for queue in queues:
                queue.put_nowait(None)
            break


    logging_listener_process.join()

    # Close the queues
    close_queues(queues)

    # Close the processes
    close_processes(processes)