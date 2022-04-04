import configparser

import requests
import logging
import json
from exceptions import ApiError
import logging.config

"""
This class will be used to construct and carry out API requests.
"""


class MakeApiRequest:

    # This will be a static variable for this class
    headers = {'version': '6.0'}

    def __init__(self, configFile: configparser.ConfigParser(), url: str):

        self.configFile = configFile
        self.api_url = self.configFile['RestAPI']['APIURL']
        self.client_id = self.configFile['RestAPI']['ClientId']
        self.client_secret = self.configFile['RestAPI']['ClientSecret']
        self.audience = self.configFile['RestAPI']['Audience']
        self.grant_type = self.configFile['RestAPI']['GrantType']
        self.auth0_domain = self.configFile['RestAPI']['Auth0Domain']
        self.url = f"{self.api_url}{url}"

        # Load the logger configuration
        logging.config.fileConfig(fname=self.configFile['File']['LoggerConfig'], disable_existing_loggers=False)
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def add_authentication_header(token: str) -> None:
        MakeApiRequest.headers['Authorization'] = f'Bearer {token}'

    def get_authentication_token(self):
        """Will fetch a new authentication token using client credentials and update
        the headers dict"""
        try:
            self.logger.debug("Making a request to get the authentication token")
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'audience': self.audience,
                'grant_type': self.grant_type
            }
            response = requests.post(f"{self.auth0_domain}", json=payload)
            parsed_response = response.json()
            access_token = parsed_response['access_token']
            self.logger.debug("Got the authentication token")
            MakeApiRequest.add_authentication_header(access_token)
            return
        except Exception as err:
            raise err

    def retry_request(self, method, payload):
        if method == 'GET':
            return self.get(payload)
        elif method == 'POST':
            return self.post(payload)
        elif method == 'GET_WITH_BODY':
            return self.get_request_with_body(payload)

    def authenticate_and_retry_request(self, method, payload):
        """Will re-fetch the token and then retry the request"""
        try:
            self.get_authentication_token()
            return self.retry_request(method, payload)
        except Exception as err:
            raise err

    def get(self, data: dict = {}):
        """Makes a GET method API request"""
        try:
            self.logger.debug(f"Making a GET request with the following data: {data} to the following endpoint: {self.url}")
            response = requests.get(self.url, params=data, headers=MakeApiRequest.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                self.logger.error("There was a 401 authentication error while making the GET request. Application will fetch a new token and retry the request")
                return self.authenticate_and_retry_request('GET', data)
            else:
                error_response = json.loads(err.response.text)
                error_message = error_response['message']
                self.logger.error(f"There was an error while making the GET request: {error_message}")
                raise ApiError(error_message) from err

        except requests.exceptions.MissingSchema as err:
            self.logger.error(f"There was an error while making the GET request: {err}")
            raise ApiError(err)

    def post(self, data: dict):
        """Makes a POST method API request"""
        try:
            self.logger.debug(f"Making a POST request with the following data: {data} to the following endpoint: {self.url}")
            response = requests.post(self.url, json=data, headers=MakeApiRequest.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                self.logger.error("There was a 401 authentication error while making the POST request. Application will fetch a new token and retry the request")
                return self.authenticate_and_retry_request('POST', data)
            else:
                error_response = json.loads(err.response.text)
                error_message = error_response['message']
                self.logger.error(f"There was an error while making the POST request: {error_message}")
                raise ApiError(error_message) from err

        except requests.exceptions.MissingSchema as err:
            self.logger.error(f"There was an error while making the POST request: {err}")
            raise ApiError(err)

    def get_request_with_body(self, data: dict = {}):
        """Makes a GET method API request with the body attached"""
        try:
            self.logger.debug(f"Making a GET request with the following data: {data} attached to the body to the following endpoint: {self.url}")
            response = requests.request(method='get', url=self.url, data=data, headers=MakeApiRequest.headers)
            response.raise_for_status()
            print(response.json())
            return response.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                self.logger.error("There was a 401 authentication error while making the GET request with a body. Application will fetch a new token and retry the request")
                return self.authenticate_and_retry_request('GET_WITH_BODY', data)
            else:
                error_response = json.loads(err.response.text)
                error_message = error_response['message']
                self.logger.error(f"There was an error while making the GET request with a body: {error_message}")
                raise ApiError(error_message) from err

        except requests.exceptions.MissingSchema as err:
            self.logger.error(f"There was an error while making the GET request with a body: {err}")
            raise ApiError(err)
