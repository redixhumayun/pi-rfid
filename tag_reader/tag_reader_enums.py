from enum import Enum, unique

@unique
class TagReaderEnums(Enum):
  START_READING_TAGS = 'start reading tags'
  DONE_READING_TAGS = 'done reading tags'
  CLEAR_TAG_DATA = 'clear tag data'