import serial
import sys

def convert_tag_from_bytes_to_hex(tag_bytes_list):
    tag_hex_value = ""
    for index, bytes_value in enumerate(tag_bytes_list):
        #   First 3 bytes and last byte are placeholders
        if index > 3 and index < 16:
            tag_hex_value += "{0:02X}".format(bytes_value)

    return tag_hex_value

def run_test():
    tag_bytes_list_for_device_1 = []
    tag_bytes_list_for_device_2 = []

    tag_hex_value_list = []

    should_read_tag_from_device_1 = False
    should_read_tag_from_device_2 = False
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
        serial_device_1.reset_input_buffer()
        serial_device_2.reset_input_buffer()
        while True:
            read_bytes_from_device_1 = serial_device_1.read()
            int_value_from_device_1 = int.from_bytes(
                read_bytes_from_device_1, "big")
            print(int_value_from_device_1)
            read_bytes_from_device_2 = serial_device_2.read()
            int_value_from_device_2 = int.from_bytes(
                read_bytes_from_device_2, "big"
            )
            sys.stdout.flush()

            if int_value_from_device_1 == 0x11:
                should_read_tag_from_device_1 = True

            if should_read_tag_from_device_1 is True:
                tag_bytes_list_for_device_1.append(int_value_from_device_1)

                if len(tag_bytes_list_for_device_1) == 18:
                    should_read_tag_from_device_1 = False
                    tag_hex_value = convert_tag_from_bytes_to_hex(tag_bytes_list_for_device_1)
                    if tag_hex_value not in tag_hex_value_list:
                        tag_hex_value_list.append(tag_hex_value)
                    tag_bytes_list_for_device_1.clear()

            if should_read_tag_from_device_2 is True:
                tag_bytes_list_for_device_2.append(int_value_from_device_2)

                if len(tag_bytes_list_for_device_2) == 18:
                    should_read_tag_from_device_2 = True
                    tag_hex_value = convert_tag_from_bytes_to_hex(tag_bytes_list_for_device_2)
                    if tag_hex_value not in tag_hex_value_list:
                        tag_hex_value_list.append(tag_hex_value)
                    tag_bytes_list_for_device_2.clear()

            print(f"Tag list: {tag_hex_value_list}")
                    
    except KeyboardInterrupt:
        print("Received keyboard interrupt in the RFID reader test program. Closing the ports and exiting the program")
        serial_device_1.flush()
        serial_device_1.reset_input_buffer()
        serial_device_1.close()

        serial_device_2.flush()
        serial_device_2.reset_input_buffer()
        serial_device_2.close()

        sys.exit(0)

if __name__ == "__main__":
    run_test()