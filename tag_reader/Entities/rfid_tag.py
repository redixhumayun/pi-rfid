class RFIDTagEntity():
    def __init__(self):
        self.allowed_company_prefixes = [731422, 731430]
        self.allowed_header = 48

    def convert_tag_from_bytes_to_hex(self, tag_bytes_list) -> str:
        tag_hex_value = ""
        for index, bytes_value in enumerate(tag_bytes_list):
            #   First 3 bytes and last byte are placeholders
            if index > 3 and index < 16:
                tag_hex_value += "{0:02X}".format(bytes_value)

        return tag_hex_value

    def is_tag_valid(self, tag_hex_value) -> bool:
        #   This line converts from hex -> int -> bin, removes the 0b at the beginning and then zfills to get 96 bits
        binary_tag_value: str = bin(int(tag_hex_value, 16))[2:].zfill(96)

        binary_header: str = binary_tag_value[0:8]
        binary_company_prefix: str = binary_tag_value[14:34]

        header: int = int(binary_header, 2)
        company_prefix: int = int(binary_company_prefix, 2)

        #   All SGTIN values have an 8-bit header corresponding to 48
        if header != self.allowed_header:
            return False

        if company_prefix not in self.allowed_company_prefixes:
            return False

        return True