import requests

class MakeApiRequest():
  headers = { 'version': '3.0' }

  def __init__(self, url):
    self.url = url
    self.headers = { 'version': '3.0' }

  @staticmethod
  def add_authentication_header(token):
    MakeApiRequest.headers['Authorization'] = f'Bearer {token}'

  # def add_authentication_header(self, token):
  #   self.headers['Authorization'] = f'Bearer {token}'

  def get(self, data={}):
    try:
      print(MakeApiRequest.headers)
      response = requests.get(self.url, params=data, headers=MakeApiRequest.headers)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      print(f"The GET request failed with the status code: {err}")
      raise err
  
  def post(self, data):
    try:
      response = requests.post(self.url, json=data, headers=MakeApiRequest.headers)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      # print(f"The POST request failed with the status code: {err}")
      print(err)
      raise err