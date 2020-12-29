#!/bin/bash
# This script will run just after CodeDeploy installs the new deployment
# This will be the third script to run

cd /home/pi/pi-rfid
# This will create a virtual environment
python3 -m venv pi-rfid-virtual-env
# This will activate the virtual environment
source pi-rfid-virtual-env/bin/activate
# This will install the required packages
pip3 install -r requirements.txt