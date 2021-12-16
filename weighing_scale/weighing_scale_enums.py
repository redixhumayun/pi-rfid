from enum import Enum, unique

@unique
class WeighingScaleEnums(Enum):
  START_WEIGHING = 'start weighing'
  WEIGHT_VALUE_READ = 'weight_value_read'