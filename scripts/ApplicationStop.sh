#!/bin/bash
# This script will run when CodeDeploy is trying to create a new deployment.
# This will be the first script to run
systemctl stop pi-rfid.service
rm /home/pi/pi-rfid