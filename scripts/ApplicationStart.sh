#!/bin/bash
# This script will run after CodeDeploy starts the new application revision
# This will be the fourth script to run

sudo systemctl daemon-reload
sudo systemctl start pi-rfid.service
sudo systemctl enable pi-rfid.service