import configparser
import sys
import time

from Weighment import Weighment
from exceptions import WeighmentError

''' Load the configuration '''
config = configparser.ConfigParser()

try:
    config.read('/var/RFID/conf/RFIDConfig.ini')
    #config.read('D:/Projects/Python/RFIDDemo-25-Mar-2022/conf/RFIDConfig.ini')
except configparser.Error as error:
    print("Error occurred while running the code:" + str(error))
    sys.exit(10)

vWeighment = Weighment(config)

try:
    while True:
        print(vWeighment.getWeighment())
        time.sleep(100)

except WeighmentError as error:
    print('WeighmentError: ' + str(error))
