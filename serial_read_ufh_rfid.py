#!/usr/bin/python3
import serial
import sys
import os
import requests
from dotenv import load_dotenv

from make_api_request import MakeApiRequest

load_dotenv()

ps=0
cnt=0
tagid=[]

Alltags=[]

def pr_tagid():
    taghex=""
    a=len(tagid)
    for i in range(a):
        if i >3 and i < 16:
            taghex+="{0:02X}".format(tagid[i])

    if taghex not in Alltags:
        Alltags.append(taghex)
        print(taghex,": Added")

ser=serial.Serial('/dev/ttyUSB0', 57600,timeout=1)

while True:
    x = ser.read()
    i=int.from_bytes(x,"big")
    sys.stdout.flush()
    if i == 0x11:
        ps=1
        cnt=0
    if ps:
        tagid.append(i)
        cnt +=1
        if cnt == 18:
            cnt=0
            ps=0
            pr_tagid()
            tagid.clear()


#   Documentation around making an API call

#   Load all the env variables
api_url = os.getenv("SERVER_BASE_URL")
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
audience = os.getenv("AUDIENCE")
grant_type = os.getenv("GRANT_TYPE")
auth0_domain = os.getenv("AUTH0_DOMAIN")

#   First create a payload and make a request to get the authentication token
api_request = MakeApiRequest(f"{auth0_domain}")
payload = {'client_id': client_id, 'client_secret': client_secret,
           'audience': audience, 'grant_type': grant_type}
response = api_request.post(payload)
access_token = response['access_token']
MakeApiRequest.add_authentication_header(access_token)

#   Validate the location
#   The location will be passed in from the GPS encoder
api_request = MakeApiRequest(f"{api_url}/rfid/location/validate")
payload = {'latitude': 13.03278000, 'longitude': 77.62371000}
response = api_request.get(payload)
location = response[0]
print(location)

#   Send the list of EPC tags along with the location
api_request = MakeApiRequest(f"{api_url}/rfid/epc")
epc = ['12tu12un1i2gn12', '2o1un2821gh912g', '2g9128129g8h129g']
payload = {'location': location, 'epc': epc}
response = api_request.post(payload)
print(response)