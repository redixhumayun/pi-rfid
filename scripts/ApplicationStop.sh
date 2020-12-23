#!/bin/bash
# This script will run when CodeDeploy is trying to create a new deployment.
# This will be the first script to run
sudo systemctl stop pi-rfid.service
sudo rm -r /home/pi/pi-rfid