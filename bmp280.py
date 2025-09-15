#!/usr/bin/env python3
"""
bmp280_log.py
Log BMP280 temperature and pressure over I²C every N seconds (default: 300 = 5 min).
Each run creates a new file with the start date/time in the filename.

Usage examples:
  python3 bmp280_log.py
  python3 bmp280_log.py --addr 0x77 --interval 300 --outdir /home/cosmic/logs --prefix Turkey_Istanbul-BMP280
"""

import argparse
import csv
import datetime as dt
import os
import signal
import sys
import time

# --- Optional: helpful error if libraries missing ---
try:
    import board
    import busio
    from adafruit_bmp280 import Adafruit_BMP280_I2C
except Exception as e:
    print(
        "Import error: {}\n\n"
        "Install the libraries first:\n"
        "  sudo apt-get update\n"
        "  sudo apt-get install -y python3-pip python3-dev\n"
        "  pip3 install --upgrade adafruit-circuitpython-bmp280 adafruit-blinka\n"
        "Also enable I2C on the Pi (sudo raspi-config → Interface Options → I2C).\n".format(e),
        file=sys.stderr,
    )
    sys.exit(1)

STOP = False


def handle_signal(signum, frame):
    global STOP
    STOP = True


def parse_args():
    p = argparse.ArgumentParser(description="BMP280 logger (CSV) with timestamped filename.")
    p.add_argument("--addr", default="0x76", help="I2C address (e.g., 0x76 or 0x77). Default: 0x76")
    p.add_argument("--interval", type=int, default=300, help="Seconds between samples. Default: 300 (5 min)")
    p.add_argument("--outdir", default=".", help="Output directory for logs. Default: current directory")
    p.add_argument("--prefix", default="BMP280", help="File prefix. Default: BMP280")
    p.add_argument("--align", action="store_true",
                   help="Align sampling to wall-clock boundaries of 'interval' seconds (e.g., 00,05,10...).")
    return p.parse_args()


def ensure_outdir(path):
    os.makedirs(path, exist_ok=True)


def open_sensor(addr_int):
    # Initialize I2C and sensor
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = Adafruit_BMP280_I2C(i2c, address=addr_int)
    # Optional: tweak settings if desired (leaving defaults is fine for 5-min sampling)
    # sensor.sea_level_pressure = 1013.25  # hPa (set if you want altitude())
    return sensor


def timestamp_str():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_filename(prefix, outdir):
    stamp = dt.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    name = f"{prefix}_{stamp}.log"
    return os.path.join(outdir, name)


def seconds_to_next_boundary(interval_s):
    now = time.time()
    return interval_s - (int(now) % interval_s)


def main():
    args = parse_args()
    try:
        addr_int = int(args.addr, 16)
    except ValueError:
        print(f"Invalid --addr '{args.addr}'. Use hex like 0x76 or 0x77.", file=sys.stderr)
        sys.exit(2)

    if args.interval <= 0:
        print("--interval must be > 0", file=sys.stderr)
        sys.exit(2)

    ensure_outdir(args.outdir)

    # Handle graceful shutdown (Ctrl+C, SIGTERM)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Open sensor
    try:
        sensor = open_sensor(addr_int)
    except Exception as e:
        print(f"Failed to initialize BMP280 at {hex(addr_int)}: {e}", file=sys.stderr)
        sys.exit(1)

    # Create a new file per run
    filepath = make_filename(args.prefix, args.outdir)
    print(f"[{timestamp_str()}] Logging to {filepath} (addr={hex(addr_int)}, interval={args.interval}s)")
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "i2c_addr", "temp_C", "pressure_hPa"])
        f.flush()

        # If alignment requested, wait to the next wall-clock boundary
        if args.align:
            sleep_s = seconds_to_next_boundary(args.interval)
            if 0 < sleep_s < args.interval:
                time.sleep(sleep_s)

        # Loop
        while not STOP:
            ts = timestamp_str()
            try:
                temp_c = float(sensor.temperature)         # °C
                pressure_hpa = float(sensor.pressure)      # hPa
                writer.writerow([ts, hex(addr_int), f"{temp_c:.3f}", f"{pressure_hpa:.3f}"])
                f.flush()
                print(f"{ts}, addr={hex(addr_int)}, T={temp_c:.3f} °C, P={pressure_hpa:.3f} hPa")
            except Exception as e:
                # Log a row with NaNs on read error instead of crashing
                writer.writerow([ts, hex(addr_int), "nan", "nan"])
                f.flush()
                print(f"{ts} READ ERROR: {e}", file=sys.stderr)

            # Sleep until next sample (aligned next boundary if requested)
            if args.align:
                sleep_s = seconds_to_next_boundary(args.interval)
            else:
                sleep_s = args.interval

            # Allow quick shutdown while sleeping
            end_time = time.time() + sleep_s
            while not STOP and time.time() < end_time:
                time.sleep(min(0.5, end_time - time.time()))

    print(f"[{timestamp_str()}] Stopped.")


if __name__ == "__main__":
    main()
