from enum import Enum, unique

@unique
class DisplayEnums(Enum):
    """
    This class is used to enumerate the different display options
    """
    SCAN = 'scan'
    UPLOAD = 'upload'
    UPLOAD_SUCCESS = 'upload success'
    UPLOAD_FAIL = 'upload fail'
    SHOW_SCANNED_BARCODE = 'show scanned barcode'
    SHOW_WEIGHT = 'show weight'
    SHOW_NUMBER_OF_TAGS_AND_CARTON_TYPE = 'show number of tags and carton type'    
    QUIT = 'quit'
