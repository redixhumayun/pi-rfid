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

