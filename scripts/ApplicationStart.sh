#!/bin/bash
# This script will run after CodeDeploy starts the new application revision
# This will be the fourth script to run

systemctl daemon-reload
systemctl start pi-rfid.service
systemctl enable pi-rfid.service