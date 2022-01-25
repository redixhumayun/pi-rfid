import serial

def run_test():
    try:
        serial_device = serial.Serial(
            '/dev/weighing-scale', 9600, timeout=0.5
        )
    except serial.serialutil.SerialException as err:
        print("There was a problem opening the weighing scale port")
        raise err

    try:
        serial_device.reset_input_buffer()
        while True:
            weight_in_bytes = serial_device.read()
            weight_as_string = weight_in_bytes.decode('ascii')
            print(f"Reading the weight as string as: {weight_as_string}")
            try:
                weight = float(weight_as_string)
                print(f"Reading the weight as float as: {weight}")
            except ValueError as err:
                #   Not reading this data because the scale is calibrating
                pass
    except KeyboardInterrupt:
        print("Received keyboard interrupt in weighing scale test. Closing the port and exiting the program")
        serial_device.close()

if __name__ == "__main__":
    run_test()