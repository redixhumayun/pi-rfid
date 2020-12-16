#!/usr/bin/python3
from os import path
from multiprocessing import Process, Queue
import random
import time
import serial
import pynmea2
import sys
import requests
import json
import tkinter as tk
from tkinter import ttk

from make_api_request import MakeApiRequest
#########################################################################

ps = 0
cnt = 0
tagid = []

Alltags = []
sttime = 0
prevtime = 0


def pr_tagid(que, ss):
    global sttime, prevtime
    taghex = ""

    sttime = time.time()
    a = len(tagid)
    for i in range(a):
        if i > 3 and i < 16:
            taghex += "{0:02X}".format(tagid[i])
        #print(hex(tagid[i]),end=" ")

    if taghex not in Alltags:
        Alltags.append(taghex)
        print(taghex, ": Added")

    if ss == 1:
        if sttime - prevtime > 1.0:
            print("Sending all tags")
            lentag = len(Alltags)
            S = str(lentag)+" "
            if lentag > 0:
                for i in range(lentag):
                    S += (Alltags[i]+" ")

            que.put("TAG "+S)
            prevtime = sttime


# This function is used to read the tags from the RFID reader plugged in via USB
def tagreader_proc(x, queue, rq):
    global ps
    sstop = 0
    trq = rq
    S = ""

    ser = serial.Serial('/dev/ttyUSB0', 57600, timeout=0.5)

    while True:
        x = ser.read()
        i = int.from_bytes(x, "big")
        #print(hex(i), end=" ")
        sys.stdout.flush()
        if not trq.empty():
            arq = trq.get()
            if arq == "start":
                print("setting sstop")
                sstop = 1
               # if len(Alltags) == 0:
               #     queue.put("TAG: 0")
                Alltags.clear()
            else:
                sstop = 0
                Alltags.clear()

        if i == 0x11:
            ps = 1
            cnt = 0
        if ps:
            tagid.append(i)
            cnt += 1
            if cnt == 18:
                cnt = 0
                ps = 0
                pr_tagid(queue, sstop)
                tagid.clear()


#########################################################################
def upload_proc(x, queue, rq):
    trq = rq
    while True:
        if not trq.empty():
            arq = trq.get()
            print("------------Upload Process Ret:", arq)
            url = 'http://eetrax.com/json_my/jd2.php'
            payload = arq
            try:
                r = requests.post(url, json=payload, timeout=4)
                if r.status_code == 200:
                    queue.put("UP_SUCCESS")
                else:
                    queue.put("UP_FAIL")
            except Exception as err:
                print(err)
                queue.put("UP_FAIL")
            else:
                print(r)


#########################################################################

# Reading from the GPS doesn't need to be a process. No idea why this has been turned into a process
# This just needs to be read once when the program first boots
# def gps_proc(x,queue,rq):
#     sstop=0
#     trq=rq
#     S=""
#     ser=serial.Serial('/dev/ttyACM0', 9600,timeout=1)

#     while True:
#         try:
#             x = ser.readline()
#             y=x[:-2].decode("utf-8")
#             if  y.find("RMC") > 0:
#                 msg = pynmea2.parse(str(y))
#                 S="GPS " +"{:.2f}".format(msg.latitude)+" "+"{:.2f}".format(msg.longitude)

#                 if sstop ==1:
#                    queue.put(S)
#             if not trq.empty():
#                 arq=trq.get()
#                 print("Gps Process Ret:",arq)
#                 if arq == "start":
#                     sstop=1
#                 else:
#                     sstop=0


#         except Exception as e:
#             print("GPS Excepton caught",e)


# This function is apparently just generating random numbers
# and not doing anything else. No idea why this is in here

# def rand_num(x,queue,rq):
#     sstop=0
#     trq=-1
#     if x == 0:
#         trq= rq1
#     elif x == 1:
#         trq=rq2
#     elif x == 2:
#         trq=rq3

#     while True:
#         num = random.random()
#         S=str(x)+" "+str(num)
#         if not trq.empty():
#             arq=trq.get()
#             print("Process Ret:",x,arq)
#             if arq == "start":
#                 sstop=1
#             else:
#                 sstop=0
#         if sstop ==1:
#             queue.put(S)
#         #time.sleep(random.randint(1,10))
#         time.sleep(1)


###########################################################

canvas_width = 800
canvas_height = 450
scan = 0
dvar = -1

tk_wq = ""
tk_sq = ""
master = ""
canvas = -1
upvar = -1


def scan():
    global scan
    scan = 1


def upload():
    global upvar
    upvar = 1


def tloop():
    global scan, canvas, dvar, tk_wq, tk_sq, master, upvar
    if scan == 1:
        scan = 0
        if dvar > -1:
            jj = canvas.delete("cantext")
            master.update()
            print("Ret Dvar", dvar, jj)
        tk_wq.put("TKFE_SCAN")
    if upvar == 1:
        upvar = 0
        if dvar > -1:
            jj = canvas.delete("cantext")
            master.update()
            print("Up Dvar", dvar, jj)
        tk_wq.put("TKFE_UPLOAD")

    if not tk_sq.empty():
        arq = tk_sq.get()
        print("TK Process Ret:", arq)
        if dvar > -1:
            jj = canvas.delete("cantext")
            master.update()
        dvar = canvas.create_text(320, 200, fill="Black", anchor=tk.NW,
                                  font="Helvetica 80 bold", text=str(arq), tag="cantext")
        master.update()

    master.after(300, tloop)

# This function will run the TKinter GUI as a process


def gui_bk_proc(x, queue, rq):
    global tk_wq, tk_sq, master, canvas
    tk_wq = queue
    tk_sq = rq
    master = tk.Tk()

    canvas = tk.Canvas(master, bg="white",
                       width=canvas_width,
                       height=canvas_height)
    canvas.pack(side=tk.TOP)
    # bk = tk.PhotoImage(file="rfid-bk.png")
    # bkimg=canvas.create_image(0,0, anchor=tk.NW, image=bk)
    master.update()
    b_scan = tk.Button(master, text="Scan", command=scan)
    b_scan.pack(side=tk.RIGHT)
    b_up = tk.Button(master, text="Upload", command=upload)
    b_up.pack(side=tk.RIGHT)
    master.after(900, tloop)
    tk.mainloop()

class DisplayTagIdGUI(Process):
  """
  This class is used to create a GUI that will be used to display the list of tags that
  are being read from the USB device
  """

  def __init__(self, queue: list):
    Process.__init__(self)
    self.queue = queue

  def scan(self):
    print("Scan")
  
  def upload(self):
    print("Upload")

  def run_loop(self):
    pass

  def run(self):
    self.root = tk.Tk()
    self.canvas = tk.Canvas(self.root, bg="white",
                            width=800,
                            height=450)
    self.canvas.pack(side=tk.TOP)
    scan_button = ttk.Button(self.root, text="Scan", command=self.scan)
    upload_button = ttk.Button(self.root, text="Upload", command=self.upload)
    scan_button.pack(side=tk.RIGHT)
    upload_button.pack(side=tk.RIGHT)
    self.root.after(900, self.run_loop)
    tk.mainloop()
    

class SelectLocationGUI(Process):
  """
  This class is used to create a GUI that will be used to display the list of possible locations to the user
  and allow the user to select a location
  """

  def __init__(self, queue: list):
    Process.__init__(self)
    print(queue)
    self.queue = queue
    self.possible_locations = None
    self.buttons = {}

  def command(self, loc: str):
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    with open(filename, 'w+') as f:
      f.write(loc)
    self.root.destroy()

  def run(self):
    while self.possible_locations is None:
      self.possible_locations = self.queue.get()
    self.root = tk.Tk()
    self.canvas = tk.Canvas(master, bg="white",
                            width=canvas_width,
                            height=canvas_height)
    for location in self.possible_locations:
      key = f"button_{location}"
      self.buttons[key] = ttk.Button(
          self.root, text=location, command=lambda loc=location: self.command(loc))
      self.buttons[key].pack(side=tk.TOP)
    tk.mainloop()

###########################################################

# This function is used to call the GPS device attached via USB
# and fetch the latitude and longitude


def get_latitude_and_longitude(gps_child_queue):
  time_end = time.time() + 5

  #   Read from the GPS device for 30 seconds
  # serial_device = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
  # while time.time() < 30:
  #   x = serial_device.readline()
  #   y = x[:-2].decode('utf-8')
  #   if y.find("RMC") > 0:
  #     message = pynmea2.parse(str(y))
  #     latitude = message.latitude
  #     longitude = message.longitude

  # gps_child_queue.put({ latitude: latitude, longitude: longitude })

  #   Use this for testing
  while time.time() < time_end:
    latitude = 13.02518000
    longitude = 77.63192000
  gps_child_queue.put({'latitude': latitude, 'longitude': longitude})


def get_location(location_object):
  try:
    api_request = MakeApiRequest('/service/validate/locations')
    payload = {
        'latitude': location_object['latitude'], 'longitude': location_object['longitude']}
    response = api_request.get(payload)
    return response
  except Exception as err:
    print("Sorry, there was an error while fetching the location. Please try again")
    print(err)


if __name__ == "__main__":
  # wq = Queue()
  # rq1= Queue()  #There is no need for the random number queue
  # rq2= Queue()  #There is no need for the random number queue
  # gpsq= Queue() #There is no need for the GPS queue
  # tagq= Queue()
  # guibq= Queue()
  # uploadq= Queue()

  # This variable will determine whether the location should be checked or not
  should_check_location = False

  # First, check if there is a location file which has been written to
  # If there is no file with location saved, fire up GPS device and fetch latitude & longitude
  # Then allow user to select the correct location
  dirname = path.dirname(__file__)
  filename = path.join(dirname, 'location.txt')
  try:
    with open(filename, 'r') as f:
      location = f.readline()
  except FileNotFoundError:
    should_check_location = True

  # Define a list to hold all the process references
  processes = []

  # Start GPS process and allow user to select location only if
  # locatio has not already been set
  if should_check_location is True:
    select_location_gui_queue = Queue()
    select_location_gui_process = SelectLocationGUI(select_location_gui_queue)
    gps_queue = Queue()
    gps_process = Process(
        target=get_latitude_and_longitude, args=(gps_queue,))
    processes.append(gps_process)
    processes.append(select_location_gui_process)

    # display_tag_id_gui_queue = Queue()
    # display_tag_id_gui_process = DisplayTagIdGUI(display_tag_id_gui_queue)
    # processes.append(display_tag_id_gui_process)

    # Start the processes
    for process in processes:
      process.start()

    # Pass data between the various processes
    location_data = gps_queue.get()
    possible_locations = get_location(location_data)
    select_location_gui_queue.put(possible_locations)

    # Clear the process list
    processes.clear()

  display_tag_id_gui_queue = Queue()
  display_tag_id_gui_process = DisplayTagIdGUI(display_tag_id_gui_queue)
  processes.append(display_tag_id_gui_process)

  for process in processes:
    process.start()
    process.join()






    # a=Process(target=rand_num, args=(0,wq,rq1))
    # b=Process(target=rand_num, args=(1,wq,rq2))
    # c=Process(target=gps_proc, args=(2,wq,gpsq))
    # d=Process(target=tagreader_proc,args=(3,wq,tagq))
    # e=Process(target=gui_bk_proc,args=(4,wq,guibq))
    # f=Process(target=upload_proc,args=(5,wq,uploadq))
    # processes.append(a)
    # processes.append(b)
    # processes.append(c)
    # processes.append(d)
    # processes.append(e)
    # processes.append(f)

    # for p in processes:
    #     p.start()

    # cnt=1
    # sent="end"
    # tagstr=""
    # gpsstr=""
    # gpsdict={}
    # tagdict={}
    # while True:
    #     try:
    #         for p in processes:
    #             if not wq.empty():
    #                 rq=wq.get()
    #                 print("ML Ret:",rq)
    #             #     if rq == "TKFE_SCAN":
    #             #         rq1.put("start")
    #             #         rq2.put("start")
    #             #         gpsq.put("start")
    #             #         tagq.put("start")
    #             #     elif rq == "TKFE_UPLOAD":
    #             #         rq1.put("end")
    #             #         rq2.put("end")
    #             #         gpsq.put("end")
    #             #         tagq.put("end")
    #             #         updict=dict({"tags":uptlist,"gps":upglist})
    #             #         uploadq.put(updict)
    #             #     elif rq == "UP_SUCCESS":
    #             #         guibq.put("Upload Sucess")
    #             #     elif rq == "UP_FAIL":
    #             #         guibq.put("Upload Failure")

    #             #     if rq.find("TAG") == 0:
    #             #         tagstr=rq
    #             #         taglist=rq.split()
    #             #         guibq.put(taglist[1])
    #             #         uptlist=taglist[2:]
    #             #     if rq.find("GPS") == 0:
    #             #         gpsstr=rq
    #             #         gpslist=rq.split()
    #             #         upglist=gpslist[1:]

    #         cnt+=1
    #         time.sleep(1)
    #     except Exception as inst:
    #         sys.exit(1)
    #         # print("Type",type(inst))    # the exception instance
    #         # print("Args",inst.args)     # arguments stored in .args
    #         # print("Inst",inst)
