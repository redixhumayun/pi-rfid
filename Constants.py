
usbPortOpenError = "Unable to open Barcode USB device:"
permissionError = "There was an error while opening the barcode scanner reader:"

# Weighing Scale error
serialPortOpenError = "Weighing scale is not connected to Serial port:"
weighingScaleIsOff = "Serial port is disconnected or Weighing machine is off or weight is unstable"
noItemPlaceOnWeighingScale = "No item is placed on Weighing machine is off"
serialPortTimeoutError = "Serial port read timeout error:"

# RFID Reader error
rfidReaderConnectError = "Error in connecting to RFID Reader:"
rfidListenerError = "Error in starting RFID Listener:"
rfidCloseConnectError = "Error in closing RFID Reader Connection:"
rfidOpenConnectError = "Error in opening RFID Reader Connection:"

# Error Status
weighingScaleInfoStatus = 'Connected    '
weighingScaleErrorStatus = 'Disconnected  '
barcodeInfoStatus = 'Connected    '
barcodeErrorStatus = 'Disconnected  '
rfidReaderInfoStatus = 'Connected    '
rfidReaderErrorStatus = 'Disconnected  '

# Refresh after milliseconds
RefreshStatusMilliSeconds = 6000
RefreshRFIDCount = 250

# Color Code
green = '#12AD2B'
red = '#B00020'
white = '#ffffff'
cyan = '#065666'
black = '#000000'

"""
This denotes the types of perforations for cartons
"""
PERFORATED = 'perforated'
NONPERFORATED = 'nonperforated'

"""
This is used to enumerate the different types of cartons
"""
ASSORTED = 'assorted'
SOLID = 'solid'
MIXED = 'mixed'