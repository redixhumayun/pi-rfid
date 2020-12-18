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
from tkinter import BooleanVar, ttk, messagebox

from make_api_request import MakeApiRequest
#########################################################################

# ps = 0
# cnt = 0
# tagid = []

# Alltags = []
# sttime = 0
# prevtime = 0


# def pr_tagid(que, ss):
#     global sttime, prevtime
#     taghex = ""

#     sttime = time.time()
#     a = len(tagid)
#     for i in range(a):
#         if i > 3 and i < 16:
#             taghex += "{0:02X}".format(tagid[i])
#         #print(hex(tagid[i]),end=" ")

#     if taghex not in Alltags:
#         Alltags.append(taghex)
#         print(taghex, ": Added")

#     if ss == 1:
#         if sttime - prevtime > 1.0:
#             print("Sending all tags")
#             lentag = len(Alltags)
#             S = str(lentag)+" "
#             if lentag > 0:
#                 for i in range(lentag):
#                     S += (Alltags[i]+" ")

#             que.put("TAG "+S)
#             prevtime = sttime


# # This function is used to read the tags from the RFID reader plugged in via USB
# def tagreader_proc(x, queue, rq):
#     global ps
#     sstop = 0
#     trq = rq
#     S = ""

#     ser = serial.Serial('/dev/ttyUSB0', 57600, timeout=0.5)

#     while True:
#         x = ser.read()
#         i = int.from_bytes(x, "big")
#         #print(hex(i), end=" ")
#         sys.stdout.flush()
#         if not trq.empty():
#             arq = trq.get()
#             if arq == "start":
#                 print("setting sstop")
#                 sstop = 1
#                # if len(Alltags) == 0:
#                #     queue.put("TAG: 0")
#                 Alltags.clear()
#             else:
#                 sstop = 0
#                 Alltags.clear()

#         if i == 0x11:
#             ps = 1
#             cnt = 0
#         if ps:
#             tagid.append(i)
#             cnt += 1
#             if cnt == 18:
#                 cnt = 0
#                 ps = 0
#                 pr_tagid(queue, sstop)
#                 tagid.clear()


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

class TagReader(Process):
  """
  This class is used to read values from the RFID reader connected via USB
  """
  def __init__(self, queue, main_queue):
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.serial_device = None
    self.should_read_tags = False
    self.tag_bytes_list = [] # The bytes read from the serial device for an RFID tag will be stored in this list
    self.tag_hex_list = []  # The hex value of the RFID tag will be stored in this list
    self.string_of_tags = ""

  def convert_tags_to_hex(self, send_back_tag_values: bool):
    """
    This method is called to convert a list of bytes into one complete
    RFID tag

    Parameters
    ----------
    send_back_tag_values: boolean
    """
    tag_hex_value = ""
    for index, bytes_value in enumerate(self.tag_bytes_list):
      # The assumption here is that the first 3 bytes and the last byte are just placeholders
      if index > 3 and index < 16:
        tag_hex_value += "{0:02X}".format(bytes_value)

    if tag_hex_value not in self.tag_hex_list:
      self.tag_hex_list.append(tag_hex_value)

    if send_back_tag_values is True and len(self.tag_hex_list) > 0:
      self.string_of_tags = str(len(self.tag_hex_list)) + " "
      for tag_value in self.tag_hex_list:
        self.string_of_tags += tag_value + " "
      
      self.main_queue.put("TAGS: " + self.string_of_tags)
      self.string_of_tags = ""

  def read_tags_bytes(self):
    """
    This method is called to start reading the byte strings from the serial
    device connected via USB

    Raises
    ------
    serial.serialutil.SerialException
      If the USB device is not connected properly and cannot be read from
    """
    try:
      self.serial_device = serial.Serial('/dev/ttyUSB0', 57600, timeout=0.5)
    except serial.serialutil.SerialException as err:
      raise err

    while True:
      send_back_tag_values = False
      input_queue_string = self.queue.get()
      if input_queue_string == "SCAN":
        send_back_tag_values = True
      else:
        send_back_tag_values = False

      read_bytes = self.serial_device.read()
      int_value = int.from_bytes(read_bytes, "big")
      sys.stdout.flush()

      # The assumption here is that the starting byte of any tag id is 0x11 (which is 17)
      if int_value == 0x11:
        self.should_read_tags = True
      
      if self.should_read_tags is True:
        self.tag_bytes_list.append(int_value)

        # The assumption here is that one RFID tag has a sequence of 18 bytes
        if len(self.tag_bytes_list) == 18:
          self.should_read_tags = False
          self.convert_tags_to_hex(send_back_tag_values)
          self.tag_bytes_list.clear() # Clear the bytes from the RFID tag read in preparation for the next one

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    self.read_tags_bytes()

class DisplayTagIdGUI(Process):
  """
  This class is used to create a GUI that will be used to display the list of tags that
  are being read from the USB device
  """

  def __init__(self, queue: list, main_queue: list):
    """
    Parameters
    ----------
    queue: list
      The list into which the main process will input data
    main_queue: list
      The list into which this process will transfer data back to the
      main process
    """
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.action_to_perform = None

  def scan(self):
    """
    This method is called when the scan button is pressed
    """
    self.main_queue.put("SCAN")
  
  def upload(self):
    """
    This method is called when the upload button is pressed
    """
    self.main_queue.put("UPLOAD")

  def close_window(self):
    """
    This method is called when the close button is pressed
    """
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
      self.main_queue.put("QUIT")
      self.root.destroy()

  def run_loop(self):
    """
    This method is used to run a loop every 900ms and is called
    by TKinter. It listens for user interactions

    Raises
    ------
    Exception
      Raises a base Exception if a button that is neither scan nor upload
      is clicked
    """
    if self.action_to_perform == "scan":
      self.main_queue.put("scan")
    elif self.action_to_perform == "upload":
      self.main_queue.put("upload")
    elif self.action_to_perform is None:
      # Do nothing if its still default value
      pass
    else:
      raise Exception('An undefined button was pressed')

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    self.root = tk.Tk()
    self.canvas = tk.Canvas(self.root, bg="white",
                            width=800,
                            height=450)
    self.canvas.pack(side=tk.TOP)
    scan_button = ttk.Button(self.root, text="Scan", command=self.scan)
    upload_button = ttk.Button(self.root, text="Upload", command=self.upload)
    scan_button.pack(side=tk.RIGHT)
    upload_button.pack(side=tk.RIGHT)
    self.root.protocol("WM_DELETE_WINDOW", self.close_window)
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

  def command(self, location: str):
    """
    This method is used to listen to a click event where the user
    picks the location

    Parameters
    ----------
    location: str, required
      The location selected by the user
    """
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    with open(filename, 'w+') as f:
      f.write(location)
    self.root.destroy()

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
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


# This function is used to call the GPS device attached via USB
# and fetch the latitude and longitude

def get_latitude_and_longitude(gps_child_queue):
  time_end = time.time() + 5

  # Read from the GPS device for 30 seconds
  # serial_device = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
  # while time.time() < time_end:
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
  processes: list = []

  # Start GPS process and allow user to select location only if
  # locatio has not already been set
  if should_check_location is True:

    # Create the GUI and associated queue to fetch lat & long using GPS device
    gps_queue = Queue()
    gps_process = Process(
        target=get_latitude_and_longitude, args=(gps_queue,))

    # Create the GUI and associated queue to allow the user to select the location
    select_location_gui_queue = Queue()
    select_location_gui_process = SelectLocationGUI(select_location_gui_queue)

    processes.append(gps_process)
    processes.append(select_location_gui_process)

    # Start the processes
    for process in processes:
      process.start()

    # Pass data between the various processes
    location_data = gps_queue.get()
    possible_locations = get_location(location_data)
    select_location_gui_queue.put(possible_locations)

    # Clear the process list
    processes.clear()

  # Create the main queue that will be used for parent child communication
  main_queue = Queue()

  # Create the GUI and associated queue to allow the user to view the scanned tags
  display_tag_id_gui_queue = Queue()
  display_tag_id_gui_process = DisplayTagIdGUI(display_tag_id_gui_queue, main_queue)
  processes.append(display_tag_id_gui_process)

  # Create the process associated with reading tags
  read_tags_queue = Queue()
  read_tags_process = TagReader(read_tags_queue, main_queue)
  processes.append(read_tags_process)

  for process in processes:
    process.start()

  should_exit_program = False

  while should_exit_program is False:
    main_queue_value = main_queue.get()
    print("main_queue_value", main_queue_value)
    if main_queue_value == "SCAN":
      print("START SCANNING")
      read_tags_queue.put("SCAN")
    elif main_queue_value == "UPLOAD":
      print("START UPLOADING")
    elif main_queue_value == "QUIT":
      should_exit_program = True



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
