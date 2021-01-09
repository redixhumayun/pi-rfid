from multiprocessing.queues import Queue
from os import environ
import time
import serial
import pynmea2

from make_api_request import MakeApiRequest
from environment_variable import EnvironmentVariable

# This function is used to call the GPS device attached via USB
# and fetch the latitude and longitude

def get_latitude_and_longitude(gps_child_queue: Queue, environment: str):
  # Run for at least this many number of seconds
  time_end = time.time() + 10

  # Read from the GPS device for 30 seconds
  serial_device = serial.Serial('/dev/ttyS0', 9600, timeout=1)

  # Define and set latitude and longitude
  latitude = None
  longitude = None

  # When launching with hardware devices, use this loop
  if environment == EnvironmentVariable.PRODUCTION.value:
    while time.time() < time_end:
      x = serial_device.readline()
      y = x[:-2].decode('utf-8')
      if y.find("RMC") > 0:
        message = pynmea2.parse(str(y))
        latitude = message.latitude
        longitude = message.longitude

    gps_child_queue.put({ 'latitude': latitude, 'longitude': longitude })

  # When launching without hardware devices, use this loop
  elif environment == EnvironmentVariable.DEVELOPMENT.value:
    while time.time() < time_end:
      latitude = 13.02518000
      longitude = 77.63192000
    gps_child_queue.put({'latitude': latitude, 'longitude': longitude})

# This function is used to make a call to the API to fetch the possible
# locations based on latitude and longitude
def get_location(location_object):
  try:
    api_request = MakeApiRequest('/service/validate/locations')
    payload = {
        'latitude': location_object['latitude'], 'longitude': location_object['longitude']}
    response = api_request.get(payload)
    return response
  except Exception as err:
    print("Sorry, there was an error while fetching the location. Please try again")
    print(err)