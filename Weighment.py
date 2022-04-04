# -----------------------------------------------------------
# This class provides weighment functionalities
#
# Date: 22-Mar-2022
# -----------------------------------------------------------
import configparser
import logging
import logging.config
import serial
import time
import Constants
from exceptions import WeighmentError
from Utility import Utility


class Weighment:

    # ---------------------------------
    # Weighment class constructor
    # Input configFile : ConfigParser
    # ---------------------------------
    def __init__(self, configFile: configparser.ConfigParser()):
        self.configFile = configFile

        # Load the logger configuration
        logging.config.fileConfig(fname=self.configFile['File']['LoggerConfig'], disable_existing_loggers=False)
        self.logger = logging.getLogger(__name__)

        # Initialize the class variables
        # Read WeighmentCount from config file
        self.weighmentCount = configFile.getint("Weighment", "WeighmentCount")
        self.weighmentSerial = None
        self.utility = Utility(self.configFile)

    # Get weight from weighing scale using serial port data
    def getWeighment(self):

        self.logger.debug("Start weighment process")

        if not self.utility.serialPortIsUsable():
            self.logger.error(Constants.serialPortOpenError +
                              self.configFile["Weighment"]["SerialPort"])
            raise WeighmentError(Constants.serialPortOpenError +
                                 self.configFile["Weighment"]["SerialPort"])

        try:
            self.weighmentSerial = serial.Serial(self.configFile["Weighment"]["SerialPort"],
                                                 baudrate=self.configFile.getint("Weighment", "BaudRate"),
                                                 parity=serial.PARITY_EVEN,
                                                 stopbits=serial.STOPBITS_ONE,
                                                 bytesize=serial.SEVENBITS,
                                                 timeout=self.configFile.getint("Weighment", "SerialPortTimeout"))
        except Exception as error:
            self.logger.error(Constants.serialPortOpenError +
                              self.configFile["Weighment"]["SerialPort"] + ", error:" + str(error))
            raise WeighmentError(Constants.serialPortOpenError +
                                 self.configFile["Weighment"]["SerialPort"] + ", error:" + str(error))

        emptyWeightCount = 0
        zeroWeightCount = 0
        correctWeightCount = 0
        correctWeight = None

        while True:
            self.weighmentSerial.write(b"blabla")
            time.sleep(0.2)  # wait for the data to get

            try:
                serialOutput = (self.weighmentSerial.read(self.weighmentSerial.in_waiting))
                serialOutput = serialOutput.decode('UTF-8')
                serialOutputLine = serialOutput.splitlines(True)
            except Exception as error:
                self.logger.error(Constants.serialPortTimeoutError +
                                  self.configFile["Weighment"]["SerialPort"] + ", error:" + str(error))
                serialOutput = None

            # if serialOutputLine is emtpy increment empty count
            if not serialOutput:
                emptyWeightCount = emptyWeightCount + 1
            else:
                weight = None

                for weight in serialOutputLine:
                    weight = weight.strip()

                # if there is a value check it is zero or proper weight
                if weight:
                    if float(weight) == 0.0:
                        zeroWeightCount = zeroWeightCount + 1
                    else:
                        correctWeightCount = correctWeightCount + 1
                        correctWeight = weight
                else:  # if weight is empty increment empty weight count
                    emptyWeightCount = emptyWeightCount + 1

            # if got proper weight then return the weight otherwise try again
            if correctWeightCount >= self.weighmentCount:
                self.logger.debug("Read weight successfully with value:%s Kg", correctWeight)
                return correctWeight
            elif emptyWeightCount >= self.weighmentCount:
                self.logger.error(Constants.weighingScaleIsOff)
                time.sleep(1)
            elif zeroWeightCount >= self.weighmentCount:
                self.logger.error(Constants.noItemPlaceOnWeighingScale)
                time.sleep(1)
