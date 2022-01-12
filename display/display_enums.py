from enum import Enum, unique

@unique
class DisplayEnums(Enum):
    """
    This class is used to enumerate the different display options
    """
    SCAN = 'scan'
    GET_CARTON_TYPE = 'get carton type'
    UPLOAD = 'upload'
    UPLOAD_SUCCESS = 'upload success'
    UPLOAD_FAIL = 'upload fail'
    SHOW_SCANNED_BARCODE = 'show scanned barcode'
    SHOW_WEIGHT = 'show weight'
    SHOW_NUMBER_OF_TAGS = 'show number of tags'
    SHOW_CARTON_TYPE = 'show carton type'   
    CUSTOM_ERROR = 'custom error' 
    QUIT = 'quit'
    RESET = 'reset'
    
