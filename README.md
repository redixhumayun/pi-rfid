# Introduction

This document will serve as a setup guide when setting up a new RFID system using a Raspberry Pi 4A/B.

There are a few things that need to be done before the Pi can be used in an RFID system:

1. Load a base OS image on the SD card of the Pi
2. Set up the Pi as a managed instance with AWS SSM
3. Register the Pi with CodeDeploy as an on-premise server.
4. Set up the systemd service to start the program automatically
5. Set up the udev service to register the barcode scanner as soon as it is plugged in
6. Ensure that the development or production pipeline works well with the Pi
7. Test the integration of the physical infrastructure with the Pi

## Base OS Image

**Need to fill this section out**

## Set Up Pi As Managed Instance with AWS SSM

The AWS Systems Manager allows remote management of the Pi. Documentation on how to set that up can be found [here](https://aws.amazon.com/blogs/mt/manage-raspberry-pi-devices-using-aws-systems-manager/).

It involves creating a separate user for each device in the IAM console. The naming scheme for the user required AWS SSM is: RaspberryPi-RFID-<location>. For example, RaspberryPi-RFID-ID1 and RaspberryPi-RFID-ID4

## AWS CodeDeploy Registration

Installing the CodeDeploy agent on the Raspberry Pi is a little more complicated.

[This blog post](https://aws.amazon.com/blogs/devops/automating-deployments-to-raspberry-pi-devices-using-aws-codepipeline/) shows an example of setting up the CodeDeploy agent for a Pi running Ubuntu.

Technically, AWS does not support installing the CodeDeploy agent officially for Raspberry Pi OS. However, follow [this video tutorial](https://www.udemy.com/course/awsraspberrypi/learn/lecture/14245834#overview) for a way around that. The role required for this in IAM is called CodeDeployServiceRoleRaspberryPiRFID.

On the CodeDeploy console, there is a RaspberryPi-RFID application set up with two deployment groups - one for test and one for production. Make sure to register the Pi with the correct deployment group.

**Note**: When installing and running CodeDeployAgent on the Pi, be mindful of [this issue](https://github.com/aws/aws-codedeploy-agent/issues/80). 
When an ApplicationStop shell script is deployed to the Pi and there is an error with it, it is not possible to deploy a new version of the ApplicationStop script through CodeDeploy itself. This is because ApplicationStop.sh will run every time a new revision is deployed. If there is a problem with the old revision, it will always error and the new revision will never deploy.

## Testing The Pipeline

To test the pipeline, commit some code to either the development or main branch, to run the development or production pipeline respectively.

## Set Up Systemd On The Pi

The Raspberry Pi makes use of systemd (which is the standard service runner on Linux boxes) to daemonize the RFID reader service. You can read more about setting up systemd on a Raspberry Pi here and here. This Medium post provides a sample systemd file which is used to automatically keep restarting a failed process infinitely.

The systemd file for the `pi-rfid` program is here. It needs to be placed in the `/lib/systemd/system/pi-rfid.service` file.

```bash
[Unit]
Description=Pi RFID Service that will boot to GUI
StartLimitIntervalSec=0

[Service]
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/home/pi/pi-rfid/pi-rfid-virtual-env/bin/python3 /home/pi/pi-rfid/RFID_Upload_V0.2.py --env development
Restart=Always
RestartSec=1
KillMode=control-group
TimeoutSec=infinity

[Install]
WantedBy=graphical.target
```

## Set Up udev Rules On The System

Udev rules are user land dev rules which will run based on certain conditions - like plugging in a USB device for instance.

The below line of code is added to the /etc/udev/rules/10-com.rules file which is created to specify user udev rules. This will change the file permissions for the barcode scanner when it is connected. The current model of the barcode scanner that this will work for is RETSOL LS 450 Laser Barcode Scanner

```bash
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="0011", MODE="666", SYMLINK+="usb-barcode-scanner"
```

## How To Start The Program

First, activate the virtual environment for the project by using the following commands

```bash
cd ~
cd ./pi-rfid
source ./pi-rfid-virtual-env/bin/activate
```

The command to run the program is `python3 ./RFID_Upload_V0.2.py --env production`. Be warned that running it in production will cause data to be uploaded to the production DB. If you won't plan to test the actual RFID scanning, you can run `python3 ./RFID_Upload_V0.2.py --env development`.

## Setting Up udev Rules On The System

The below line of code is added to the `/etc/udev/rules/10-com.rules` file which is created to specify user udev rules. This will change the file permissions for the barcode scanner when it is connected.

```bash
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="0011", MODE="666", SYMLINK+="usb-barcode-scanner"
```
