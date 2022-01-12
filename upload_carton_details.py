import logging
from os import path

from make_api_request import MakeApiRequest
from exceptions import ApiError

logger = logging.getLogger('upload_carton_details')
api_request = MakeApiRequest('/fabship/product/rfid')

def upload_carton_details(list_of_epc_tags, carton_weight, carton_code, carton_barcode, carton_pack_type, shipment_id) -> bool:
    logger.log(logging.DEBUG, f"Received the following tags to upload: {list_of_epc_tags}")
    # Read the location from the relevant file
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    try:
        logger.log(
            logging.DEBUG, "Trying to read the location before uploading tags")
        with open(filename, 'r') as f:
            location = f.readline()
    except FileNotFoundError as err:
        logger.log(
            logging.ERROR, "Could not find the location.txt file to read from")
        raise err
    # Make the API request
    try:
        logger.log(logging.DEBUG, "Making a POST request")
        response = api_request.post(
            {
                'location': 'IDU1', #   only while testing against prod 
                'epcs': list_of_epc_tags,
                'shipmentId': str(shipment_id),
                'cartonCode': carton_code,
                'cartonBarcode': carton_barcode,
                'cartonWeight': carton_weight,
                'packType': carton_pack_type
            }
        )
        logger.log(logging.DEBUG,
                    f"Received the following response: {response}")
        return True
    except ApiError as err:
        logger.log(logging.ERROR,
                    f"Error raised while uploading tags: {err.message}")
        return err.message