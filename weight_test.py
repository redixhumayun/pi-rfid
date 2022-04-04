import configparser
import sys

from Weighment import Weighment
from exceptions import WeighmentError

''' Load the configuration '''
config = configparser.ConfigParser()

try:
    #config.read('/home/pi/RFID/conf/RFIDConfig.ini')
    config.read('D:/Projects/Python/RFIDDemo-25-Mar-2022/conf/RFIDConfig.ini')
except configparser.Error as error:
    print("Error occurred while running the code:" + str(error))
    sys.exit(10)

vWeighment = Weighment(config)

try:
    print(vWeighment.getWeighment())
except WeighmentError as error:
    print('WeighmentError: ' + str(error))
