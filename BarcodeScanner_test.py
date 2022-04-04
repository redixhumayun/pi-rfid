import configparser
import sys
import time
from datetime import datetime

from BarcodeScanner import BarcodeScanner
from exceptions import BarcodeError

''' Load the configuration '''
config = configparser.ConfigParser()

try:
    # config.read('/home/pi/RFID/conf/RFIDConfig.ini')
    config.read('D:/Projects/Python/RFIDDemo-25-Mar-2022/conf/RFIDConfig.ini')
except configparser.Error as error:
    print("Error occurred while running the code:" + str(error))
    sys.exit(10)

vBarcodeScanner = BarcodeScanner(config)

while True:
    try:
        now = datetime.now()
        print("Before Barcode Current Time =", datetime.utcnow().isoformat(sep=' ', timespec='milliseconds'))
        print(vBarcodeScanner.getBarcode())
        time.sleep(0.1)
    except BarcodeError as error:
        print('BarcodeError: ' + str(error))

    current_time = now.strftime("%H:%M:%S")
    print("After Barcode Current Time =", datetime.utcnow().isoformat(sep=' ', timespec='milliseconds'))
