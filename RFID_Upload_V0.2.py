#!/usr/bin/python3
from os import path
import sys
from multiprocessing import Process, Queue
import argparse
import logging
import logging.handlers
import watchtower

from get_aws_secrets import get_secret, write_secrets_to_env_file
from location_finder import get_latitude_and_longitude, get_location
from environment_variable import EnvironmentVariable
from select_location_gui import SelectLocationGUI
from display.display_tag_id_gui import DisplayTagIdGUI
from tag_reader.tag_reader import TagReader
from tag_reader.tag_reader_enums import TagReaderEnums
from tag_reader.random_number_generator import RandomNumberGenerator
from weighing_scale.weighing_scale import WeighingScale
from weighing_scale.weighing_scale_enums import WeighingScaleEnums
from weighing_scale.weighing_scale_test import WeighingScaleTest
from barcode_scanner.barcode_scanner_enums import BarcodeScannerEnums
from display.display_enums import DisplayEnums
from barcode_scanner.barcode_scanner_reader import BarcodeScannerReader
from barcode_scanner.barcode_scanner_reader_test import BarcodeScannerReaderTest
from upload_carton_details import upload_carton_details
from decode_carton_type import decode_epc_tags_into_product_details, get_carton_pack_type
from common_enums import CommonEnums
from exceptions import ApiError, UnknownCartonTypeError

# This method is used to configure the watchtower handler which will be used to
# log the events to AWS CloudWatch


def listener_configurer():
    try:
        with open(filename, 'r') as f:
            system_location = f.readline()
    except FileNotFoundError:
        print("The location.txt file was not found. Cannot start logging")
    root = logging.getLogger()
    watchtower_handler = watchtower.CloudWatchLogHandler(
        log_group=f"{system_location}-rfid-logs")
    formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)-8s %(message)s')
    watchtower_handler.setFormatter(formatter)
    root.addHandler(watchtower_handler)

# This is the listener process which will watch the multiprocessing Queue for all
# records that are sent by the remaining processes


def listener_process(queue, configurer):
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

# This is the configurer process which configures the handlers

def worker_configurer(queue):
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
    for queue in queues_to_close:
        queue.put_nowait(None)
        queue.close()
        queue.join_thread()

def close_processes(processes_to_close):
    for process in processes_to_close:
        process.join()
        


if __name__ == "__main__":
    """
    This program is set up to use multi-processing. This is the main process which will spawn
    all of the child processes.
    Communication between processes happens using the multi-processing queue.
    Each process has its own queue, named accordingly. There is also a main process queue
    Each process is passed its own queue and the main queue as parameters.
    Each process queue is used by the main queue to communicate to the child process.
    The main queue is used by the child process to communicate to the main queue.
    """

    # Create the argument parser
    parser = argparse.ArgumentParser(
        description='Start the RFID process in either dev or prod mode')
    parser.add_argument('--env', action='store', type=str, dest='environment')

    # Parse the environment from command line
    environment = parser.parse_args().environment

    # Get the secrets from AWS and write them to a file
    secrets = None
    while secrets is None:
        try:
            print('Trying to get secrets')
            secrets = get_secret(environment)
            print(secrets)
        except Exception as e:
            raise e
    
    try:
        write_secrets_to_env_file(secrets=secrets)
    except Exception as e:
        print(e)
        sys.exit(1)

    # This variable will determine whether the location should be checked or not
    should_check_location = False

    # First, check if there is a location file which has been written to
    # If there is no file with location saved, fire up GPS device and fetch latitude & longitude
    # Then allow user to select the correct location
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    try:
        with open(filename, 'r') as f:
            location = f.readline()
    except FileNotFoundError:
        print("The location.txt file was not found")
        should_check_location = True

    # Define a list to hold all the process references
    processes: list = []

    # Define a list to hold all the queues for the sub-processes
    queues: list = []

    # Create the main queue that will be used for parent child communication
    main_queue = Queue()

    # Start GPS process and allow user to select location only if
    # location has not already been set
    if should_check_location is True:
        # Create a boolean to check if the location has been picked by the user
        has_location_been_picked = False

        # Create the GUI and associated queue to fetch lat & long using GPS device
        gps_queue = Queue()
        gps_process = Process(
            target=get_latitude_and_longitude, args=(gps_queue, environment))

        # Create the GUI and associated queue to allow the user to select the location
        select_location_gui_queue = Queue()
        select_location_gui_process = SelectLocationGUI(
            select_location_gui_queue, main_queue)

        queues.append(gps_queue)

        processes.append(gps_process)
        processes.append(select_location_gui_process)

        # Start the processes
        for process in processes:
            process.start()

        # Pass data between the various processes
        location_data = gps_queue.get()
        possible_locations = get_location(location_data)
        select_location_gui_queue.put(possible_locations)

        # Keep looping until a location is picked
        while has_location_been_picked is False:
            main_queue_value = main_queue.get()
            if main_queue_value == "LOCATION_PICKED":
                has_location_been_picked = True

        # Close the queues and clear the list
        close_queues(queues)
        queues.clear()                

        # Stop processes and clear the list
        close_processes(processes)
        processes.clear()

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

    # Decide based on the environment variable passed in which process to launch
    # Either the tag reader process or the random number generator process
    if environment == EnvironmentVariable.PRODUCTION.value:
        read_tags_queue = Queue()
        read_tags_process = TagReader(read_tags_queue, main_queue)
        processes.append(read_tags_process)
        queues.append(read_tags_queue)

        weighing_queue = Queue()
        weighing_process = WeighingScale(weighing_queue, main_queue)
        processes.append(weighing_process)
        queues.append(weighing_queue)

        barcode_scanner_queue = Queue()
        barcode_scanner_process = BarcodeScannerReader(barcode_scanner_queue, main_queue)
        processes.append(barcode_scanner_process)
        queues.append(barcode_scanner_queue)       
    elif environment == EnvironmentVariable.DEVELOPMENT.value:
        read_tags_queue = Queue()
        read_tags_process = RandomNumberGenerator(read_tags_queue, main_queue)
        processes.append(read_tags_process)
        queues.append(read_tags_queue)

        weighing_queue = Queue()
        weighing_process = WeighingScaleTest(weighing_queue, main_queue)
        processes.append(weighing_process)
        queues.append(weighing_queue)

        barcode_scanner_queue = Queue()
        barcode_scanner_process = BarcodeScannerReaderTest(barcode_scanner_queue, main_queue)
        processes.append(barcode_scanner_process)
        queues.append(barcode_scanner_queue)
    else:
        raise Exception('Unknown input for --env argument')

    for process in processes:
        process.start()

    list_of_tags_to_upload = []
    carton_weight = 0
    carton_code = ''
    carton_barcode = ''
    carton_pack_type = None
    shipment_id = ''

    while True:
        main_queue_value = main_queue.get(block=True)
        if main_queue_value == DisplayEnums.SCAN.value:
            # Everytime the user hits scan, start a fresh read
            list_of_tags_to_upload.clear()
            read_tags_queue.put(TagReaderEnums.START_READING_TAGS.value)
            weighing_queue.put(WeighingScaleEnums.START_WEIGHING.value)
        
        elif main_queue_value == DisplayEnums.RESET.value:
            list_of_tags_to_upload.clear()
            read_tags_queue.put(TagReaderEnums.CLEAR_TAG_DATA.value)
        
        elif main_queue_value == CommonEnums.API_PROCESSING.value:
            display_tag_id_gui_queue.put(CommonEnums.API_PROCESSING.value)
        
        elif main_queue_value == CommonEnums.API_COMPLETED.value:
            display_tag_id_gui_queue.put(CommonEnums.API_COMPLETED.value)

        elif main_queue_value == DisplayEnums.QUIT.value:
            for queue in queues:
                queue.put_nowait(None)
            break

        elif isinstance(main_queue_value, dict):        
            if main_queue_value['type'] == TagReaderEnums.DONE_READING_TAGS.value:
                data = main_queue_value['data']
                tags_list = data['tags']
                split_string = tags_list.split()
                number_of_tags = split_string[0]
                display_tag_id_gui_queue.put({
                    'type': DisplayEnums.SHOW_NUMBER_OF_TAGS.value,
                    'data': {
                        'tags': number_of_tags
                    }
                })

                # Save list of tags to the appropriate variable and make it unique
                list_of_tags = split_string[1:]
                list_of_tags_to_upload.extend(list_of_tags)
                list_of_tags_to_upload = list(set(list_of_tags_to_upload))
                
            if main_queue_value['type'] == WeighingScaleEnums.WEIGHT_VALUE_READ.value:
                carton_weight = main_queue_value['data']['weight']
                display_tag_id_gui_queue.put({
                    'type': DisplayEnums.SHOW_WEIGHT.value,
                    'data': {
                        'weight': carton_weight
                    }
                })

            if main_queue_value['type'] == BarcodeScannerEnums.CARTON_BARCODE_SCAN_VALUE.value:
                carton_barcode = main_queue_value['data']['carton_barcode']
                carton_code = main_queue_value['data']['carton_code']
                display_tag_id_gui_queue.put({
                    'type': DisplayEnums.SHOW_SCANNED_BARCODE.value,
                    'data': {
                        'barcode': carton_code
                    }
                })
                read_tags_queue.put({
                    'type': TagReaderEnums.RECEIVED_CARTON_BARCODE_VALUE.value,
                    'data': {
                        'carton_code': carton_code
                    }
                })
            
            if main_queue_value['type'] == CommonEnums.API_ERROR.value:
                error_message = main_queue_value['message']
                display_tag_id_gui_queue.put({
                    'type': CommonEnums.API_ERROR.value,
                    'message': error_message
                })
            
            if main_queue_value['type'] == BarcodeScannerEnums.BARCODE_SCANNER_PERMISSION_ERROR.value:
                error_message = main_queue_value['message']
                display_tag_id_gui_queue.put({
                    'type': DisplayEnums.CUSTOM_ERROR.value,
                    'message': error_message
                })
            
            if main_queue_value['type'] == DisplayEnums.GET_CARTON_TYPE.value:
                try:
                    display_tag_id_gui_queue.put(CommonEnums.API_PROCESSING.value)
                    product_details = decode_epc_tags_into_product_details(list_of_tags_to_upload)
                    carton_pack_type = get_carton_pack_type(product_details, carton_code)
                    display_tag_id_gui_queue.put({
                        'type': DisplayEnums.SHOW_CARTON_TYPE.value,
                        'data': {
                            'carton_type': carton_pack_type
                        }
                    })
                    display_tag_id_gui_queue.put(CommonEnums.API_COMPLETED.value)
                except ApiError as err:
                    read_tags_queue.put(TagReaderEnums.CLEAR_TAG_DATA.value)
                    display_tag_id_gui_queue.put(CommonEnums.API_COMPLETED.value)
                    display_tag_id_gui_queue.put({
                        'type': CommonEnums.API_ERROR.value,
                        'message': err.message
                    })
                except UnknownCartonTypeError as err:
                    read_tags_queue.put(TagReaderEnums.CLEAR_TAG_DATA.value)
                    display_tag_id_gui_queue.put(CommonEnums.API_COMPLETED.value)
                    display_tag_id_gui_queue.put({
                        'type': DisplayEnums.CUSTOM_ERROR.value,
                        'message': 'There was an error while getting the carton type'
                    })

            if main_queue_value['type'] == DisplayEnums.UPLOAD.value:
                shipment_id = main_queue_value['data']['shipment_id']
                read_tags_queue.put(TagReaderEnums.CLEAR_TAG_DATA.value)
                display_tag_id_gui_queue.put(CommonEnums.API_PROCESSING.value)
                try:
                    carton_details_api_upload_call_result = upload_carton_details(
                        list_of_tags_to_upload, 
                        carton_weight,
                        carton_code,
                        carton_barcode, 
                        carton_pack_type,
                        shipment_id
                    )
                    display_tag_id_gui_queue.put(CommonEnums.API_COMPLETED.value)
                    display_tag_id_gui_queue.put(DisplayEnums.UPLOAD_SUCCESS.value)
                    list_of_tags_to_upload = []
                    carton_weight = 0
                    carton_code = ''
                    carton_barcode = ''
                    carton_pack_type = None
                    shipment_id = ''
                except FileNotFoundError as err:
                    display_tag_id_gui_queue.put(CommonEnums.API_COMPLETED.value)
                    error_message = 'There was a problem while reading the location'
                    display_tag_id_gui_queue.put({
                        'type': DisplayEnums.CUSTOM_ERROR.value,
                        'message': error_message
                    })
                except ApiError as err:
                    display_tag_id_gui_queue.put(CommonEnums.API_COMPLETED.value)
                    error_message = err.message
                    display_tag_id_gui_queue.put({
                        'type': DisplayEnums.CUSTOM_ERROR.value,
                        'message': error_message
                    })
                    display_tag_id_gui_queue.put(DisplayEnums.UPLOAD_FAIL.value)

    logging_listener_process.join()

    # Close the queues
    close_queues(queues)

    # Close the processes
    close_processes(processes)