# -----------------------------------------------------------
# This class provides utility methods
#
# Date: 20-Mar-2022
# -----------------------------------------------------------
import configparser
import logging
import os
import time
import serial
import socket
from puresnmp import get
import logging.config

import Constants
from MakeApiRequest import MakeApiRequest
from exceptions import UnknownCartonTypeError, ApiError


class Utility:

    # Initialize the class global variables
    rfidSessionId = 0

    # ---------------------------------
    # Utility class constructor
    # Input configFile : ConfigParser
    # ---------------------------------
    def __init__(self, configFile: configparser.ConfigParser()):
        self.configFile = configFile
        # Load the logger configuration
        logging.config.fileConfig(fname=self.configFile['File']['LoggerConfig'], disable_existing_loggers=False)
        self.logger = logging.getLogger(__name__)

        self.rfidReaderHost = self.configFile["RFIDParamerer"]["Host"]
        self.rfidReaderPort = int(self.configFile["RFIDParamerer"]["Port"])
        self.snmpCommunity = self.configFile["RFIDParamerer"]["SNMPCommunity"]
        self.snmpOid = self.configFile['RFIDParamerer']['SNMPOID']
        self.shipmentIdFile = self.configFile["File"]["ShipmentIdFile"]
        self.location = self.configFile["File"]["Location"]
        self.weightmentPort = self.configFile["Weighment"]["SerialPort"]
        self.barcodePort = self.configFile['Barcode']['BarcodeUSBPort']
        self.shipmentPrefix = self.configFile["Default"]["ShipmentPrefix"]

    # -------------------------------------------------------------
    # Get shipmentID Reading it from shipmentid.txt file
    # Increment shipmentId by 1 and write to shipmentid.txt file
    # Input configFile : ConfigParser
    # Output shipmentId: integer (in String format)
    # -------------------------------------------------------------
    def getShipmentId(self):

        try:
            with open(self.shipmentIdFile, 'r', encoding='utf-8') as shipmentIdFile:
                shipmentIdValues = shipmentIdFile.readlines()
                shipmentIdValue = int(shipmentIdValues[0])
                shipmentIdFile.close()
        except Exception as error:
            # In case of exception use UnixTimeStamp last 8 digit as shipmentId
            self.logger.error("Error in reading shipmentId from file:%s, error:%s", self.shipmentIdFile, str(error))
            shipmentIdValueStr = str(int(time.time()))[2:10]
            shipmentIdValue = int(shipmentIdValueStr)

        # Concatenate shipment prefix value and Set the shipmentId
        shipmentId = self.shipmentPrefix + str(shipmentIdValue).zfill(8)

        # Write the incremented shipmentId  to file to shipmentid.txt file
        shipmentIdValue = shipmentIdValue + 1
        try:
            with open(self.shipmentIdFile, 'w', encoding='utf-8') as shipmentIdFile:
                shipmentIdFile.write('%d \n' % shipmentIdValue)
                shipmentIdFile.close()
        except Exception as error:
            self.logger.error("Error in writing shipmentId to file:%s, error:%s",
                              self.shipmentIdFile, str(error))

        self.logger.debug("Return shipmentId:%s",
                          self.shipmentIdFile)
        return shipmentId

    # --------------------------------------------
    # Check Weighment serial port is open or not
    # Return True if open otherwise Return False
    # --------------------------------------------
    def serialPortIsUsable(self):
        try:
            serial.Serial(port=self.weightmentPort)
            return True
        except:
            return False

    # --------------------------------------------
    # Check Barcode USB port is open or not
    # Return True if open otherwise Return False
    # --------------------------------------------
    def usbPortIsUsable(self):

        # Check USB device file exists
        try:
            os.stat(self.barcodePort)
        except OSError:
            return False
        return True

    # --------------------------------------------------------
    # Check RFID Reader and network port is or up or not
    # Return True if network port open otherwise Return False
    # --------------------------------------------------------
    def rfidReaderIsConnected(self):

        result = 1
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(
            (self.rfidReaderHost, self.rfidReaderPort))
        sock.close()

        if result == 0:
            return True
        else:
            return False

    # ------------------------------------------------------------------
    # Get antenna status
    # Return dict with antenna id and True if connected otherwise false
    # ------------------------------------------------------------------
    def getAntennaStatus(self):

        antennaStatus = {}
        for antennaIndex in range(1, 5):  # Antenna range from 1 to 4
            try:  # if value is 3 then RFID antenna is connected
                if get(self.rfidReaderHost, self.snmpCommunity, self.snmpOid + str(antennaIndex)) == 3:
                    antennaStatus[antennaIndex] = True
                else:
                    antennaStatus[antennaIndex] = False
            except:  # In case of exception consider antenna is not connected
                antennaStatus[antennaIndex] = False

        return antennaStatus

    # Get RFIDSessionId Value
    @staticmethod
    def getRFIDSessionId():
        Utility.rfidSessionId = 0 if Utility.rfidSessionId == 1 else 1
        return Utility.rfidSessionId

    def getCartonPerforation(self, cartonCode):
        if cartonCode[-1] == 'P':
            return Constants.PERFORATED
        return Constants.NONPERFORATED

    def decide_carton_type(self, product_details_in_carton, carton_type):
        """
        This method will decide what type of carton it is based on the sizes
        of products found inside the carton
        1. Perforated Carton
          a. Solid cartons have only one size
          b. Mixed cartons have more than one size
        2. Non-perforated carton
          a. Is only a ratio pack
        """

        if carton_type == Constants.PERFORATED:
            # Carton is either solid or mixed
            hash_map_of_unique_sizes = {}
            for dict_item in product_details_in_carton:
                for key in dict_item:
                    if key == 'size':
                        if dict_item[key] in hash_map_of_unique_sizes:
                            hash_map_of_unique_sizes[dict_item[key]
                            ] = hash_map_of_unique_sizes[dict_item[key]] + 1
                        else:
                            hash_map_of_unique_sizes[dict_item[key]] = 1
            if len(hash_map_of_unique_sizes) == 1:
                return Constants.SOLID
            return Constants.MIXED

        if carton_type == Constants.NONPERFORATED:
            # Carton type is ratio
            return Constants.ASSORTED

        raise UnknownCartonTypeError('This carton type is not identifiable')

    def decodeEpcTagsIntoProductDetails(self, tagEpcCodeDict : dict):
        """
        This method is responsible for converting the EPC into product details via API request
        """
        self.logger.debug('API to Decode Epc Tags into ProductDetails')
        apiRequest = MakeApiRequest(self.configFile, '/fabship/product/rfid')
        decodedProductDetails = None
        try:
            decodedProductDetails = apiRequest.get_request_with_body(
                { 'epc': tagEpcCodeDict }
            )
            return decodedProductDetails
        except ApiError as err:
            self.logger.error(str(err))
            raise ApiError(str(err))


    def getCartonPackType(self, productDetails, cartonCode : str):
        """
        This method is responsible for getting the carton type based on the product details
        """
        self.logger.debug('Get Carton pack type using product detail and carton Code')
        cartonPerforation = self.getCartonPerforation(cartonCode)
        try:
            cartonType = self.decide_carton_type(
                productDetails, cartonPerforation
            )
            return cartonType
        except UnknownCartonTypeError as err:
            self.logger.error(str(err))
            raise UnknownCartonTypeError(str(err))

    # Decode Barcode Into CartonCode using API
    def decodeBarcodeIntoCartonCode(self, barcode):
        self.logger.debug('API to Decode Barcode into CartonCode')
        apiRequest = MakeApiRequest(self.configFile, f"/fabship/product/rfid/carton/barcode/{barcode}")
        try:
            cartonCode = apiRequest.get()
            return cartonCode
        except ApiError as err:
            self.logger.error(str(err))
            raise ApiError(str(err))

    def uploadCartonDetails(self, location, listOfEpcTags, cartonWeight, cartonCode, cartonBarcode, cartonPackType, shipmentId) -> bool:

        """This method is used to upload the details associated with a carton"""
        apiRequest = MakeApiRequest(self.configFile, '/fabship/product/rfid')
        self.logger.debug(f"Received the following tags to upload: {listOfEpcTags}")

        # Make the API request
        try:
            self.logger.debug("Making a Upload POST request")
            response = apiRequest.post(
                {
                    'location': location,
                    'epcs': listOfEpcTags,
                    'shipmentId': str(shipmentId),
                    'cartonCode': cartonCode,
                    'cartonBarcode': cartonBarcode,
                    'cartonWeight': cartonWeight,
                    'packType': cartonPackType
                }
            )
            self.logger.debug("Received the following response:%s", str(response))
            return True
        except ApiError as err:
            self.logger.error(str(err))
            raise ApiError(str(err))

    # Return the location
    def getLocation(self):

        location = 'Unknown'
        try:
            with open(self.location, 'r', encoding='utf-8') as locationFile:
                locationLine = locationFile.readlines()

                # Remove any leading and trailing whitespaces
                location = str(locationLine[0]).strip()
                locationFile.close()
        except FileNotFoundError as error:
            self.logger.error(str(error))

        return location