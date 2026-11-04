"""Watch for ANY serial port to appear, then connect and dump the console.

COM5 was the CH343 UART bridge. The ESP32-S3's native USB-Serial-JTAG
enumerates as a *different* device (VID_303A) and will almost certainly get
a different COM number, so pinning to COM5 would miss it. This polls the
whole port list and pounces on whatever shows up.
"""
import argparse
import sys
import time

import serial
from serial.tools import list_ports


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def snapshot():
    """Map of device name -> human description for every present port."""
    return {p.device: f"{p.description} [{p.hwid}]" for p in list_ports.comports()}


def hard_reset(ser):
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setDTR(True)
    ser.setRTS(False)
    time.sleep(0.05)
    ser.setDTR(False)


def drain(port, seconds, reset):
    """Listen on a port. Native USB-JTAG needs no reset pulse to talk."""
    try:
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = 115200
        ser.timeout = 0.3
        ser.dtr = False
        ser.rts = False
        ser.open()
    except Exception as e:
        log(f"  open {port} failed: {e.__class__.__name__}: {e}")
        return b""

    buf = b""
    try:
        with ser:
            if reset:
                hard_reset(ser)
            end = time.time() + seconds
            while time.time() < end:
                buf += ser.read(4096)
    except Exception as e:
        # The device yanking itself off the bus mid-read surfaces here as
        # "Access denied". Keep whatever we captured and let the caller
        # carry on watching instead of dying.
        log(f"  {port} dropped mid-read: {e.__class__.__name__}: {e}")
    return buf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--interval", type=float, default=2.0)
    args = ap.parse_args()

    deadline = time.time() + args.timeout
    known = snapshot()
    log(f"baseline ports: {known if known else 'NONE'}")
    log("waiting for any port to appear...")

    while time.time() < deadline:
        time.sleep(args.interval)
        now = snapshot()

        for gone in set(known) - set(now):
            log(f"PORT REMOVED: {gone}")
        for new in set(now) - set(known):
            log(f"PORT APPEARED: {new} -> {now[new]}")
            time.sleep(1.5)  # let the driver settle before opening

            # Native USB-JTAG usually prints without any reset nudge.
            buf = drain(new, 5.0, reset=False)
            if not buf:
                log(f"  passive listen silent; trying reset pulse")
                buf = drain(new, 6.0, reset=True)

            if buf:
                log(f"  GOT {len(buf)} BYTES from {new}")
                sys.stdout.write(buf.decode("utf-8", "replace"))
                sys.stdout.flush()
                log("  streaming...")
                more = drain(new, min(40.0, max(1.0, deadline - time.time())), reset=False)
                sys.stdout.write(more.decode("utf-8", "replace"))
                sys.stdout.flush()
                return 0
            log(f"  {new} present but silent")

        known = now

    log("gave up: no port ever produced data")
    return 1


if __name__ == "__main__":
    sys.exit(main())
