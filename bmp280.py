#!/usr/bin/env python3
# Simple BMP280 logger: no Blinka required.
# Logs "timestamp,temp_C,pressure_hPa" every 300 s to /home/cosmic/bmp280_logs/<stamp>.log

import csv
import datetime as dt
import os
import time
import sys
import signal

# ---- user knobs ----
ADDR       = 0x76
INTERVAL_S = 300                  # 5 minutes
OUTDIR     = "/home/cosmic/bmp280_logs"
PREFIX     = "BMP280"

# Try smbus2 first (nicer on many systems), fall back to smbus
_i2c = None
try:
    from smbus2 import SMBus
    _i2c = "smbus2"
except Exception:
    try:
        from smbus import SMBus
        _i2c = "smbus"
    except Exception as e:
        print("Need I²C lib. Install one of:\n"
              "  sudo apt-get install -y python3-smbus\n"
              "  OR\n"
              "  sudo pip3 install smbus2 --break-system-packages", file=sys.stderr)
        sys.exit(1)

# BMP280 registers
REG_CALIB_START = 0x88  # 24 bytes: T/P calibration
REG_ID          = 0xD0
REG_RESET       = 0xE0
REG_STATUS      = 0xF3
REG_CTRL_MEAS   = 0xF4
REG_CONFIG      = 0xF5
REG_PRESS_MSB   = 0xF7  # F7..F9 = press, FA..FC = temp

STOP = False
def _sig(_s, _f):  # graceful stop
    global STOP
    STOP = True

signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)

def _s16(u):
    return u - 65536 if u > 32767 else u

def read_calibration(bus):
    # Read 24 bytes (dig_T1..dig_T3, dig_P1..dig_P9)
    b = bus.read_i2c_block_data(ADDR, REG_CALIB_START, 24)
    dig_T1 = b[0] | (b[1] << 8)
    dig_T2 = _s16(b[2] | (b[3] << 8))
    dig_T3 = _s16(b[4] | (b[5] << 8))
    dig_P1 = b[6] | (b[7] << 8)
    dig_P2 = _s16(b[8] | (b[9] << 8))
    dig_P3 = _s16(b[10] | (b[11] << 8))
    dig_P4 = _s16(b[12] | (b[13] << 8))
    dig_P5 = _s16(b[14] | (b[15] << 8))
    dig_P6 = _s16(b[16] | (b[17] << 8))
    dig_P7 = _s16(b[18] | (b[19] << 8))
    dig_P8 = _s16(b[20] | (b[21] << 8))
    dig_P9 = _s16(b[22] | (b[23] << 8))
    return (dig_T1, dig_T2, dig_T3,
            dig_P1, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9)

def configure_sensor(bus):
    # Normal mode, oversampling x1 (simple, low power)
    # ctrl_meas: [osrs_t(2:0)=001][osrs_p(5:2)=001][mode(1:0)=11(normal)]
    bus.write_byte_data(ADDR, REG_CTRL_MEAS, 0b001_001_11)
    # config: standby 500ms (t_sb=100), filter off
    bus.write_byte_data(ADDR, REG_CONFIG, 0b100_000_00)

def read_raw(bus):
    data = bus.read_i2c_block_data(ADDR, REG_PRESS_MSB, 6)
    adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
    adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
    return adc_t, adc_p

def compensate(adc_t, adc_p, calib):
    dig_T1, dig_T2, dig_T3, dig_P1, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9 = calib

    # Temperature (datasheet floating-point version)
    var1 = (adc_t / 16384.0 - dig_T1 / 1024.0) * dig_T2
    var2 = ((adc_t / 131072.0 - dig_T1 / 8192.0) ** 2) * dig_T3
    t_fine = var1 + var2
    temp_c = t_fine / 5120.0

    # Pressure (Pa)
    var1 = t_fine / 2.0 - 64000.0
    var2 = var1 * var1 * dig_P6 / 32768.0
    var2 = var2 + var1 * dig_P5 * 2.0
    var2 = var2 / 4.0 + dig_P4 * 65536.0
    var1 = (dig_P3 * var1 * var1 / 524288.0 + dig_P2 * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * dig_P1
    if var1 == 0:
        pres_pa = 0.0
    else:
        p = 1048576.0 - adc_p
        p = (p - var2 / 4096.0) * 6250.0 / var1
        var1 = dig_P9 * p * p / 2147483648.0
        var2 = p * dig_P8 / 32768.0
        p = p + (var1 + var2 + dig_P7) / 16.0
        pres_pa = p

    pres_hpa = pres_pa / 100.0
    return float(temp_c), float(pres_hpa)

def ts():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    logfile = os.path.join(OUTDIR, f"{PREFIX}_{dt.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.log")

    try:
        bus = SMBus(1)
    except Exception as e:
        print(f"Failed to open /dev/i2c-1: {e}\n"
              f"Check: ls -l /dev/i2c-1  (enable I2C in raspi-config if missing)", file=sys.stderr)
        sys.exit(1)

    try:
        chip_id = bus.read_byte_data(ADDR, REG_ID)
        # 0x58 = BMP280, 0x60 = BME280 (pressure/temperature still fine)
        # print(f"Chip ID: 0x{chip_id:02X}")
        calib = read_calibration(bus)
        configure_sensor(bus)
        # Small delay to let first measurement be ready
        time.sleep(0.2)

        print(f"[{ts()}] Logging to {logfile} (addr=0x{ADDR:02X}, every {INTERVAL_S}s). Ctrl-C to stop.")
        with open(logfile, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "temp_C", "pressure_hPa"])
            f.flush()

            while not STOP:
                try:
                    adc_t, adc_p = read_raw(bus)
                    t_c, p_hpa = compensate(adc_t, adc_p, calib)
                    w.writerow([ts(), f"{t_c:.3f}", f"{p_hpa:.3f}"])
                    f.flush()
                    print(f"{ts()}  T={t_c:.3f} °C  P={p_hpa:.3f} hPa")
                except Exception as e:
                    # Write NaNs so you can see gaps in data
                    w.writerow([ts(), "nan", "nan"])
                    f.flush()
                    print(f"{ts()} READ ERROR: {e}", file=sys.stderr)

                # Sleep in small chunks so Ctrl-C is responsive
                end = time.time() + INTERVAL_S
                while not STOP and time.time() < end:
                    time.sleep(min(0.5, end - time.time()))
    finally:
        try:
            bus.close()
        except Exception:
            pass
        print(f"[{ts()}] Stopped.")

if __name__ == "__main__":
    main()
