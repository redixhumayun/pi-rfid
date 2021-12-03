from enum import Enum, unique

@unique
class BarcodeScannerEnums(Enum):
  SEND_VALUE_TO_MAIN_PROCESS = 'send value to main process'
  SENDING_WEIGHT_VALUE_TO_MAIN_PROCESS = 'sending weight value to main process'