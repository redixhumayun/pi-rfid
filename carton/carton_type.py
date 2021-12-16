from enum import Enum, auto, unique

@unique
class CartonType(Enum):
  """
  This class is used to enumerate the different types of cartons
  """
  ASSORTED = 'assorted'
  SOLID = 'solid'
  MIXED = 'mixed'