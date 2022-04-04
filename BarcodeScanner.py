import configparser
import logging
import logging.config
import re
import Constants
from Utility import Utility
from exceptions import BarcodeError
from exceptions import ApiError
from Scanner import Scanner


class BarcodeScanner:

    # ---------------------------------
    # BarcodeScanner class constructor
    # Input configFile : ConfigParser
    # ---------------------------------
    def __init__(self, configFile: configparser.ConfigParser()):
        self.configFile = configFile

        # Load the logger configuration
        logging.config.fileConfig(fname=self.configFile['File']['LoggerConfig'], disable_existing_loggers=False)

        # Initialize the class variables
        self.logger = logging.getLogger(__name__)
        self.scanner = Scanner(self.configFile['Barcode']['BarcodeUSBPort'])
        self.utility = Utility(self.configFile)

    # Get the barcode
    # Return Dict with cartonCode and Barcode
    def getBarcode(self):

        self.logger.debug("Start barcode scanning process")
        if not self.utility.usbPortIsUsable():
            self.logger.error(Constants.usbPortOpenError + "%s",
                              self.configFile['Barcode']['BarcodeUSBPort'])
            raise BarcodeError(Constants.usbPortOpenError +
                               self.configFile['Barcode']['BarcodeUSBPort'])

        # Continue in the loop till barcode is scanned
        while True:
            try:
                barcode = self.scanner.read()
                if barcode:  # Check the barcode scanned value using Regular expression
                    # if re.search("^HM[0-9]{4}", barcode):
                    if True:
                        self.logger.debug("Barcode scanned: %s ", barcode)
                        try:
                            cartonCode = self.utility.decodeBarcodeIntoCartonCode(barcode)
                            self.logger.debug("Carton Code: %s ", cartonCode)
                            return {'CC':cartonCode, 'BC':barcode}
                        except ApiError as err:
                            self.logger.error(str(err))
                            raise BarcodeError(str(err))
                    else:
                        self.logger.error("Invalid Barcode: %s ", barcode)
                        self.scanner.reset()
            except PermissionError as err:
                self.logger.error(Constants.permissionError + "%s "
                                                              ", Error:%s",
                                  self.configFile['Barcode']['BarcodeUSBPort'], str(err))
                raise BarcodeError(Constants.permissionError +
                                   self.configFile['Barcode']['BarcodeUSBPort'] + ", Error:" + str(err))


