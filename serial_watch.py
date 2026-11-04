"""Keep trying to open COM5 and dump whatever the ESP32-S3 prints.

Retries the open forever (until --timeout), survives unplug/replug, and
optionally pulses the auto-reset lines so a quiet board reboots and emits
its ROM banner.
"""
import argparse
import sys
import time

import serial


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="COM5")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--timeout", type=float, default=60.0, help="total seconds to run")
    p.add_argument("--reset", action="store_true", help="pulse DTR/RTS to reboot the chip")
    return p.parse_args()


def hard_reset(ser):
    """esptool's classic reset: EN low via RTS, then release."""
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setDTR(True)
    ser.setRTS(False)
    time.sleep(0.05)
    ser.setDTR(False)


def main():
    args = parse_args()
    deadline = time.time() + args.timeout
    attempt = 0
    total_bytes = 0

    while time.time() < deadline:
        attempt += 1
        try:
            ser = serial.Serial(args.port, args.baud, timeout=0.5)
        except Exception as e:  # port busy, missing, or access denied
            print(f"[attempt {attempt}] open failed: {e.__class__.__name__}: {e}", flush=True)
            time.sleep(1.0)
            continue

        print(f"[attempt {attempt}] OPEN {args.port} @ {args.baud}", flush=True)
        with ser:
            if args.reset:
                hard_reset(ser)
                print("[reset] pulsed DTR/RTS", flush=True)
            try:
                while time.time() < deadline:
                    data = ser.read(4096)
                    if data:
                        total_bytes += len(data)
                        sys.stdout.write(data.decode("utf-8", "replace"))
                        sys.stdout.flush()
            except Exception as e:
                print(f"\n[read error] {e.__class__.__name__}: {e}", flush=True)
                time.sleep(1.0)

    print(f"\n[done] attempts={attempt} bytes_read={total_bytes}", flush=True)


if __name__ == "__main__":
    main()
