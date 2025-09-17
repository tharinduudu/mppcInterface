**!!Please send the public key printed at the end of the procedure**

# mppcInterface

End-to-end setup for a Raspberry Pi–based cosmic muon detector.  
This repo includes a one step installer that enables I²C/SPI, installs dependencies, builds firmware helpers, configures boot-time services, schedules data transfers, and prints an SSH public key for secure access.

---

## Quick start

1) **Download the installer**
```bash
curl -fL -o DetectorInstallation.sh https://raw.githubusercontent.com/tharinduudu/mppcInterface/main/DetectorInstallation.sh
```

2) **(Optional) Review the script**
```bash
less DetectorInstallation.sh
```

3) **Run it**
```bash
chmod +x DetectorInstallation.sh
sudo ./DetectorInstallation.sh
```

> The script is idempotent: you can re-run it safely if needed.

---

## What the installer does

- **Enables I²C & SPI**
  - Persists settings in `/boot/config.txt` (and `/boot/firmware/config.txt` if present)
  - Loads overlays/modules **immediately** so you can proceed without reboot (when possible)
- **Fetches repo contents** needed for the detector:
  - `mppcinterface-oct-2022/` (firmware helpers & slowControl)
  - `bmp280.py` (environment logger)
- **Installs WiringPi** from source
- **Builds** the helper binaries (`ice40`, `max1932`, `dac60508`) with `make clean && make`
- **Builds `slowControl`** and applies a **safe relink fallback** so WiringPi links correctly
- **Installs a non-blocking `/etc/rc.local`** and enables systemd’s compatibility unit for next boot
- **Installs `Datatransfer.sh`** to `/home/cosmic` and schedules it via **cron** every 6 hours
- **Generates an SSH key** and prints the **public key** with a friendly message you can share with GSU

---

## Requirements

- **Hardware**: Raspberry Pi 4 (others may work, not tested here)
- **OS**: Raspberry Pi OS Bullseye/Bookworm
- **User**: assumes primary user **`cosmic`** (edit the script if different)
- **Network**: internet access during install
- **Privileges**: run the installer with `sudo`

---

## After install

- **Reboot** if the script tells you SPI/I²C device nodes were missing:
  ```bash
  sudo reboot
  ```
- **Verify devices**
  ```bash
  ls -l /dev/i2c-1
  ls -l /dev/spidev*
  ```
- **Check rc.local status** (enabled for next boot):
  ```bash
  systemctl status rc-local
  ```
- **Confirm cron job** (runs every 6h):
  ```bash
  crontab -u cosmic -l
  ```
- **Get your public key again** (if needed):
  ```bash
  cat /home/cosmic/.ssh/id_ed25519.pub
  ```

---

## Where things live

- Detector code & helpers: `/home/cosmic/mppcinterface-oct-2022/`
- BMP280 logger: `/home/cosmic/bmp280.py`
- Data transfer script: `/home/cosmic/Datatransfer.sh` (cron runs it every 6h)
- Boot-time startup: `/etc/rc.local` (runs hardware init + loggers in background)
- Logs:
  - SlowControl: `/var/log/slowcontrol.log`
  - BMP280: `/var/log/bmp280.log`

---

## Customize

Open `DetectorInstallation.sh` and adjust:

- `USER_NAME` (default `cosmic`)
- `BITFILE` (bitstream filename for your station)
- Any site-specific tags/paths inside your `rc.local` or data scripts

Re-run the installer after changes.

---

## Troubleshooting

- **Missing `/dev/spidev0.0` or `/dev/i2c-1`**  
  Reboot once after install:
  ```bash
  sudo reboot
  ```
  Then re-check device nodes.

- **`slowControl` fails to link with WiringPi**  
  The installer already applies a “relink once” fallback:
  ```bash
  cd /home/cosmic/mppcinterface-oct-2022/firmware/libraries/slowControl
  rm -f main main.o
  g++ -c main.cpp -std=c++11 -I. && g++ main.o -lwiringPi -o main
  ```

- **`rc.local` hangs when starting manually**  
  This repo’s `rc.local` backgrounds long-running tasks and ends with `exit 0`.  
  If you edited it, ensure long commands end with `&` and the file ends with `exit 0`.

- **Cron not running the transfer**  
  Check the user’s crontab:
  ```bash
  crontab -u cosmic -l
  ```
  And system log for cron activity:
  ```bash
  grep CRON /var/log/syslog
  ```
