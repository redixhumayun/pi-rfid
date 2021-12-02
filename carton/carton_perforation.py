from enum import Enum, auto, unique

@unique
class CartonPerforation(Enum):
  """
  This class denotes the types of perforations for cartons
  """
  PERFORATED = 'perforated'
  NONPERFORATED = 'nonperforated'