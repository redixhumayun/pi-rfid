import requests

"""
This class will be used to construct and carry out API requests.
"""
class MakeApiRequest():
  # This will be a static variable for this class
  headers = {'version': '3.0'}

  def __init__(self, url: str):
    self.url = url

  @staticmethod
  def add_authentication_header(token: str) -> None:
    MakeApiRequest.headers['Authorization'] = f'Bearer {token}'

  def get(self, data: dict = {}):
    """Makes a GET method API request"""
    try:
      print(MakeApiRequest.headers)
      response = requests.get(self.url, params=data, headers=MakeApiRequest.headers)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      print(err)
      raise err
  
  def post(self, data: dict):
    """Makes a POST method API request"""
    try:
      response = requests.post(self.url, json=data, headers=MakeApiRequest.headers)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      print(err)
      raise err
