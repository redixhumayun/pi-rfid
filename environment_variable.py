from enum import Enum, auto, unique

@unique
class EnvironmentVariable(Enum):
  PRODUCTION = 'production'
  DEVELOPMENT = 'development'