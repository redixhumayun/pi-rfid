import requests
import os
from dotenv import load_dotenv

"""
This class will be used to construct and carry out API requests.
"""
class MakeApiRequest():
  # Load the env variables when this class is instantiated
  load_dotenv()

  # This will be a static variable for this class
  headers = {'version': '4.0'}

  def __init__(self, url: str):
    #   Load all the env variables
    self.api_url = os.getenv("SERVER_BASE_URL")
    self.client_id = os.getenv("CLIENT_ID")
    self.client_secret = os.getenv("CLIENT_SECRET")
    self.audience = os.getenv("AUDIENCE")
    self.grant_type = os.getenv("GRANT_TYPE")
    self.auth0_domain = os.getenv("AUTH0_DOMAIN")
    self.url = f"{self.api_url}{url}"

  @staticmethod
  def add_authentication_header(token: str) -> None:
    MakeApiRequest.headers['Authorization'] = f'Bearer {token}'

  def get_authentication_token(self):
    """Will fetch a new authentication token using client credentials and update
    the headers dict"""
    try:
      payload = {'client_id': client_id, 'client_secret': client_secret,
           'audience': audience, 'grant_type': grant_type}
      response = requests.post(f"{auth0_domain}", json=payload)
      parsed_response = response.json()
      access_token = parsed_response['access_token']
      MakeApiRequest.add_authentication_header(access_token)
      print('Got authentication token')
      return
    except Exception as err:
      raise err

  def retry_request(self, method, payload):
    if method == 'GET':
      return self.get(payload)
    elif method == 'POST':
      return self.post(payload)

  def authenticate_and_retry_request(self, method, payload):
    """Will re-fetch the token and then retry the request"""
    try:
      self.get_authentication_token()
      return self.retry_request(method, payload)
    except Exception as err:
      raise err
      
  def get(self, data: dict={}):
    """Makes a GET method API request"""
    try:
      response = requests.get(self.url, params=data, headers=MakeApiRequest.headers)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      if err.response.status_code == 401:
        return self.authenticate_and_retry_request('GET', data)
      else:
        raise err

  def post(self, data: dict):
    """Makes a POST method API request"""
    try:
      response = requests.post(self.url, json=data, headers=MakeApiRequest.headers)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      if err.response.status_code == 401:
        return self.authenticate_and_retry_request('POST', data)
      else:
        raise err
