from multiprocessing import Queue
import logging
from os import path

from make_api_request import MakeApiRequest

# This method runs a process which will upload tags when the user
# clicks the Upload button


def upload_tags(queue: Queue, main_queue: Queue):
    """
    This function will be used to run the upload process
    """
    logger = logging.getLogger('upload_tags_process')

    api_request = MakeApiRequest('/fabship/product/rfid')

    # Use this variable to determine when to break out of a loop
    should_exit_loop = False

    while should_exit_loop is False:
        # Always check if the queue has elements in it
        if queue.qsize() > 0:
            queue_value: Union[List[str], None] = queue.get()
            print('upload tag value', queue_value)

            # Check if this process needs to quit
            if queue_value is None:
                logger.log(
                    logging.DEBUG, "Exiting the upload tags process")
                should_exit_loop = True

            # The list of tags should have values
            elif len(queue_value) > 0:
                logger.log(
                    logging.DEBUG, f"Received the following tags to upload: {queue_value}")
                # Read the location from the relevant file
                dirname = path.dirname(__file__)
                filename = path.join(dirname, 'location.txt')
                try:
                    logger.log(
                        logging.DEBUG, "Trying to read the location before uploading tags")
                    with open(filename, 'r') as f:
                        location = f.readline()
                except FileNotFoundError as err:
                    logger.log(
                        logging.ERROR, "Could not find the location.txt file to read from")
                    raise err

                # Make the API request
                try:
                    logger.log(logging.DEBUG, "Making a POST request")
                    response = api_request.post(
                        {'location': location, 'epc': queue_value})
                    logger.log(logging.DEBUG,
                               f"Received the following response: {response}")
                    main_queue.put("UPLOAD_SUCCESS")
                except Exception as err:
                    logger.log(logging.ERROR,
                               f"Error raised while uploading tags: {err}")
                    main_queue.put("UPLOAD_FAIL")
