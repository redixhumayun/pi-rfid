from multiprocessing import Process, Queue
import serial
import logging

from weighing_scale_enums import WeighingScaleEnums

class WeighingScale(Process):
  def __init__(self, queue: Queue, main_queue: Queue):
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.weight = 0
    self.logger = logging.getLogger('weighing_scale')
    
  def read_weight(self):
    try:
      self.serial_device_1 = serial.Serial('/dev/ttyUSB2', 9600, timeout=0.5)
    except serial.serialutil.SerialException as err:
      self.logger.log(logging.ERROR, f"There was an error while opening the port to read from the weighing scale: {err}")
      raise err
    should_exit_loop = False
    while should_exit_loop is False:
      if self.queue.qsize() > 0:
        input_queue_string = self.queue.get()
        if input_queue_string == WeighingScaleEnums.START_WEIGHING:
          is_weight_read = False
          print("Reading weight")
          while is_weight_read is False:
            weight_in_bytes = self.serial_device_1.readline()
            weight_as_string = weight_in_bytes.decode('ascii')
            try:
              self.weight = float(weight_as_string)
            except ValueError as err:
              # Not reading this data because scale is calibrating
              pass
            
            if self.weight > 0:
              is_weight_read = True
              print('Weight: ', self.weight)

          print("Done reading the weight")
        elif input_queue_string is None:
          self.logger.log(logging.DEBUG, "Exiting the weighing process")
          should_exit_loop = True

    self.serial_device_1.flush()
    self.serial_device_1.reset_input_buffer()
    self.serial_device_1.close()

  def run(self):
    self.read_weight()