from multiprocessing import Process, Queue
import logging
import time
import serial
import sys

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
    
    print("TAGS: ", self.string_of_tags)
    self.main_queue.put("TAGS: " + self.string_of_tags)
    self.string_of_tags = ""
    self.start_time = time.time()

  def is_tag_valid(self, tag_value) -> bool:
    """
    This method is used to determine the validity of an EPC tag
    """
    binary_tag_value: str = bin(int(tag_value, 16))[2:].zfill(96)  # This line converts from hex -> int -> bin, removes the 0b at the beginning and then zfills to get 96 bits

    binary_header: str = binary_tag_value[0:8]
    binary_company_prefix: str = binary_tag_value[14:34]

    header: int = int(binary_header, 2)
    company_prefix: int = int(binary_company_prefix, 2)

    # All SGTIN values have an 8-bit header corresponding to 48
    if header != 48:
      return False

    # H&M's GS1 company prefix is 731422
    if company_prefix != 731422 and company_prefix != 731430:
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
      self.logger.log(logging.ERROR, f"There was an error while opening ports for the RFID readers: {err}")
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
          print("Pressed the scan button")
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
          print("Pressed the upload button")
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