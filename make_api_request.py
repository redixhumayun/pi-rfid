import requests

class MakeApiRequest():
  def __init__(self, url):
    self.url = url

  def get(self, data={}):
    try:
      response = requests.get(self.url, params=data)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      print(f"The GET request failed with the status code: {err}")
      raise err
  
  def post(self, data):
    try:
      response = requests.post(self.url, json=data)
      response.raise_for_status()
      return response.json()
    except requests.exceptions.HTTPError as err:
      # print(f"The POST request failed with the status code: {err}")
      print(err)
      raise err