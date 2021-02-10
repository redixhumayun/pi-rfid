#!/usr/bin/python3
from os import path
from multiprocessing import Process, Queue
import time
import serial
import sys
import argparse
import requests
import logging, logging.handlers
import watchtower
import tkinter as tk
from random import random
from tkinter import ttk, messagebox
from typing import Union, List

from get_aws_secrets import get_secret, write_secrets_to_env_file
from location_finder import get_latitude_and_longitude, get_location
from make_api_request import MakeApiRequest
from environment_variable import EnvironmentVariable

# This method is used to configure the watchtower handler which will be used to
# log the events to AWS CloudWatch
def listener_configurer():
  root = logging.getLogger()
  watchtower_handler = watchtower.CloudWatchLogHandler()
  formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s')
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
      import sys, traceback
      traceback.print_exc(file=sys.stderr)

# This is the configurer process which configures the handlers
def worker_configurer(queue):
  root = logging.getLogger()
  root.setLevel(logging.DEBUG)
  if not root.hasHandlers():
    console_handler = logging.StreamHandler()
    queue_handler = logging.handlers.QueueHandler(queue)

    formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s')

    console_handler.setFormatter(formatter)

    root.addHandler(queue_handler)
    root.addHandler(console_handler)

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

      # Check if this process needs to quit
      if queue_value is None:
        should_exit_loop = True

      # The list of tags should have values
      elif len(queue_value) > 0:
        logger.log(logging.DEBUG, f"Received the following tags to upload: {queue_value}")
        # Read the location from the relevant file
        dirname = path.dirname(__file__)
        filename = path.join(dirname, 'location.txt')
        try:
          logger.log(logging.DEBUG, "Trying to read the location before uploading tags")
          with open(filename, 'r') as f:
            location = f.readline()
        except FileNotFoundError as err:
          logger.log(logging.ERROR, "Could not find the location.txt file to read from")
          raise err

        # Make the API request
        try:
          logger.log(logging.DEBUG, "Making a POST request")
          response = api_request.post({ 'location': location, 'epc': queue_value })
          logger.log(logging.DEBUG, f"Received the following response: {response}")
          main_queue.put("UPLOAD_SUCCESS")
        except requests.exceptions.HTTPError as err:
          logger.log(logging.ERROR, f"Error raised while uploading tags: {err}")
          main_queue.put("UPLOAD_FAIL")

def random_number_generator(queue: Queue, main_queue: Queue):
  logger = logging.getLogger('random_number_generator')
  return_string: str = "TAGS:"
  while True:
    random_number: float = random()
    return_string += f" {str(random_number)}"
    if queue.qsize() > 0:
      queue_value: Union[str, None] = queue.get()
      logger.log(logging.DEBUG, f"Received {queue_value} from queue")
      
      if queue_value is None:
        break
      
      if queue_value == "SCAN":
        logger.log(logging.DEBUG, f"Returning {return_string} to main queue")
        main_queue.put(return_string)
        return_string = "TAGS:"

    time.sleep(1)
  logger.log(logging.DEBUG, "Exiting the random number generator process")

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
    self.tag_bytes_list = [] # The bytes read from the serial device for an RFID tag will be stored in this list
    self.tag_hex_list = []  # The hex value of the RFID tag will be stored in this list
    self.string_of_tags = ""
    self.start_time = 0
    self.logger = logging.getLogger('tag_reader')

  def send_tags_to_main_process(self):
    """
    This method is called to return the list of tags to the main process
    """
    self.string_of_tags = str(len(self.tag_hex_list)) + " "
    for tag_value in self.tag_hex_list:
      self.string_of_tags += tag_value + " "
    
    self.main_queue.put("TAGS: " + self.string_of_tags)
    self.string_of_tags = ""
    self.start_time = time.time()

  def is_tag_valid(self, tag_value) -> bool:
    """
    This method is used to determine the validity of an EPC tag
    """
    binary_tag_value: str = bin(int(tag_value, 16))[2:].zfill(96)  # This line converts from hex -> int -> bin, removes the 0b at the beginning and then zfills to get 96 bits

    binary_header: str = binary_tag_value[0:8]
    binary_filter_value: str = binary_tag_value[8:11]
    binary_partition: str = binary_tag_value[11:14]
    binary_company_prefix: str = binary_tag_value[14:34]
    binary_item_reference: str = binary_tag_value[34:58]
    binary_serial_value: str = binary_tag_value[58:]

    header: int = int(binary_header, 2)
    filter_value: int = int(binary_filter_value, 2)
    partition: int = int(binary_partition, 2)
    company_prefix: int = int(binary_company_prefix, 2)
    item_reference: int = int(binary_item_reference, 2)
    serial_value: int = int(binary_serial_value, 2)

    # All SGTIN values have an 8-bit header corresponding to 48
    if header != 48:
      return False

    # H&M's GS1 company prefix is 731422
    if company_prefix != 731422:
      return False

    return True

  def convert_tags_to_hex(self, tag_bytes_list):
    """
    This method is called to convert a list of bytes into one complete
    RFID tag
    """

    # Stores the hex value of the RFID tag being read
    tag_hex_value = ""

    for index, bytes_value in enumerate(tag_bytes_list):
      # The assumption here is that the first 3 bytes and the last byte are just placeholders
      if index > 3 and index < 16:
        tag_hex_value += "{0:02X}".format(bytes_value)

    if tag_hex_value not in self.tag_hex_list:
      # Check if this is a valid EPC tag for H&M
      if self.is_tag_valid(tag_hex_value) is True:
        self.tag_hex_list.append(tag_hex_value)
      else:
        self.logger.log(logging.ERROR, f"This tag value {tag_hex_value} is not a valid EPC")

    # Before sending tag values to the main process, check the following:
    # 1. The boolean for this is set to True
    # 2. The tag hex list actually has values
    # 3. The time lapsed has been atleast 2 seconds
    if self.should_send_back_tag_values == True and len(self.tag_hex_list) > 0 and time.time() - self.start_time > 2:
      self.send_tags_to_main_process()

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
      self.logger.log(logging.DEBUG, "Starting the serial ports for RFID reading")
      self.serial_device_1 = serial.Serial('/dev/ttyUSB0', 57600, timeout=0.5)
      self.serial_device_2 = serial.Serial('/dev/ttyUSB1', 57600, timeout=0.5)
    except serial.serialutil.SerialException as err:
      self.logger.log(logging.ERROR, "There was an error while opening ports for the RFID readers: {err}")
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
        if input_queue_string == "SCAN":
          # When the user clicks the scan button, clear the buffer
          # clear the bytes list and also clear previously stored EPC's
          self.logger.log(logging.DEBUG, "Clearing the bytes list for tags in preparation for another scan")
          tag_bytes_list_for_device_1.clear()
          tag_bytes_list_for_device_2.clear()
          self.serial_device_1.reset_input_buffer()
          self.serial_device_2.reset_input_buffer()
          self.tag_hex_list.clear()
          self.should_send_back_tag_values = True
          self.start_time = time.time()
        elif input_queue_string == "UPLOAD":
          self.logger.log(logging.DEBUG, "Clearing the bytes list for tags in preparation for an upload")
          tag_bytes_list_for_device_1.clear()
          tag_bytes_list_for_device_2.clear()
          self.serial_device_1.reset_input_buffer()
          self.serial_device_2.reset_input_buffer()
          self.tag_hex_list.clear()
          self.should_send_back_tag_values = False
          self.start_time = time.time()
        elif input_queue_string is None:
          self.logger.log(logging.DEBUG, "Exiting the tag_reader process")
          should_exit_loop = True

      read_bytes_from_device_1 = self.serial_device_1.read()
      int_value_from_device_1 = int.from_bytes(read_bytes_from_device_1, "big")

      read_bytes_from_device_2 = self.serial_device_2.read()
      int_value_from_device_2 = int.from_bytes(read_bytes_from_device_2, "big")

      sys.stdout.flush()

      # The starting byte of any tag id is 0x11 (which is 17)
      if int_value_from_device_1 == 0x11:
        should_read_tags_from_device_1 = True
      
      if should_read_tags_from_device_1 is True:
        tag_bytes_list_for_device_1.append(int_value_from_device_1)

        # One RFID tag has a sequence of 18 bytes
        if len(tag_bytes_list_for_device_1) == 18:
          should_read_tags_from_device_1 = False
          self.convert_tags_to_hex(tag_bytes_list = tag_bytes_list_for_device_1)
          tag_bytes_list_for_device_1.clear() # Clear the bytes from the RFID tag read in preparation for the next one

      # The starting byte of any tag id is 0x11 (which is 17)
      if int_value_from_device_2 == 0x11:
        should_read_tags_from_device_2 = True

      if should_read_tags_from_device_2 is True:
        tag_bytes_list_for_device_2.append(int_value_from_device_2)
      
        # One RFID tag has a sequence of 18 bytes
        if len(tag_bytes_list_for_device_2) == 18:
          should_read_tags_from_device_2 = False
          self.convert_tags_to_hex(tag_bytes_list = tag_bytes_list_for_device_2)
          tag_bytes_list_for_device_2.clear() # Clear the bytes from the RFID tag read in preparation for the next one
    
    # Once the loop exits, perform clean up and close serial ports
    self.serial_device_1.close()
    self.serial_device_2.close()

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    self.read_tag_bytes()

class DisplayTagIdGUI(Process):
  """
  This class is used to create a GUI that will be used to display the list of tags that
  are being read from the USB device
  """

  def __init__(self, queue: Queue, main_queue: Queue):
    """
    Parameters
    ----------
    queue: list
      The list into which the main process will input data
    main_queue: list
      The list into which this process will transfer data back to the
      main process
    """
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.action_to_perform = None
    self.logger = logging.getLogger('display_tag_id_gui')

  def scan(self):
    """
    This method is called when the scan button is pressed
    """
    self.logger.log(logging.DEBUG, "The user pressed scan")
    self.main_queue.put("SCAN")
  
  def upload(self):
    """
    This method is called when the upload button is pressed
    """
    self.logger.log(logging.DEBUG, "The user pressed upload")
    self.main_queue.put("UPLOAD")

  def close_window(self):
    """
    This method is called when the close button is pressed
    """
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
      self.main_queue.put("QUIT")
      self.logger.log(logging.DEBUG, "The user pressed quit")
      self.root.destroy()

  def clear_canvas(self):
    """
    This method is used to clear the canvas
    """
    try:
      self.canvas.delete("text_to_be_shown")
      self.root.update()
    except Exception as err:
      self.logger.log(logging.ERROR, f"The canvas could not be cleared. {err}")

  def run_loop(self):
    """
    This method is used to run a loop every 900ms and is called
    by TKinter. It listens for user interactions

    Raises
    ------
    Exception
      Raises a base Exception if a button that is neither scan nor upload
      is clicked
    """

    # Check if the queue has any elements in it
    # Do this because queue.get() is a blocking call
    if self.queue.qsize() > 0:
      input_value = self.queue.get()

      # Check if the scan button has been clicked
      if input_value == "SCAN":
        self.logger.log(logging.DEBUG, "Clearing canvas because user pressed scan")
        self.clear_canvas()

      if input_value == "UPLOAD_SUCCESS":
        self.logger.log(logging.DEBUG, "Clearing canvas because the upload was successful")
        self.clear_canvas()
        self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
                                      font="Helvetica 20 bold", text="UPLOAD SUCCESSFUL", tag="text_to_be_shown")
        self.root.update()
        
      elif input_value == "UPLOAD_FAIL":
        self.logger.log(logging.DEBUG, "Clearing canvas because the upload failed")
        self.clear_canvas()
        self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
                                      font="Helvetica 20 bold", text="UPLOAD FAILED", tag="text_to_be_shown")
        self.root.update()
      
      # If the value is none of the above, then it must be the list of tags to display
      else:
        self.clear_canvas()
        self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
                                      font="Helvetica 40 bold", text=input_value, tag="text_to_be_shown")
        self.root.update()
    self.root.after(300, self.run_loop)

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    self.root = tk.Tk()
    self.canvas = tk.Canvas(self.root, bg="white",
                            width=1200,
                            height=800)
    self.canvas.pack(side=tk.TOP)
    scan_button = ttk.Button(self.root, text="Scan", command=self.scan)
    upload_button = ttk.Button(self.root, text="Upload", command=self.upload)
    scan_button.pack(side=tk.RIGHT)
    upload_button.pack(side=tk.LEFT)
    self.root.protocol("WM_DELETE_WINDOW", self.close_window)
    self.root.after(900, self.run_loop)
    tk.mainloop()
    

class SelectLocationGUI(Process):
  """
  This class is used to create a GUI that will be used to display the list of possible locations to the user
  and allow the user to select a location
  """

  def __init__(self, queue: Queue, main_queue: Queue):
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.possible_locations = None
    self.buttons = {}
    self.logger = logging.getLogger('select_location_gui')

  def command(self, location: str):
    """
    This method is used to listen to a click event where the user
    picks the location

    Parameters
    ----------
    location: str, required
      The location selected by the user
    """
    self.logger.log(logging.DEBUG, f"The user has picked the location: {location}")
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    with open(filename, 'w+') as f:
      f.write(location)
      self.logger.log(logging.DEBUG, f"Done writing the location to location.txt")
    self.root.destroy()
    self.main_queue.put("LOCATION_PICKED")

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    while self.possible_locations is None:
      self.possible_locations = self.queue.get()
    self.root = tk.Tk()
    self.canvas = tk.Canvas(self.root, bg="white",
                            width=800,
                            height=450)
    self.canvas.pack(side=tk.TOP)
    for location in self.possible_locations:
      key = f"button_{location}"
      self.buttons[key] = ttk.Button(
          self.root, text=location, command=lambda loc=location: self.command(loc))
      self.buttons[key].pack(side=tk.TOP)
    tk.mainloop()


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
  parser = argparse.ArgumentParser(description='Start the RFID process in either dev or prod mode')
  parser.add_argument('--env', action='store', type=str, dest='environment')

  # Parse the environment from command line
  environment = parser.parse_args().environment

  # Get the secrets from AWS and write them to a file
  secrets = get_secret()
  write_secrets_to_env_file(secrets=secrets)

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
    should_check_location = True

  # Define a list to hold all the process references
  processes: list = []

  # Create the main queue that will be used for parent child communication
  main_queue = Queue()

  # Create a queue and process for logging purposes
  logging_queue = Queue(-1)
  logging_listener = Process(target=listener_process, args=(logging_queue, listener_configurer))
  # NOTE: I have no idea why doing a start here versus adding this process to a list and starting
  # later works, but it does. If you add this process to a list and start it later in a for loop
  # it will cause the same line to log thousands of times
  # processes.append(logging_listener)
  logging_listener.start()

  # Start the worker process that will implement all required handlers
  worker_configurer(logging_queue)

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
    select_location_gui_process = SelectLocationGUI(select_location_gui_queue, main_queue)

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

    # Allow the processes to stop
    for process in processes:
      process.join()

    # Clear the process list
    processes.clear()

  # Create the GUI and associated queue to allow the user to view the scanned tags
  display_tag_id_gui_queue = Queue()
  display_tag_id_gui_process = DisplayTagIdGUI(display_tag_id_gui_queue, main_queue)
  processes.append(display_tag_id_gui_process)

  # Create the queue and process associated with uploading tags
  upload_tags_queue = Queue()
  upload_tags_process = Process(target=upload_tags, args=(upload_tags_queue, main_queue))
  processes.append(upload_tags_process)

  # Decide based on the environment variable passed in which process to launch
  # Either the tag reader process or the random number generator process
  if environment == EnvironmentVariable.PRODUCTION.value:
    read_tags_queue = Queue()
    read_tags_process = TagReader(read_tags_queue, main_queue)
    processes.append(read_tags_process)
  elif environment == EnvironmentVariable.DEVELOPMENT.value:
    read_tags_queue = Queue()
    read_tags_process = Process(target=random_number_generator, args=(read_tags_queue, main_queue))
    processes.append(read_tags_process)
  else:
    raise Exception('Unknown input for --env argument')

  for process in processes:
    process.start()

  list_of_tags_to_upload = []

  while True:
    main_queue_value = main_queue.get(block=True)
    if main_queue_value == "SCAN":
      # Everytime the user hits scan, start a fresh read
      list_of_tags_to_upload.clear()
      read_tags_queue.put("SCAN")

    elif main_queue_value == "UPLOAD":
      read_tags_queue.put("UPLOAD")
      upload_tags_queue.put(list_of_tags_to_upload)

    elif main_queue_value == "UPLOAD_SUCCESS":
      display_tag_id_gui_queue.put("UPLOAD SUCCESSFUL")
    
    elif main_queue_value == "UPLOAD_FAIL":
      display_tag_id_gui_queue.put("UPLOAD_FAIL")

    elif main_queue_value == "QUIT":
      # Pass in a sentinel value for all queues here
      read_tags_queue.put_nowait(None)
      upload_tags_queue.put_nowait(None)
      logging_queue.put_nowait(None)
      break
    
    elif main_queue_value.find("TAGS") != -1:
      split_string = main_queue_value.split()
      number_of_tags = split_string[1]
      list_of_tags = split_string[2:]
      display_tag_id_gui_queue.put(number_of_tags)
      list_of_tags_to_upload.extend(list_of_tags)
      # Make the list unique
      list_of_tags_to_upload = list(set(list_of_tags_to_upload))
  
  for process in processes:
    logging_listener.join()
    process.join()
