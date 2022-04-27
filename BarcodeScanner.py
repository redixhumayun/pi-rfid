# -----------------------------------------------------------
# This class provides Barcode reading functionalities
#
# Date: 25-Mar-2022
# -----------------------------------------------------------
import configparser
import logging
import logging.config
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
        self.utility = Utility(self.configFile)
        self.scanner = Scanner(self.utility.getBarcodeUSBPort())

    # Get the barcode
    # Return Dict with cartonCode and Barcode
    def getBarcode(self):

        self.logger.debug("Start barcode scanning process")
        if not self.utility.usbPortIsUsable():
            self.logger.error(Constants.usbPortOpenError + "%s",
                              self.utility.getBarcodeUSBPort())
            raise BarcodeError(Constants.usbPortOpenError +
                               self.utility.getBarcodeUSBPort())

        # Continue in the loop till barcode is scanned
        while True:
            try:
                barcode = self.scanner.read()
                if barcode:  # Check the barcode scanned value using Regular expression
                    self.logger.debug("Barcode scanned: %s ", barcode)
                    try:
                        cartonCode = self.utility.decodeBarcodeIntoCartonCode(barcode)
                        self.logger.debug("Carton Code: %s ", cartonCode)
                        return {'CC': cartonCode, 'BC': barcode}
                    except ApiError as err:
                        self.logger.error(str(err))
                        raise BarcodeError(str(err))
            except PermissionError as err:
                self.logger.error(Constants.permissionError + "%s "
                                                              ", Error:%s",
                                  self.utility.getBarcodeUSBPort(), str(err))
                raise BarcodeError(Constants.permissionError +
                                   self.utility.getBarcodeUSBPort() + ", Error:" + str(err))
