


# Install python packages
pip install puresnmp
pip install RPI


---------------------------------------------------------------------------------------------------------------------


>>> vi /etc/udev/rules.d/10-com.rules
# This rule is meant for the USB barcode scanner
SUBSYSTEM=="hidraw2", ATTRS{idVendor}=="0c2e", ATTRS{idProduct}=="0b01", MODE="666", SYMLINK+="usb-barcode-scanner"

# This group of rules is meant for ttyUSB devices which are plugged into different physical ports
KERNEL=="ttyUSB*", KERNELS=="1-1.2:1.0", SYMLINK+="weighing-scale"

>>> To have this rules file take effect, type in sudo udevadm trigger


