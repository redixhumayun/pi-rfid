import logging

from carton.decide_carton_type import get_carton_perforation, decide_carton_type
from make_api_request import MakeApiRequest
from exceptions import ApiError, UnknownCartonTypeError

def decode_epc_tags_into_product_details(list_of_epcs):
    """
    This method is responsible for converting the EPC into product details via API request
    """
    api_request = MakeApiRequest('/fabship/product/rfid')
    decoded_product_details = None
    try:
        decoded_product_details = api_request.get_request_with_body(
            { 'epc': list_of_epcs }
        )
        return decoded_product_details
    except ApiError as err:
        raise err

def get_carton_pack_type(product_details, carton_barcode):
    """
    This method is responsible for getting the carton type based on the product details
    """
    carton_perforation = get_carton_perforation(carton_barcode)
    try:
        carton_type = decide_carton_type(
            product_details, carton_perforation
        )
        return carton_type
    except UnknownCartonTypeError as err:
        raise err
