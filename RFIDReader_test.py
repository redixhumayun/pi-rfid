import configparser
import sys
from datetime import datetime

from RFIDReader import RFIDReader

''' Load the configuration '''
config = configparser.ConfigParser()
try:
    # config.read('/home/pi/RFID/conf/RFIDConfig.ini')
    config.read('D:/Projects/Python/RFIDTagSystem/conf/RFIDConfig.ini')
except configparser.Error as error:
    print("Error occurred while running the code:" + str(error))
    sys.exit(10)

vRFIDReader = RFIDReader(config)

vRFIDReader.startTagProcessing()


