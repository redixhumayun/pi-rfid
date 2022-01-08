from enum import Enum, unique

@unique
class BarcodeScannerEnums(Enum):
  CARTON_BARCODE_SCAN_VALUE = 'carton barcode scan value'
  BARCODE_SCANNER_PERMISSION_ERROR = 'barcode scanner permission error'
