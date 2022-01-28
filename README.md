# Introduction

This document will serve as a setup guide when setting up a new RFID system using a Raspberry Pi 4B.

There are a few things that need to be done before the Pi can be used in an RFID system:

1. Load a base OS image on the SD card of the Pi
2. Activate the serial interface on the Pi
3. Set up the Pi as a managed instance with AWS SSM
4. Install the AWS CLI on the Pi
5. Register the Pi with CodeDeploy as an on-premise server.
6. Set up the systemd service to start the program automatically
7. Set up the udev service to register the barcode scanner as soon as it is plugged in
8. Ensure that the development or production pipeline works well with the Pi
9. Test the integration of the physical infrastructure with the Pi

## Base OS Image

The base OS image used for all installations can be found in [this GDrive link](https://drive.google.com/file/d/1gxzEfLJJQkubYYjEBph1UnbrfVTQx4nT/view?usp=sharing).

## Activate The Serial Interface

Type in `sudo raspi-config` and go to the interface options. Then select Serial Port. 

You will be asked if you would like a login shell to be accessible over serial. Select No for this.

Next, you will be asked if you want the serial hardware port to be enabled. Select yes for this.

When you select finish, you will be asked to reboot the Pi. Reboot the Pi at this time so that the changes take effect.

## Set Up Pi As Managed Instance with AWS SSM

The AWS Systems Manager allows remote management of the Pi. Documentation on how to set that up can be found [here](https://aws.amazon.com/blogs/mt/manage-raspberry-pi-devices-using-aws-systems-manager/).

It involves creating a separate user for each device in the IAM console. The naming scheme while registering the Pi with AWS is: RaspberryPi-RFID-<location>. For example, RaspberryPi-RFID-ID1 and RaspberryPi-RFID-ID4.

Create a separate activation ID and code for each instance so that each instance has a separate name as mentioned in the previous paragraph.

## Install AWS CLI On The Pi

Install the AWS CLI with the apt package manager for Linux variants. The following command will install the AWS CLI on a Pi.

`sudo apt-get install awscli`

Run `aws --version` after running the above command to ensure that the CLI is installed and working.

Create an IAM user for the Pi and run `aws configure` to configure the AWS CLI on the Pi with the credentials of the user just created.

Note: Running `aws configure` and `sudo aws configure` will configure two different sets of users

## AWS CodeDeploy Registration

Installing the CodeDeploy agent on the Raspberry Pi is a little more complicated.

[This blog post](https://aws.amazon.com/blogs/devops/automating-deployments-to-raspberry-pi-devices-using-aws-codepipeline/) shows an example of setting up the CodeDeploy agent for a Pi running Ubuntu.

A quick overview of what the blog post goes through can be found below:

### Install Ruby

Ruby is required for using the wget command later. Install ruby with `sudo apt-get install ruby`.

### Install The CodeDeploy Agent

Download the CodeDeploy agent file from the link below using the following command:
`sudo wget https://aws-codedeploy-ap-south-1.s3.amazonaws.com/latest/install`

After that, make the `install` file executable with `sudo chmod +x ./install`

Next, run `sudo ./install auto`. Once done, run `sudo service codedeploy-agent status` to see if the service is running.

### Register The Instance With CodeDeploy

Once, the CodeDeploy agent has been installed, do the following commands to register the instance as an on-premise server with CodeDeploy.

First, add the following policy to the user for the Pi: `CodeDeployOnPremiseInstanceRegistrationPolicy`. This is a custom policy that provides the permissions when registering an on-premise instance.

Next, create a file called `codedeploy.onpremises.yml` in `/etc/codedeploy-agent/conf` and enter the following information in it.

``` yaml
---
aws_access_key_id: secret-key-id
aws_secret_access_key: secret-access-key
iam_user_arn: iam-user-arn
region: supported-region
```

Finally, run the following command to register the instance:

`aws deploy register-on-premises-instance --instance-name RaspberryPi-RFID-ID11 --iam-user-arn arn:aws:iam::your-user-id --region your-region`

Tag the instance with the following tags: `location` and `environment` on the console. Environment should be set to production or staging.

[This document](https://docs.aws.amazon.com/codedeploy/latest/userguide/register-on-premises-instance-iam-user-arn.html#register-on-premises-instance-iam-user-arn-1) contains a more detailed explanation.

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
Wants=network-online.target
After=network.target
StartLimitIntervalSec=0

[Service]
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/home/pi/pi-rfid/pi-rfid-virtual-env/bin/python3 /home/pi/pi-rfid/RFID_Upload_V0.2.py --env development
Restart=always
RestartSec=1
KillMode=control-group
TimeoutSec=infinity

[Install]
WantedBy=graphical.target
```

To have this unit file take effect, type in `sudo systemctl daemon-reload`

## Set Up udev Rules On The System

Udev rules are user land dev rules which will run based on certain conditions - like plugging in a USB device for instance.

The below lines of code are added to the `/etc/udev/rules.d/10-com.rules` file which is created to specify user udev rules.

```bash
# This rule is meant for the USB barcode scanner
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="0011", MODE="666", SYMLINK+="usb-barcode-scanner"

# This group of rules is meant for ttyUSB devices which are plugged into different physical ports
KERNEL=="ttyUSB*", KERNELS=="1-1.3:1.0", SYMLINK+="rfid-reader-1"
KERNEL=="ttyUSB*", KERNELS=="1-1.1:1.0", SYMLINK+="rfid-reader-2"
KERNEL=="ttyUSB*", KERNELS=="1-1.2:1.0", SYMLINK+="weighing-scale"

# This group of rules is a test meant only to see if inserting a usb drive into different
# physical ports will create a different symlink
KERNEL=="sd*", KERNELS=="1-1.3:1.0", SYMLINK+="usb-stick-3"
KERNEL=="sd*", KERNELS=="1-1.1:1.0", SYMLINK+="usb-stick-1"
KERNEL=="sd*", KERNELS=="1-1.2:1.0", SYMLINK+="usb-stick-2"
```

To have this rules file take effect, type in `sudo udevadm trigger`

## How To Start The Program

First, activate the virtual environment for the project by using the following commands

```bash
cd ~
cd ./pi-rfid
source ./pi-rfid-virtual-env/bin/activate
```

The command to run the program is `python3 ./RFID_Upload_V0.2.py --env production`. Be warned that running it in production will cause data to be uploaded to the production DB. If you won't plan to test the actual RFID scanning, you can run `python3 ./RFID_Upload_V0.2.py --env development`.
