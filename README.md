**mppcInterface**

End-to-end setup for a Raspberry Pi–based cosmic muon detector.
This repo includes a one-shot installer that enables I²C/SPI, installs dependencies, builds firmware helpers, configures boot-time services, schedules data transfers, and prints an SSH public key for secure access.

Quick start (recommended)

Download the installer

curl -fL -o DetectorInstallation.sh https://raw.githubusercontent.com/tharinduudu/mppcInterface/main/DetectorInstallation.sh


Review the script (optional but recommended)

less DetectorInstallation.sh


Run it

chmod +x DetectorInstallation.sh
sudo ./DetectorInstallation.sh


The script is idempotent: you can re-run it safely if needed.

What the installer does

Enables I²C & SPI

Persists settings in /boot/config.txt (and /boot/firmware/config.txt if present)

Loads overlays/modules immediately so you can proceed without reboot (when possible)

Fetches repo contents needed for the detector:

mppcinterface-oct-2022/ (firmware helpers & slowControl)

bmp280.py (environment logger)

Installs WiringPi from source

Builds the helper binaries (ice40, max1932, dac60508) with make clean && make

Builds slowControl and applies a safe relink fallback so WiringPi links correctly

Installs a non-blocking /etc/rc.local and enables systemd’s compatibility unit for next boot

Installs Datatransfer.sh to /home/cosmic and schedules it via cron every 6 hours

Generates an SSH key and prints the public key with a friendly message you can share with GSU

Requirements

Hardware: Raspberry Pi 4 (others may work, not tested here)

OS: Raspberry Pi OS Bullseye/Bookworm

User: assumes primary user cosmic (edit the script if different)

Network: internet access during install

Privileges: run the installer with sudo

After install

Reboot if the script tells you SPI/I²C device nodes were missing:

sudo reboot


Verify devices

ls -l /dev/i2c-1
ls -l /dev/spidev*


Check rc.local status (enabled for next boot):

systemctl status rc-local


Confirm cron job (runs every 6h):

crontab -u cosmic -l


Get your public key again (if needed):

cat /home/cosmic/.ssh/id_ed25519.pub

Where things live

Detector code & helpers: /home/cosmic/mppcinterface-oct-2022/

BMP280 logger: /home/cosmic/bmp280.py

Data transfer script: /home/cosmic/Datatransfer.sh (cron runs it every 6h)

Boot-time startup: /etc/rc.local (runs hardware init + loggers in background)

Logs:

SlowControl: /var/log/slowcontrol.log

BMP280: /var/log/bmp280.log
