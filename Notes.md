
## How To Start The Program

First, activate the virtual environment for the project by using the following commands

```bash
cd ~
cd ./pi-rfid
source ./pi-rfid-virtual-env/bin/activate
```

The command to run the program is `python3 ./RFID_Upload_V0.2.py --env production`. Be warned that running it in production will cause data to be uploaded to the production DB. If you won't plan to test the actual RFID scanning, you can run `python3 ./RFID_Upload_V0.2.py --env development`.

##  Setting Up udev Rules On The System

The below line of code is added to the `/etc/udev/rules/10-com.rules` file which is created to specify user udev rules. This will change the file permissions for the barcode scanner when it is connected.

```bash
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="0011", MODE="666", SYMLINK+="usb-barcode-scanner"
```