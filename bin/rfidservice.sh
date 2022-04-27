#!/bin/bash


#############################################################
# Author Ganesha Sridhara                                   #
# Date 31/Mar/2022                                          #
# This shell script is provided for start / stop process    #
#       RFID application                                    #
#############################################################


export RFID_HOME=/home/pi/RFID

export RFID_CONF=/var/RFID/conf

function start()
{

	# Get barcode usb port
	echo "/dev/"`dmesg | grep Honey | grep Keyboard | tail -1 | cut -d ":" -f 4|cut -d "," -f 2 ` > $RFID_CONF/barcodeport

        # If RFID Application is alread running display message and exit.
        if [ -f "$RFID_HOME/log/RFIDProcess.pid" ]
        then
                read pid <  $RFID_HOME/log/RFIDProcess.pid
                if [ `ps -p $pid | wc -l ` -gt 1 ]
                then
                        echo "RFID Process is running with Process ID=$pid"
                        exit
                fi
        fi

        sleep 1;

	nohup python $RFID_HOME/RFIDUI.py $RFID_CONF/RFIDConfig.ini > $RFID_HOME/log/output 2> /dev/null &

        echo $! > $RFID_HOME/log/RFIDProcess.pid

        echo "RFID Process started successfully."
}

function stop()
{
	if [ -d "$RFID_HOME" ]
	then
			if [ -f "$RFID_HOME/log/RFIDProcess.pid" ]
			then
					read pid <  $RFID_HOME/log/RFIDProcess.pid
					if [ `ps -p $pid | wc -l ` -gt 1 ]
					then
							kill -15 $pid
							sleep 2
							# if not normal shutdown
							if [ `ps -p $pid | wc -l ` -gt 1 ]
							then
									kill -9 $pid
							fi
							echo "RFID Process stopped successfully."
					else
							 echo "RFID Process is not running."
					fi

					rm -f $RFID_HOME/log/RFIDProcess.pid
			else
					echo "RFID Process is not running."
			fi
	fi
}

function status()
{
	if [ -d "$RFID_HOME" ]
	then
			if [ -f "$RFID_HOME/log/RFIDProcess.pid" ]
			then
					read pid <  $RFID_HOME/log/RFIDProcess.pid
					if [ `ps -p $pid | wc -l ` -gt 1 ]
					then
							echo "RFID Process is running with Process ID=$pid"
					else
							 echo "RFID Process is not running."
							 rm -f $RFID_HOME/log/RFIDProcess.pid
					fi
			else
					echo "RFID Process is not running."
			fi
	fi
}


case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  status)
        status
        ;;
  restart)
        stop
        start
        ;;
  *)
        echo $"Usage: $0 {start|stop|restart|status}"
        exit 1
esac



