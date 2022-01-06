from enum import Enum, unique

@unique
class BarcodeScannerEnums(Enum):
  CARTON_BARCODE_SCAN_VALUE = 'carton barcode scan value'
  BARCODE_DECODE_ERROR = 'barcode decode error'
  BARCODE_SCANNER_PERMISSION_ERROR = 'barcode scanner permission error'
  API_PROCESSING = 'api processing'
  API_COMPLETED = 'api completed'