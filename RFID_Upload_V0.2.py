#!/usr/bin/python3
from os import path
from multiprocessing import Process, Queue
import time
import serial
import pynmea2
import sys
import requests
import tkinter as tk
from tkinter import ttk, messagebox

from make_api_request import MakeApiRequest

def upload_tags(queue: list, main_queue: list):
  """
  This function will be used to run the upload process
  """
  api_request = MakeApiRequest('/fabship/product/rfid/epc')

  # Use this variable to determine when to break out of a loop
  should_exit_loop = False


  while should_exit_loop is False:
    # Always check if the queue has elements in it.
    # Do this because queue.get() is a blocking operation
    if main_queue.qsize() > 0:
      main_queue_value = main_queue.get()
      if main_queue_value == "QUIT":
        should_exit_loop = True

    # Always check if the queue has elements in it
    if queue.qsize() > 0:
      list_of_tags_to_upload: list = queue.get()

      # The list of tags should have values
      if len(list_of_tags_to_upload) > 0:

        # Read the location from the relevant file
        dirname = path.dirname(__file__)
        filename = path.join(dirname, 'location.txt')
        try:
          with open(filename, 'r') as f:
            location = f.readline()
        except FileNotFoundError as err:
          raise err

        # Make the API request
        try:
          response = api_request.post({ 'location': location, 'epc': list_of_tags_to_upload })
          response.raise_for_status()
          if response.status_code == 200:
            main_queue.put("UPLOAD_SUCCESS")
        except requests.exceptions.HTTPError as err:
          main_queue.put("UPLOAD_FAIL")


class TagReader(Process):
  """
  This class is used to read values from the RFID reader connected via USB

  Attributes
  ----------
  queue: Queue
    A multiprocessing queue that is used by the main process to send instructions to this process
  main_queue: Queue
    A multiprocessing queue that is used by this process to communicate information back to the main process
  """
  def __init__(self, queue: Queue, main_queue: Queue):
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.serial_device = None
    self.should_read_tags = False
    self.send_back_tag_values = False
    self.tag_bytes_list = [] # The bytes read from the serial device for an RFID tag will be stored in this list
    self.tag_hex_list = []  # The hex value of the RFID tag will be stored in this list
    self.string_of_tags = ""

  def convert_tags_to_hex(self):
    """
    This method is called to convert a list of bytes into one complete
    RFID tag

    Parameters
    ----------
    send_back_tag_values: boolean
      A boolean value taht will determine whether the tag values need to be sent back to the main queue
    """
    tag_hex_value = ""
    for index, bytes_value in enumerate(self.tag_bytes_list):
      # The assumption here is that the first 3 bytes and the last byte are just placeholders
      if index > 3 and index < 16:
        tag_hex_value += "{0:02X}".format(bytes_value)

    if tag_hex_value not in self.tag_hex_list:
      self.tag_hex_list.append(tag_hex_value)

    if self.send_back_tag_values is True and len(self.tag_hex_list) > 0:
      self.string_of_tags = str(len(self.tag_hex_list)) + " "
      for tag_value in self.tag_hex_list:
        self.string_of_tags += tag_value + " "
      
      self.main_queue.put("TAGS: " + self.string_of_tags)
      self.string_of_tags = ""

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
      self.serial_device = serial.Serial('/dev/ttyUSB1', 57600, timeout=0.5)
    except serial.serialutil.SerialException as err:
      raise err

    should_exit_loop = False

    while should_exit_loop is False:

      # Check if the queue has any elements in it
      # Do this because queue.get() is a blocking call
      if self.queue.qsize() > 0:
        input_queue_string = self.queue.get()
        if input_queue_string == "SCAN":
          self.send_back_tag_values = True
        if input_queue_string == "QUIT":
          should_exit_loop = True

      read_bytes = self.serial_device.read()
      int_value = int.from_bytes(read_bytes, "big")
      sys.stdout.flush()

      # The starting byte of any tag id is 0x11 (which is 17)
      if int_value == 0x11:
        self.should_read_tags = True
      
      if self.should_read_tags is True:
        self.tag_bytes_list.append(int_value)

        # One RFID tag has a sequence of 18 bytes
        if len(self.tag_bytes_list) == 18:
          self.should_read_tags = False
          self.convert_tags_to_hex()
          self.tag_bytes_list.clear() # Clear the bytes from the RFID tag read in preparation for the next one

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

  def __init__(self, queue: list, main_queue: list):
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

  def scan(self):
    """
    This method is called when the scan button is pressed
    """
    self.main_queue.put("SCAN")
  
  def upload(self):
    """
    This method is called when the upload button is pressed
    """
    self.main_queue.put("UPLOAD")

  def close_window(self):
    """
    This method is called when the close button is pressed
    """
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
      self.main_queue.put("QUIT")
      self.root.destroy()

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
    # try:
    #   self.canvas.delete("text_to_be_shown")
    #   self.root.update()  
    # except Exception as err:
    #   print("Cannot clear canvas probably because there is nothing on the canvas to clear")
    #   print(err)

    try:
      self.canvas.delete("text_to_be_shown")
      self.root.update()
    except Exception as err:
      print("Cannot clear canvas probably because there is nothing on the canvas to clear")
      print(err)

    # Check if the queue has any elements in it
    # Do this because queue.get() is a blocking call
    if self.queue.qsize() > 0:
      input_value = self.queue.get()
      string_to_display = ""
      for value in input_value:
        string_to_display += value + "\n"
      self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
                                    font="Helvetic 20 bold", text=string_to_display, tag="text_to_be_shown")
      self.root.update()
    self.root.after(300, self.run_loop)

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    self.root = tk.Tk()
    self.canvas = tk.Canvas(self.root, bg="white",
                            width=800,
                            height=450)
    self.canvas.pack(side=tk.TOP)
    scan_button = ttk.Button(self.root, text="Scan", command=self.scan)
    upload_button = ttk.Button(self.root, text="Upload", command=self.upload)
    scan_button.pack(side=tk.RIGHT)
    upload_button.pack(side=tk.RIGHT)
    self.root.protocol("WM_DELETE_WINDOW", self.close_window)
    self.root.after(900, self.run_loop)
    tk.mainloop()
    

class SelectLocationGUI(Process):
  """
  This class is used to create a GUI that will be used to display the list of possible locations to the user
  and allow the user to select a location
  """

  def __init__(self, queue: list, main_queue: list):
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.possible_locations = None
    self.buttons = {}

  def command(self, location: str):
    """
    This method is used to listen to a click event where the user
    picks the location

    Parameters
    ----------
    location: str, required
      The location selected by the user
    """
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    with open(filename, 'w+') as f:
      f.write(location)
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
    for location in self.possible_locations:
      key = f"button_{location}"
      self.buttons[key] = ttk.Button(
          self.root, text=location, command=lambda loc=location: self.command(loc))
      self.buttons[key].pack(side=tk.TOP)
    tk.mainloop()


# This function is used to call the GPS device attached via USB
# and fetch the latitude and longitude

def get_latitude_and_longitude(gps_child_queue):
  time_end = time.time() + 10

  # Read from the GPS device for 30 seconds
  serial_device = serial.Serial('/dev/ttyS0', 9600, timeout=1)
  while time.time() < time_end:
    x = serial_device.readline()
    y = x[:-2].decode('utf-8')
    if y.find("RMC") > 0:
      message = pynmea2.parse(str(y))
      latitude = message.latitude
      longitude = message.longitude

  gps_child_queue.put({ 'latitude': latitude, 'longitude': longitude })

  #   Use this for testing
  # while time.time() < time_end:
  #   latitude = 13.02518000
  #   longitude = 77.63192000
  # gps_child_queue.put({'latitude': latitude, 'longitude': longitude})


def get_location(location_object):
  print(location_object)
  try:
    api_request = MakeApiRequest('/service/validate/locations')
    payload = {
        'latitude': location_object['latitude'], 'longitude': location_object['longitude']}
    response = api_request.get(payload)
    return response
  except Exception as err:
    print("Sorry, there was an error while fetching the location. Please try again")
    print(err)


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

  # Start GPS process and allow user to select location only if
  # locatio has not already been set
  if should_check_location is True:
    # Create a boolean to check if the location has been picked by the user
    has_location_been_picked = False

    # Create the GUI and associated queue to fetch lat & long using GPS device
    gps_queue = Queue()
    gps_process = Process(
        target=get_latitude_and_longitude, args=(gps_queue,))

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

    # Clear the process list
    processes.clear()

  # Create the GUI and associated queue to allow the user to view the scanned tags
  display_tag_id_gui_queue = Queue()
  display_tag_id_gui_process = DisplayTagIdGUI(display_tag_id_gui_queue, main_queue)
  processes.append(display_tag_id_gui_process)

  # Create the process associated with reading tags
  read_tags_queue = Queue()
  read_tags_process = TagReader(read_tags_queue, main_queue)
  processes.append(read_tags_process)

  # Create the queue and process associated with uploading tags
  upload_tags_queue = Queue()
  upload_tags_process = Process(target=upload_tags, args=(upload_tags_queue, main_queue,))
  processes.append(upload_tags_process)

  for process in processes:
    process.start()

  should_exit_program = False

  list_of_tags_to_upload = []

  while should_exit_program is False:
    if main_queue.qsize() > 0:
      main_queue_value = main_queue.get()
      if main_queue_value == "SCAN":
        print("SCAN")
        read_tags_queue.put("SCAN")

      elif main_queue_value == "UPLOAD":
        print("UPLOAD")
        upload_tags_queue.put(list_of_tags_to_upload)

      elif main_queue_value == "UPLOAD_SUCCESS":
        display_tag_id_gui_queue.put("UPLOAD SUCCESSFUL")
      
      elif main_queue_value == "UPLOAD_FAIL":
        display_tag_id_gui_queue.put("UPLOAD_FAIL")

      elif main_queue_value == "QUIT":
        read_tags_queue.put("QUIT")
        upload_tags_queue.put("QUIT")
        should_exit_program = True

      elif main_queue_value.find("TAG") != -1 and main_queue_value.find("TAG") == 0:
        split_string = main_queue_value.split()
        list_of_tags = split_string[1:]
        display_tag_id_gui_queue.put(list_of_tags)
        list_of_tags_to_upload.append(list_of_tags)