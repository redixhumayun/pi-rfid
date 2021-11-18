import serial

def weighing_scale_test():
  try:
    serial_device_1 = serial.Serial('/dev/ttyUSB0', 9600, timeout=0.5)
  except serial.serialutil.SerialException as err:
    raise err
  
  while True:
    bytes = serial_device_1.readline()
    print(bytes)
    print(bytes.decode('ascii'))

if __name__ == "__main__":
  print("Running")
  weighing_scale_test()