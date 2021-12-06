from multiprocessing import Process, Queue
import logging
import random

from weighing_scale_enums import WeighingScaleEnums


class WeighingScaleTest(Process):
    def __init__(self, queue: Queue, main_queue: Queue):
        Process.__init__(self)
        self.queue = queue
        self.main_queue = main_queue
        self.weight = 0
        self.logger = logging.getLogger('weighing_scale_test')

    def run(self):
        should_exit_loop = False
        while should_exit_loop is False:
            if self.queue.qsize() > 0:
                input_queue_string = self.queue.get()
                if input_queue_string == WeighingScaleEnums.START_WEIGHING:
                    is_weight_read = False
                    while is_weight_read is False:
                        self.weight = round(random.uniform(5.0, 10.0), 2)
                        self.logger.log(
                            logging.DEBUG, f"Read the weight from the scale as: {self.weight}")
                        is_weight_read = True
                        self.main_queue.put({
                            'type': WeighingScaleEnums.WEIGHT_VALUE_READ,
                            'data': {
                                'weight': self.weight
                            }
                        })
                    self.weight = 0
                elif input_queue_string is None:
                    self.logger.log(
                        logging.DEBUG, "Exiting the weighing process")
                    should_exit_loop = True
