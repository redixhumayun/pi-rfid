# -----------------------------------------------------------
# This class provides reading RFID tags functionalities
#
# Date: 26-Mar-2022
# -----------------------------------------------------------
import configparser
from twisted.internet import reactor
import Constants
from Utility import Utility
from exceptions import RFIDError
import sllurp.llrp as llrp
import logging.config


class RFIDReader:

    # ---------------------------------
    # RFIDReader class constructor
    # Input configFile : ConfigParser
    # ---------------------------------
    def __init__(self, configFile: configparser.ConfigParser()):
        self.configFile = configFile

        # Load the logger configuration
        logging.config.fileConfig(fname=self.configFile['File']['LoggerConfig'], disable_existing_loggers=False)
        self.logger = logging.getLogger(__name__)
        self.vUtility = Utility(self.configFile)
        # Initialize the class variables
        self.iConnector = None
        self.tagReadCount = 0
        self.tagEpcCodeDict = {}
        self.isInScanProcess = False
        self.factory = None

    # Initialize the LLRP Client factory by reading values from configuration file
    def initFactory(self):
        self.factory = llrp.LLRPClientFactory(disconnect_when_done=self.configFile.getboolean('RFIDParamerer',
                                                                                              'DisconnectWhenDone'),
                                              antennas=eval(self.configFile.get('RFIDParamerer', 'Antennas')),
                                              tari=self.configFile.getint('RFIDParamerer', 'Tari'),
                                              session=Utility.getRFIDSessionId(),
                                              tag_population=self.configFile.getint('RFIDParamerer', 'TagPopulation'),
                                              start_inventory=self.configFile.getboolean('RFIDParamerer',
                                                                                         'StartInventory'),
                                              tx_power=self.configFile.getint('RFIDParamerer', 'TXPower'),
                                              report_every_n_tags=self.configFile.getint('RFIDParamerer',
                                                                                         'ReportEveryNTags'),
                                              start_first=True,
                                              duration=0.5,
                                              tag_content_selector={
                                                  'EnableROSpecID': self.configFile.getboolean('TagContentSelector',
                                                                                               'EnableROSpecID'),
                                                  'EnableSpecIndex': self.configFile.getboolean('TagContentSelector',
                                                                                                'EnableSpecIndex'),
                                                  'EnableInventoryParameterSpecID': self.configFile.getboolean('TagContentSelector',
                                                                                                               'EnableInventoryParameterSpecID'),
                                                  'EnableAntennaID': self.configFile.getboolean('TagContentSelector',
                                                                                                'EnableAntennaID'),
                                                  'EnableChannelIndex': self.configFile.getboolean('TagContentSelector',
                                                                                                   'EnableChannelIndex'),
                                                  'EnablePeakRRSI': self.configFile.getboolean('TagContentSelector',
                                                                                               'EnablePeakRRSI'),
                                                  'EnableFirstSeenTimestamp': self.configFile.getboolean('TagContentSelector',
                                                                                                         'EnableFirstSeenTimestamp'),
                                                  'EnableLastSeenTimestamp': self.configFile.getboolean('TagContentSelector',
                                                                                                        'EnableLastSeenTimestamp'),
                                                  'EnableTagSeenCount': self.configFile.getboolean('TagContentSelector',
                                                                                                   'EnableTagSeenCount'),
                                                  'EnableAccessSpecID': self.configFile.getboolean('TagContentSelector',
                                                                                                   'EnableAccessSpecID')
                                              })

        self.factory.addTagReportCallback(self.tagReportCallback)

    # ----------------------------------------------------------------------
    # This method to run each time the reader reports seeing tags.
    # Tag report call back function
    # process tag read event and update tagEpcCodeDict (unique tag values)
    # and tagReadCount
    # input: llrpMsg : llrp.LLRPMessage
    # ----------------------------------------------------------------------
    def tagReportCallback(self, llrpMsg: llrp.LLRPMessage):

        # Don't process tag if isInScanProcess is False
        if not self.isInScanProcess:
            return

        # Extract only required info from llrpMsg
        tags = llrpMsg.msgdict['RO_ACCESS_REPORT']['TagReportData']

        # The tag can be either in EPCData or EPC-96 filed
        for tag in tags:
            result = None
            if "EPCData" in tag:
                result = tag["EPCData"]["EPC"]
            elif "EPC-96" in tag:
                result = tag["EPC-96"]

            if result:
                tagValue = str(result.decode('UTF-8')).upper()
                # if tag key not exists then add to tag Dictionary
                if tagValue not in self.tagEpcCodeDict:
                    self.tagEpcCodeDict[tagValue] = None
                    self.tagReadCount = self.tagReadCount + 1
            else:
                self.logger.error('Invalid RFID Data:%s', tag)

    # ----------------------------------------------------------------------------
    # Method to close RFID reader connection. 
    # This method is called from main application when RFID GUI window is closed
    # ----------------------------------------------------------------------------
    def closeConnection(self):

        if self.iConnector:
            try:
                self.iConnector.disconnect()
                self.iConnector = None
                return True
            except Exception as error:
                self.logger.error(Constants.rfidCloseConnectError + ', with error:' + str(error))
                self.iConnector = None
                return False
    
    # Return RFID tag read count : integer
    def getTagReadCount(self):
        return self.tagReadCount

    # Connect to RFID reading using RFID reader IP an LLRP Port
    def connectTCP(self):

        self.logger.debug('Connect to RFID Reader:%s', self.configFile["RFIDParamerer"]["Host"])

        try:
            # Connect to RFID reader
            self.iConnector = reactor.connectTCP(self.configFile["RFIDParamerer"]["Host"],
                                                 self.configFile.getint("RFIDParamerer", "Port"),
                                                 self.factory, self.configFile.getint("RFIDParamerer", "Timeout"))
        except Exception as error:
            self.logger.error(Constants.rfidReaderConnectError + "on RFID host:" +
                              self.configFile["RFIDParamerer"]["Host"] + ", on port:" +
                              str(self.configFile["RFIDParamerer"]["Port"]) + ", with error:" + str(error))
            raise RFIDError(Constants.rfidReaderConnectError + "on RFID host:" +
                            self.configFile["RFIDParamerer"]["Host"] + ", on port:" +
                            str(self.configFile["RFIDParamerer"]["Port"]) + ", with error:" + str(error))

    # Clear tag read count and tag EPC code 
    def clearTagDetail(self):
        # Make it False when  tag reading process is stopped or main process is stopped
        self.isInScanProcess = False
        self.tagReadCount = 0
        self.tagEpcCodeDict.clear()

    # Stop RFID tag reading process and return tag EPC Codes : Dictionary
    def stopTagProcessing(self):

        self.logger.debug('Stop Tag Processing')

        # Make isInScanProcess False when  tag reading process is stopped
        self.isInScanProcess = False

        # Converting dict into list where tag EPC code is used both as key and value
        tagList = list(self.tagEpcCodeDict.keys())
        return tagList

    # Start RFID tag reading process
    def startTagProcessing(self):

        self.logger.debug('Start Tag Processing')

        # Clear the last tag inventory detail
        self.clearTagDetail()

        # Make isInScanProcess true when tag reading process is started
        self.isInScanProcess = True
        self.initFactory()
        if not self.iConnector:
            try:
                self.connectTCP()
                reactor.run(installSignalHandlers=False)
            except Exception as error:
                self.logger.error(Constants.rfidOpenConnectError + ', with error:' + str(error))
                raise RFIDError(Constants.rfidOpenConnectError + ', with error:' + str(error))
