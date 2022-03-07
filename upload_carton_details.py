import logging

from make_api_request import MakeApiRequest
from exceptions import ApiError

logger = logging.getLogger('upload_carton_details')
api_request = MakeApiRequest('/fabship/product/rfid')

def upload_carton_details(location, list_of_epc_tags, carton_weight, carton_code, carton_barcode, carton_pack_type, shipment_id) -> bool:
    """This method is used to upload the details associated with a carton"""
    logger.log(logging.DEBUG, f"Received the following tags to upload: {list_of_epc_tags}")

    # Make the API request
    try:
        logger.log(logging.DEBUG, "Making a POST request")
        response = api_request.post(
            {
                'location': location,
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
        raise err