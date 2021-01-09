from enum import Enum, auto, unique

@unique
class EnvironmentVariable(Enum):
  """
  This class is used to enumerate the different possible environments
  the program must run in
  """
  PRODUCTION = 'production'
  DEVELOPMENT = 'development'