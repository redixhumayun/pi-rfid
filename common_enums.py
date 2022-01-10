from enum import Enum, unique

@unique
class CommonEnums(Enum):
    API_PROCESSING = 'api processing'
    API_COMPLETED = 'api completed'
    API_ERROR = 'api error'
