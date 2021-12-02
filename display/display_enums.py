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
    SHOW_SCAN_DATA = 'show scan data'
    QUIT = 'quit'
