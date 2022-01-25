import serial
import sys

def run_test():
    try:
        serial_device_1 = serial.Serial(
            '/dev/rfid-reader-1', 57600, timeout=0.5
        )
        serial_device_2 = serial.Serial(
            '/dev/rfid-reader-2', 57600, timeout=0.5
        )
    except serial.serialutil.SerialException as err:
        print('There was a problem while opening the ports for the reader')
        raise err

    try:
        while True:
            serial_device_1.reset_input_buffer()
            serial_device_2.reset_input_buffer()
            
            read_bytes_from_device_1 = serial_device_1.read()
            int_value_from_device_1 = int.from_bytes(
                read_bytes_from_device_1, "big")
            read_bytes_from_device_2 = serial_device_2.read()
            int_value_from_device_2 = int.from_bytes(
                read_bytes_from_device_2, "big"
            )
            sys.stdout.flush()
            print(f"Value from device 1: {int_value_from_device_1}")
            print(f"Value from device 2: {int_value_from_device_2}")
    except KeyboardInterrupt:
        print("Received keyboard interrupt. Closing the ports and exiting the program")
        serial_device_1.close()
        serial_device_2.close()

if __name__ == "__main__":
    run_test()