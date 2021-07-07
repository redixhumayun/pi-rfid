from multiprocessing import Process, Queue
import logging
import time
from random import randint

class RandomNumberGenerator(Process):
  def __init__(self, queue: Queue, main_queue: Queue):
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.random_numbers_list: list = []
    self.return_string: str = ""
    self.logger = logging.getLogger('random_number_generator')
  
  def run(self):
    while True:
      random_number: float = self.generate_random_value()
      self.random_numbers_list.append(random_number)
      if self.queue.qsize() > 0:
        queue_value: Union[str, None] = self.queue.get()
        self.logger.log(logging.DEBUG, f"Received {queue_value} from queue")
        
        if queue_value is None:
          break
        
        if queue_value == "SCAN":
          print("Received SCAN")
          self.return_string = f"TAGS: {str(len(self.random_numbers_list))} "
          print("self.random_numbers_list", self.random_numbers_list)
          for random_number in self.random_numbers_list:
            self.return_string += str(random_number) + " "
          self.logger.log(logging.DEBUG, f"Returning {self.return_string} to main queue")
          self.main_queue.put(self.return_string)
          self.return_string = ""

      time.sleep(1)

  def generate_random_value(self):
    return ''.join(["{}".format(randint(0, 9)) for num in range(0, 24)])


# # This method is used while testing to generate a random sequence
# # of numbers to replace EPC's
# def random_number_generator(queue: Queue, main_queue: Queue):
#   logger = logging.getLogger('random_number_generator')
#   random_numbers_list: list = []
#   return_string: str = ""
#   while True:
#     random_number: float = random()
#     random_numbers_list.append(random_number)
#     if queue.qsize() > 0:
#       queue_value: Union[str, None] = queue.get()
#       logger.log(logging.DEBUG, f"Received {queue_value} from queue")
      
#       if queue_value is None:
#         break
      
#       if queue_value == "SCAN":
#         return_string = f"TAGS: {str(len(random_numbers_list))} "
#         for random_number in random_numbers_list:
#           return_string += str(random_number) + " "
#         logger.log(logging.DEBUG, f"Returning {return_string} to main queue")
#         main_queue.put(return_string)
#         return_string = ""

#     time.sleep(1)
#   logger.log(logging.DEBUG, "Exiting the random number generator process")