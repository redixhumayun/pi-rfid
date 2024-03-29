from enum import Enum, unique

@unique
class TagReaderEnums(Enum):
  START_READING_TAGS = 'start reading tags'
  DONE_READING_TAGS = 'done reading tags'
  RECEIVED_CARTON_BARCODE_VALUE = 'received carton barcode value'
  CLEAR_TAG_DATA = 'clear tag data'
  GET_CARTON_TYPE = 'get carton type'
