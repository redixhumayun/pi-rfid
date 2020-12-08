#!/usr/bin/python3
from multiprocessing import Process, Queue
import random
import time
import serial
import pynmea2
import sys
import requests
import json
import tkinter as tk

#########################################################################

ps=0
cnt=0
tagid=[]
    
Alltags=[]
sttime=0
prevtime=0

def pr_tagid(que,ss):
    global sttime,prevtime
    taghex=""

    sttime=time.time()
    a=len(tagid)
    for i in range(a):
        if i >3 and i < 16:
            taghex+="{0:02X}".format(tagid[i])
        #print(hex(tagid[i]),end=" ")

    if taghex not in Alltags:
        Alltags.append(taghex)
        print(taghex,": Added")

    if ss == 1:
        if sttime - prevtime > 1.0:
            print("Sending all tags")
            lentag=len(Alltags)
            S=str(lentag)+" "
            if lentag > 0:
                for i in range(lentag):
                    S+=(Alltags[i]+" ")

            que.put("TAG "+S)
            prevtime=sttime

        


def tagreader_proc(x,queue,rq):
    global ps
    sstop=0
    trq=rq
    S=""

    ser=serial.Serial('/dev/ttyUSB0', 57600,timeout=0.5)

    while True:
        x = ser.read()          
        i=int.from_bytes(x,"big")
        #print(hex(i), end=" ")
        sys.stdout.flush()
        if not trq.empty():
            arq=trq.get()
            if arq == "start":
                print("setting sstop")
                sstop=1
               # if len(Alltags) == 0:
               #     queue.put("TAG: 0")
                Alltags.clear()
            else:
                sstop=0
                Alltags.clear()

        if i == 0x11:
            ps=1
            cnt=0
        if ps:
            tagid.append(i)
            cnt +=1
            if cnt == 18:
                cnt=0
                ps=0
                pr_tagid(queue,sstop)
                tagid.clear()




#########################################################################
def upload_proc(x,queue,rq):
    trq=rq
    while True:
        if not trq.empty():
            arq=trq.get()
            print("------------Upload Process Ret:",arq)
            url = 'http://eetrax.com/json_my/jd2.php'
            payload = arq
            try:
                r = requests.post(url, json=payload,timeout=4)
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
def gps_proc(x,queue,rq):
    sstop=0
    trq=rq
    S=""
    ser=serial.Serial('/dev/ttyACM0', 9600,timeout=1)

    while True:
        try:
            x = ser.readline()          
            y=x[:-2].decode("utf-8")
            if  y.find("RMC") > 0:
                msg = pynmea2.parse(str(y))
                S="GPS " +"{:.2f}".format(msg.latitude)+" "+"{:.2f}".format(msg.longitude)

                if sstop ==1:
                   queue.put(S)
            if not trq.empty():
                arq=trq.get()
                print("Gps Process Ret:",arq)
                if arq == "start":
                    sstop=1
                else:
                    sstop=0


        except Exception as e:
            print("GPS Excepton caught",e)

def rand_num(x,queue,rq):
    sstop=0
    trq=-1
    if x == 0:
        trq= rq1
    elif x == 1:
        trq=rq2
    elif x == 2:
        trq=rq3

    while True:
        num = random.random()
        S=str(x)+" "+str(num)
        if not trq.empty():
            arq=trq.get()
            print("Process Ret:",x,arq)
            if arq == "start":
                sstop=1
            else:
                sstop=0
        if sstop ==1:
            queue.put(S)
        #time.sleep(random.randint(1,10))
        time.sleep(1)


###########################################################
canvas_width = 800
canvas_height =450
scan=0
dvar=-1

tk_wq=""
tk_sq=""
master=""
canvas=-1
upvar=-1

def scan():
    global scan
    scan=1


def upload():
    global upvar
    upvar=1


def tloop():
    global scan,canvas,dvar,tk_wq,tk_sq,master,upvar
    if scan ==1 :
        scan=0
        if dvar >-1:
            jj=canvas.delete("cantext")
            master.update()
            print("Ret Dvar",dvar,jj)
        tk_wq.put("TKFE_SCAN")
    if upvar==1:
        upvar=0
        if dvar >-1:
            jj=canvas.delete("cantext")
            master.update()
            print("Up Dvar",dvar,jj)
        tk_wq.put("TKFE_UPLOAD")
            
    if not tk_sq.empty():
        arq=tk_sq.get()
        print("TK Process Ret:",arq)
        if dvar >-1:
            jj=canvas.delete("cantext")
            master.update()
        dvar=canvas.create_text(320,200,fill="Black", anchor=tk.NW,font="Helvetica 80 bold", text=str(arq),tag="cantext")
        master.update()

    master.after(300,tloop)

def gui_bk_proc(x,queue,rq):
    global tk_wq, tk_sq,master,canvas
    tk_wq=queue
    tk_sq=rq
    master = tk.Tk()

    canvas= tk.Canvas(master,bg="white", 
           width=canvas_width, 
           height=canvas_height)
    canvas.pack(side=tk.TOP)
    # bk = tk.PhotoImage(file="rfid-bk.png")
    # bkimg=canvas.create_image(0,0, anchor=tk.NW, image=bk)
    master.update()
    b_scan=tk.Button(master,text = "Scan",command=scan)
    b_scan.pack(side=tk.RIGHT)
    b_up=tk.Button(master,text = "Upload",command=upload)
    b_up.pack(side=tk.RIGHT)
    master.after(900,tloop)
    tk.mainloop()
    
###########################################################


if __name__ == "__main__":
    wq = Queue()
    rq1= Queue()
    rq2= Queue()
    gpsq= Queue()
    tagq= Queue()
    guibq= Queue()
    uploadq= Queue()

    processes=[]

    # a=Process(target=rand_num, args=(0,wq,rq1)) 
    # b=Process(target=rand_num, args=(1,wq,rq2)) 
    # c=Process(target=gps_proc, args=(2,wq,gpsq)) 
    # d=Process(target=tagreader_proc,args=(3,wq,tagq))
    e=Process(target=gui_bk_proc,args=(4,wq,guibq))
    # f=Process(target=upload_proc,args=(5,wq,uploadq))
    # processes.append(a)
    # processes.append(b)
    # processes.append(c)
    # processes.append(d)
    processes.append(e)
    # processes.append(f)


    for p in processes:
        p.start()


    cnt=1
    sent="end"
    tagstr=""
    gpsstr=""
    gpsdict={}
    tagdict={}
    while True:
        try:
            for p in processes:
                if not wq.empty():
                    rq=wq.get()
                    print("ML Ret:",rq)
                    if rq == "TKFE_SCAN":
                        rq1.put("start")
                        rq2.put("start")
                        gpsq.put("start")
                        tagq.put("start")
                    elif rq == "TKFE_UPLOAD":
                        rq1.put("end")
                        rq2.put("end")
                        gpsq.put("end")
                        tagq.put("end")
                        updict=dict({"tags":uptlist,"gps":upglist})
                        uploadq.put(updict)
                    elif rq == "UP_SUCCESS":
                        guibq.put("Upload Sucess") 
                    elif rq == "UP_FAIL":
                        guibq.put("Upload Failure") 

                    if rq.find("TAG") == 0:
                        tagstr=rq
                        taglist=rq.split()
                        guibq.put(taglist[1])
                        uptlist=taglist[2:]
                    if rq.find("GPS") == 0:
                        gpsstr=rq
                        gpslist=rq.split()
                        upglist=gpslist[1:]
                        



            cnt+=1
            time.sleep(1)
        except Exception as inst:
            print("Type",type(inst))    # the exception instance
            print("Args",inst.args)     # arguments stored in .args
            print("Inst",inst)  

