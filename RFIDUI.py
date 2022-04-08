# -----------------------------------------------------------
# This class provides GUI functionalities
#
# Date: 24-Mar-2022
# -----------------------------------------------------------
import logging
import logging.config
import os.path
import threading
import time
from tkinter import *  # Tkinter used for UI
from PIL import Image, ImageTk  # Display logo on the UI
from tkinter.font import Font
import RPi.GPIO as GPIO
import Constants
from BarcodeScanner import BarcodeScanner
from RFIDReader import RFIDReader
from Utility import Utility
import sys
import os
import configparser  # Parse and use config file
from tkinter import messagebox

from Weighment import Weighment
from exceptions import BarcodeError, WeighmentError, RFIDError, ApiError, UnknownCartonTypeError


class RFIDUI:

    # ---------------------------------
    # RFIDUI class constructor
    # Input configFile : ConfigParser
    # ---------------------------------
    def __init__(self, configFile: configparser.ConfigParser()):

        self.shipmentId = None  # Unique ShipmentId value

        self.configFile = configFile

        ''' Load the logger configuration '''
        logging.config.fileConfig(fname=self.configFile['File']['LoggerConfig'], disable_existing_loggers=False)

        self.logger = logging.getLogger(__name__)
        self.rfidUtility = Utility(self.configFile)

        self.shipmentId = self.rfidUtility.getShipmentId()
        self.location = self.rfidUtility.getLocation()

        self.imageFolder = self.configFile['File']['ImagePath']

        # Status Labels
        self.ScaleStatusLabel = None
        self.barcodeStatusLabel = None
        self.AntennaStatusLabelId = {}
        # self.AntennaStatusLabel2 = None
        # self.AntennaStatusLabel3 = None
        # self.AntennaStatusLabel4 = None
        # self.AntennaStatusLabel5 = None
        # self.AntennaStatusLabel6 = None

        self.ReaderStatusLabel = None
        self.processState = 'Start'
        self.conveyorState = 0

        # UI items
        self.InfoLabel1 = None
        self.InfoLabel2 = None
        self.InfoLabel3 = None
        self.InfoLabel4 = None
        self.CartonInfo = None
        self.CartonWeightLabel = None
        self.CartonWeight = None
        self.CartonBarcodeLabel = None
        self.CartonBarcode = None
        self.ScannedPieces = None
        self.ScannedPieceCount = None
        self.StartStopRFIDButton = None
        self.ResetButton = None
        self.ReScanButton = None

        self.barcodeScanner = BarcodeScanner(self.configFile)
        self.weighment = Weighment(self.configFile)
        self.rfidReader = RFIDReader(self.configFile)

        self.weight = None
        self.cartonCode = None
        self.cartonBarocode = None
        self.cartonType = None
        self.tagReadCount = 0
        self.tagEpcCodeDict = []

        self.readBarcodeAndWeightThread = None
        self.processTagThread = None
        self.moveConveyorThread = None
        self.cartonTypeThread = None
        self.rfidCallBackId = None

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(16, GPIO.OUT)
        GPIO.output(16, GPIO.LOW)

        self.startFirstProcess()  # Start from first step

    # This method will read RFID Tags and it is executed as thread
    def readRFIDTags(self):

        try:
            self.rfidReader.startTagProcessing()
        except RFIDError as error:
            self.logger.error('Error in readRFIDTags:%s', str(error))
            messagebox.showerror("RFID tag reading error", str(error))

    # Get carthon type detail using API
    def getCartonType(self):

        try:
            decodedProductDetails = self.rfidUtility.decodeEpcTagsIntoProductDetails(self.tagEpcCodeDict)
            self.cartonType = self.rfidUtility.getCartonPackType(decodedProductDetails, self.cartonCode)
            self.InfoLabel2.config(font=self.large4_font, text=self.cartonType)
        except ApiError as error:
            self.logger.error('Error in decode epc tags into product details:%s', str(error))
            messagebox.showerror('Carton Type error', str(error))
            self.StartStopRFIDButton.config(text="Upload", command=self.uploadCallback, state="disabled")
        except UnknownCartonTypeError as error:
            self.logger.error('Error in get carton pack type :%s', str(error))
            messagebox.showerror('Carton Type error', str(error))
            self.StartStopRFIDButton.config(text="Upload", command=self.uploadCallback, state="disabled")

    # Read Barcode and weight
    def readBarcodeAndWeight(self):

        # First Get Carton Code, if status is Exit then break the loop
        # If barcode value is found then break the loop
        while True:

            # Exit loop in case state is Exit or Reset
            if self.processState == 'Exit' or self.processState == 'Reset':
                return

            if not self.cartonCode:
                try:
                    codeAndBarcode = self.barcodeScanner.getBarcode()
                    self.cartonCode = codeAndBarcode['CC']
                    self.cartonBarocode = codeAndBarcode['BC']
                    self.InfoLabel4.config(text=self.cartonCode)  # Scan carton area
                    self.CartonBarcode.config(text=self.cartonCode)  # Carton Info area
                except BarcodeError as error:
                    self.logger.error('Barcode reading error:' + str(error))
                    messagebox.showerror('Barcode error', str(error))

            if self.cartonCode:
                break

        # Get weighment and update message in UI
        while True:

            # Exit loop in case state is Exit or Reset
            if self.processState == 'Exit' or self.processState == 'Reset':
                return

            if not self.weight:
                try:
                    self.weight = self.weighment.getWeighment()

                    if self.weight:  # Enable Reset button if we have wight
                        self.ResetButton.config(state='normal')

                    self.InfoLabel2.config(text=self.weight)  # Scan carton area
                    self.CartonWeight.config(text=self.weight)  # Carton Info area
                except WeighmentError as error:
                    self.logger.error('Weighment reading error:' + str(error))
                    messagebox.showerror("Weighing error", str(error))

            # if we got both barcode and weight then return
            if self.weight:
                if self.StartStopRFIDButton:
                    self.StartStopRFIDButton.config(state='normal')
                    self.processState = 'StartRFIDScan'  # Change the state to StartRFIDScan
                return

            if self.processState == 'Exit':
                return

    # Start process
    def startFirstProcess(self):

        self.logger.debug("Start Barcode and Weight reading process")

        # if state is Reset and read barcode thread exists then close the thread
        if self.processState == 'Reset':
            if self.readBarcodeAndWeightThread.is_alive():
                self.readBarcodeAndWeightThread.join(0)

            # Set the value to start so that read barcode thread can work properly
            self.processState = 'Start'

        self.readBarcodeAndWeightThread = threading.Thread(target=self.readBarcodeAndWeight)
        self.readBarcodeAndWeightThread.start()

    # ResetButtonCallback action
    def ResetButtonCallback(self):

        self.logger.debug("Move the conveyor in...")

        #  Make conveyor  movement when reset button is pressed
        if self.conveyorState == 0:
            sleepTimer = self.configFile.getint("Default", "GPIO16InTimer") + self.configFile.getint("Default", "GPIO16OutTimer")
            self.moveConveyorThread = threading.Thread(target=self.moveConveyor, args=(sleepTimer,))
            self.moveConveyorThread.start()
            self.moveConveyorThread.join(0)
        elif self.conveyorState == 1:
            sleepTimer = self.configFile.getint("Default", "GPIO16OutTimer")
            self.moveConveyorThread = threading.Thread(target=self.moveConveyor, args=(sleepTimer,))
            self.moveConveyorThread.start()
            self.moveConveyorThread.join(0)

        self.conveyorState = 0  # Reset conveyor state
        self.processState = 'Reset'
        self.ResetButton.config(state='disabled')  # Avoid multiple press

        #
        # Reset the text
        self.BarCodeScanLabel.config(background='#C4F1F9')
        self.RFIDScanLabel.config(background=Constants.white)
        self.TypeScanLabel.config(background=Constants.white)
        self.MainActionLabel.config(text='Scan Carton')

        # Reset the text self.SubInfoFrame and self.StatusFrame
        self.InfoLabel1.config(text='Carton Weight')
        self.InfoLabel2.config(text='', font=self.large2_font)
        self.InfoLabel3.config(text='Carton code')
        self.InfoLabel4.config(text='', font=self.large2_font)
        self.CartonWeight.config(text='')
        self.CartonBarcode.config(text='')
        self.ScannedPieceCount.config(text='')
        self.ReScanButton.place(x=0, y=0, width=0, height=0)  # Hide the Rescan button

        self.StartStopRFIDButton.config(text='Start RFID Scan', font=self.medium0_5_font,
                                        command=self.StartRFIDButtonCallback, state='disabled')

        self.weight = None
        self.cartonCode = None
        self.cartonBarocode = None
        self.cartonType = None
        self.tagReadCount = 0
        self.tagEpcCodeDict.clear()  # Clear the Dict content

        self.StartStopRFIDButton.config(state='disabled')
        self.startFirstProcess()  # Start from first step

    # uploadCallback action updater
    def uploadCallback(self):

        # Clear the text
        self.InfoLabel1.config(text='')
        self.InfoLabel2.config(text='')

        result = False
        try:
            result = self.rfidUtility.uploadCartonDetails(self.location, self.tagEpcCodeDict, self.weight,
                                                          self.cartonCode,
                                                          self.cartonBarocode, self.cartonType, self.shipmentId)
        except ApiError as error:
            self.logger.error("Error raised while uploading tags:%s", error, )
            messagebox.showerror("Failed to upload", str(error))

        if result:
            self.logger.debug("Tag data uploaded successfully...")
            messagebox.showinfo("Tag upload", "Carton Details successfully uploaded")

        # Start the process again
        self.ResetButtonCallback()

    # RescanButtonCallback action updater
    def RescanButtonCallback(self):

        self.processState = 'Rescan'
        self.StartRFIDButtonCallback()

    # getCartonTypeCallback action updater
    def getCartonTypeCallback(self):

        self.logger.debug("Get carton type")

        self.processState = 'GetCartonType'
        self.BarCodeScanLabel.config(background=Constants.white)
        self.RFIDScanLabel.config(background=Constants.white)
        self.MainActionLabel.config(text='Check Carton Type')
        self.TypeScanLabel.config(background='#C4F1F9')
        self.InfoLabel1.config(text='Carton Type Details')
        self.InfoLabel2.config(text='')
        self.StartStopRFIDButton.config(text="Upload", command=self.uploadCallback, state="normal")
        self.cartonTypeThread = threading.Thread(target=self.getCartonType())
        self.cartonTypeThread.start()

    # StopRFIDButtonCallback action updater
    def StopRFIDButtonCallback(self):

        self.processState = 'StopRFIDScan'
        self.logger.debug("Stop RFID Tag reading process")
        self.tagEpcCodeDict = self.rfidReader.stopTagProcessing()
        self.ScannedPieceCount.config(text=self.tagReadCount)
        self.StartStopRFIDButton.config(text="Get Carton Type", command=self.getCartonTypeCallback, state="normal")

        self.ReScanButton.place(x=0, y=0, width=0, height=0)  # Hide the Rescan button

        #  From RFID chamber to exit
        sleepTimer = self.configFile.getint("Default", "GPIO16OutTimer")
        self.moveConveyorThread = threading.Thread(target=self.moveConveyor, args=(sleepTimer,))
        self.moveConveyorThread.start()
        self.moveConveyorThread.join(0)

        self.conveyorState = 2  # Move out of RFID chamber

    # Move the conveyor
    def moveConveyor(self, sleepTimer):

        self.logger.debug('Moving conveyor for:%s seconds', sleepTimer)
        sleepTimer = int(sleepTimer)

        GPIO.output(16, GPIO.HIGH)
        time.sleep(sleepTimer)
        GPIO.output(16, GPIO.LOW)

    # StartRFIDButtonCallback action updater
    def StartRFIDButtonCallback(self):

        # Change menu background color based on menu selection
        self.BarCodeScanLabel.config(background=Constants.white)
        self.RFIDScanLabel.config(background='#C4F1F9')
        self.TypeScanLabel.config(background=Constants.white)
        self.MainActionLabel.config(text='Scan RFID')
        self.InfoLabel1.config(text='Scanned Pieces')
        self.InfoLabel2.config(font=self.large3_font)
        self.InfoLabel3.config(text='')
        self.InfoLabel4.config(text='')
        self.ReScanButton.place(x=367, y=400, width=80, height=30)  # Show Rescan button

        self.StartStopRFIDButton.config(text="Stop RFID Scan", command=self.StopRFIDButtonCallback)

        self.logger.debug("Start RFID Tag reading process")
        self.processTagThread = threading.Thread(target=self.readRFIDTags)
        self.processTagThread.start()
        self.updateTagReadCount()

        #  From start to RFID chamber
        if self.conveyorState == 0:
            sleepTimer = self.configFile.getint("Default", "GPIO16InTimer")
            self.moveConveyorThread = threading.Thread(target=self.moveConveyor, args=(sleepTimer,))
            self.moveConveyorThread.start()
            self.moveConveyorThread.join(0)

        self.conveyorState = 1  # In the RFID chamber

    # ####################### Device status info #####################

    # Update Weight serial port status
    def updateWeightStatus(self):

        if self.rfidUtility.serialPortIsUsable():
            self.ScaleStatusLabel.config(background=Constants.green)
        else:
            self.ScaleStatusLabel.config(background=Constants.red)

        self.ScaleStatusLabel.after(Constants.RefreshStatusMilliSeconds, self.updateWeightStatus)

    # Update Barcode USB status
    def updateBarcodeStatus(self):

        if self.rfidUtility.usbPortIsUsable():
            self.barcodeStatusLabel.config(background=Constants.green)
        else:
            self.barcodeStatusLabel.config(background=Constants.red)

        self.barcodeStatusLabel.after(Constants.RefreshStatusMilliSeconds, self.updateBarcodeStatus)

    # Update RFID reader status
    def updateRFIDReaderStatus(self):

        if self.rfidUtility.rfidReaderIsConnected():
            self.ReaderStatusLabel.config(background=Constants.green)
        else:
            self.ReaderStatusLabel.config(background=Constants.red)

        self.ReaderStatusLabel.after(Constants.RefreshStatusMilliSeconds, self.updateRFIDReaderStatus)

    # Update antenna status
    def updateAntennaStatus(self):

        antennaStatus = self.rfidUtility.getAntennaStatus()

        for antennaId, antennaStatus in antennaStatus.items():
            if antennaStatus:
                self.AntennaStatusLabelId[antennaId].config(background=Constants.green, fg=Constants.black)
            else:
                self.AntennaStatusLabelId[antennaId].config(background=Constants.red, fg=Constants.white)

        self.ReaderStatusLabel.after(Constants.RefreshStatusMilliSeconds, self.updateAntennaStatus)

    # Update RFID tag count detail
    def updateTagReadCount(self):

        if self.processState == 'StartRFIDScan' or self.processState == 'Rescan':
            self.tagReadCount = self.rfidReader.getTagReadCount()
            self.InfoLabel2.config(text=self.tagReadCount)
            self.rfidCallBackId = self.InfoLabel2.after(Constants.RefreshRFIDCount, self.updateTagReadCount)
        else:
            # Don't refresh rfid count
            if self.rfidCallBackId:
                self.MainWindow.after_cancel(self.rfidCallBackId)
                self.rfidCallBackId = None

    # Main method
    def mainMethod(self):

        # Window setup
        self.MainWindow = Tk()
        self.MainWindow.title('RFID System')
        self.MainWindow.geometry('1000x800')

        # Fonts
        self.small_font = Font(family='Inter', size=8, weight='normal')
        self.medium0_5_font = Font(family='Helvetica', size=12, weight='bold')
        self.medium1_font = Font(family='Inter', size=20, weight='normal')
        self.medium1_italic_font = Font(family='Inter', size=20, slant='italic', weight='bold')
        self.medium1_bold_font = Font(family='Inter', size=20, weight='bold')
        self.medium2_font = Font(family='Roboto', size=23, weight='normal')
        self.medium3_font = Font(family='Roboto', size=18, weight='normal')
        self.large2_font = Font(family='Roboto', size=48, weight='normal')
        self.large3_font = Font(family='Roboto', size=100, weight='normal')
        self.large4_font = Font(family='Roboto', size=60, weight='normal')

        # ############################ Display four frames #############################

        MenuFrame = LabelFrame(self.MainWindow, width=100, height=700, bd=0, bg='#065666').place(x=0, y=0)
        LargeFrame = LabelFrame(self.MainWindow, width=900, height=700, bd=0, bg=Constants.white).place(x=100, y=0)
        InfoFrame = LabelFrame(self.MainWindow, width=585, height=610, bd=1, bg=Constants.white,
                               highlightbackground='#065666', highlightthickness=1).place(x=110, y=80)
        SubInfoFrame = LabelFrame(self.MainWindow, width=290, height=400, bd=1, bg=Constants.white,
                                  highlightbackground='#065666', highlightthickness=1).place(x=705, y=80)
        StatusFrame = LabelFrame(self.MainWindow, width=1000, height=100, bd=1, bg=Constants.white,
                                 highlightbackground='#065666', highlightthickness=1).place(x=0, y=700)

        # ################################# Insert Buttons ################################

        self.StartStopRFIDButton = Button(self.MainWindow, text='Start RFID Scan', font=self.medium0_5_font,
                                          command=self.StartRFIDButtonCallback, state='disabled', width=20, height=3,
                                          bg='#C4F1F9', highlightbackground='#065666', highlightthickness=1)
        self.StartStopRFIDButton.place(x=730, y=510)

        self.ResetButton = Button(self.MainWindow, text='Reset', font=self.medium0_5_font, state='disabled',
                                  command=self.ResetButtonCallback, width=20, height=2, bg='#C4F1F9',
                                  highlightbackground='#065666', highlightthickness=1)
        self.ResetButton.place(x=730, y=620)

        # ################################# Start of Menu Frame ################################
        BarCodeImage = Image.open(self.imageFolder + 'barcode.png')
        BarCodeImageFile = ImageTk.PhotoImage(BarCodeImage)
        self.BarCodeScanLabel = Label(MenuFrame, image=BarCodeImageFile, width=70, height=70, text='Scan', compound=TOP,
                                      font=self.small_font, background='#C4F1F9')  # , background='#C4F1F9'
        self.BarCodeScanLabel.place(x=13, y=82)

        RFIDImage = Image.open(self.imageFolder + 'RFID.png')
        RFIDImageFile = ImageTk.PhotoImage(RFIDImage)
        self.RFIDScanLabel = Label(MenuFrame, image=RFIDImageFile, width=70, height=70, text='RFID', compound=TOP,
                                   font=self.small_font, background=Constants.white)  # , background='#C4F1F9'
        self.RFIDScanLabel.place(x=13, y=315)

        TypeImage = Image.open(self.imageFolder + 'type.png')
        TypeImageFile = ImageTk.PhotoImage(TypeImage)
        self.TypeScanLabel = Label(MenuFrame, image=TypeImageFile, width=70, height=70, text='Type', compound=TOP,
                                   font=self.small_font, background=Constants.white)  # , background='#C4F1F9'
        self.TypeScanLabel.place(x=13, y=549)

        # ################################# Main Label ################################

        self.MainActionLabel = Label(LargeFrame, text='Scan Carton', font=self.medium2_font, fg='#1A365D',
                                     bg=Constants.white)
        self.MainActionLabel.place(x=105, y=30)
        Label(LargeFrame, text='Shipment ID - ' + self.shipmentId, font=self.medium3_font, fg='#1A365D',
              bg=Constants.white).place(x=600, y=10)

        # ################################# Status Frame ################################

        Label(StatusFrame, text='Reader', font=self.medium1_font, bg=Constants.white).place(x=10, y=740)
        self.ReaderStatusLabel = Label(StatusFrame, width=5, bg=Constants.red)
        self.ReaderStatusLabel.place(x=120, y=750)

        Label(StatusFrame, text='Antenna', font=self.medium1_font, bg=Constants.white).place(x=200, y=740)
        self.AntennaStatusLabelId[1] = Label(StatusFrame, text='1', width=5, bg=Constants.red, fg=Constants.white)
        self.AntennaStatusLabelId[1].place(x=325, y=750)
        self.AntennaStatusLabelId[2] = Label(StatusFrame, text='2', width=5, bg=Constants.red, fg=Constants.white)
        self.AntennaStatusLabelId[2].place(x=375, y=750)
        self.AntennaStatusLabelId[3] = Label(StatusFrame, text='3', width=5, bg=Constants.red, fg=Constants.white)
        self.AntennaStatusLabelId[3].place(x=425, y=750)

        self.AntennaStatusLabelId[4] = Label(StatusFrame, text='4', width=5, bg=Constants.red, fg=Constants.white)
        self.AntennaStatusLabelId[4].place(x=475, y=750)
        self.AntennaStatusLabelId[5] = Label(StatusFrame, text='5', width=5, bg=Constants.red, fg=Constants.white)
        self.AntennaStatusLabelId[5].place(x=525, y=750)
        self.AntennaStatusLabelId[6] = Label(StatusFrame, text='6', width=5, bg=Constants.red, fg=Constants.white)
        self.AntennaStatusLabelId[6].place(x=575, y=750)

        Label(StatusFrame, text='Barcode', font=self.medium1_font, bg=Constants.white).place(x=665, y=740)
        self.barcodeStatusLabel = Label(StatusFrame, width=5, bg=Constants.red)
        self.barcodeStatusLabel.place(x=784, y=750)

        Label(StatusFrame, text='Scale', font=self.medium1_font, bg=Constants.white).place(x=855, y=740)
        self.ScaleStatusLabel = Label(StatusFrame, width=5, bg=Constants.red)
        self.ScaleStatusLabel.place(x=935, y=750)

        # ################################# Info Frame ################################
        self.InfoLabel1 = Label(InfoFrame, text='Carton Weight', font=self.medium3_font, fg='#1A365D',
                                bg=Constants.white, anchor='center')
        self.InfoLabel1.place(x=115, y=170, width=575)
        self.InfoLabel2 = Label(InfoFrame, font=self.large2_font, fg='#1A365D', bg=Constants.white, anchor='center')
        self.InfoLabel2.place(x=115, y=200, width=575)
        self.InfoLabel3 = Label(InfoFrame, text='Carton code', font=self.medium3_font, fg='#1A365D',
                                bg=Constants.white, anchor='center')
        self.InfoLabel3.place(x=115, y=410, width=575)
        self.InfoLabel4 = Label(InfoFrame, font=self.large2_font, fg='#1A365D', bg=Constants.white, anchor='center')
        self.InfoLabel4.place(x=115, y=470, width=575)

        self.ReScanButton = Button(InfoFrame, text='Rescan', font=self.medium0_5_font, state='normal',
                                   command=self.RescanButtonCallback, bg='#C4F1F9', highlightbackground='#065666',
                                   highlightthickness=1, anchor='center')
        self.ReScanButton.place(x=0, y=0, width=0, height=0)  # Hide the Rescan button

        # ################################# SubInfo Frame ################################
        self.CartonInfo = Label(SubInfoFrame, text='Carton Info', font=self.medium1_bold_font,
                                fg='#1A365D', bg=Constants.white)
        self.CartonInfo.place(x=715, y=90)
        self.CartonWeightLabel = Label(SubInfoFrame, text='Carton Weight', font=self.medium1_font, fg='#1A365D',
                                       bg=Constants.white)
        self.CartonWeightLabel.place(x=715, y=155)
        self.CartonWeight = Label(SubInfoFrame, font=self.medium1_italic_font, fg='#0A365D', bg=Constants.white)
        self.CartonWeight.place(x=810, y=195)
        self.CartonBarcodeLabel = Label(SubInfoFrame, text='Carton code', font=self.medium1_font, fg='#1A365D',
                                        bg=Constants.white)
        self.CartonBarcodeLabel.place(x=715, y=240)
        self.CartonBarcode = Label(SubInfoFrame, font=self.medium1_italic_font, fg='#0A365D', bg=Constants.white)
        self.CartonBarcode.place(x=810, y=280)
        self.ScannedPieces = Label(SubInfoFrame, text='Scanned Pieces', font=self.medium1_font, fg='#1A365D',
                                   bg=Constants.white)
        self.ScannedPieces.place(x=715, y=325)
        self.ScannedPieceCount = Label(SubInfoFrame, font=self.medium1_italic_font, fg='#0A365D', bg=Constants.white )
        self.ScannedPieceCount.place(x=810, y=365)

        # Software loop
        self.MainWindow.resizable(width=False, height=False)  # No resize

        # Update status message box
        self.updateWeightStatus()
        self.updateBarcodeStatus()
        self.updateRFIDReaderStatus()
        self.updateAntennaStatus()

        # Main software loop
        self.MainWindow.mainloop()

        self.processState = 'Exit'

        # Close RFID connection
        self.rfidReader.closeConnection()

        restartScript = None
        try:
            # Restart script is executed after closing the tkinter window is closed
            restartScript = self.configFile['File']['RestartScript']
            self.logger.debug('Executing restartScript:%s', restartScript)
            os.system(restartScript)
        except:
            self.logger.error('Error in executing stop script:%s', restartScript)

        sys.exit(0)


# ############## End of NewUI ################################

# Main program
def main():
    if len(sys.argv) != 2:
        print('Usage: python ', sys.argv[0], ' <Configuration Filename>')
        sys.exit(2)

    configFilename = sys.argv[1]

    if not os.path.exists(configFilename):
        print('Configuration file does not exists:', configFilename)
        sys.exit()

    ''' Load the configuration '''
    config = configparser.ConfigParser()

    try:
        config.read(configFilename)
    except configparser.Error as error:
        print('Error occurred while running the code:' + str(error))
        sys.exit(10)

    vRFIDUI = RFIDUI(config)

    try:
        vRFIDUI.mainMethod()
    except Exception as error:
        print('Error: ' + str(error))


if __name__ == '__main__':
    main()
