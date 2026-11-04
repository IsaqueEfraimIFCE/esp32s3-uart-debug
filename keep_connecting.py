"""Keep trying to reach the ESP32-S3 on COM5 until it answers.

Each round does two things:
  1. an esptool sync handshake (proves the ROM bootloader is reachable)
  2. a passive listen after a reset pulse (catches an app that boots and
     prints but won't drop into download mode)

Runs until success or --timeout, then dumps the console log on success.
"""
import argparse
import subprocess
import sys
import time

import serial

PORT = "COM5"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def hard_reset(ser):
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setDTR(True)
    ser.setRTS(False)
    time.sleep(0.05)
    ser.setDTR(False)


def try_listen(seconds=4.0):
    """Return bytes captured after a reset pulse, or None if port unusable."""
    try:
        with serial.Serial(PORT, 115200, timeout=0.3) as ser:
            hard_reset(ser)
            buf = b""
            end = time.time() + seconds
            while time.time() < end:
                buf += ser.read(4096)
            return buf
    except Exception as e:
        log(f"port unavailable: {e.__class__.__name__}: {e}")
        return None


def try_sync():
    """Run esptool chip-id. Returns (ok, output)."""
    proc = subprocess.run(
        [sys.executable, "-m", "esptool", "--port", PORT,
         "--baud", "115200", "--connect-attempts", "2", "chip-id"],
        capture_output=True, text=True, timeout=120,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def stream_console(seconds):
    log(f"streaming console for {seconds:.0f}s")
    try:
        with serial.Serial(PORT, 115200, timeout=0.5) as ser:
            hard_reset(ser)
            end = time.time() + seconds
            while time.time() < end:
                data = ser.read(4096)
                if data:
                    sys.stdout.write(data.decode("utf-8", "replace"))
                    sys.stdout.flush()
    except Exception as e:
        log(f"stream ended: {e.__class__.__name__}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--interval", type=float, default=10.0)
    args = ap.parse_args()

    deadline = time.time() + args.timeout
    rnd = 0
    log(f"watching {PORT}; will retry until success or {args.timeout/60:.0f} min elapse")

    while time.time() < deadline:
        rnd += 1

        buf = try_listen()
        if buf:
            log(f"ROUND {rnd}: GOT {len(buf)} BYTES on the wire")
            sys.stdout.write(buf.decode("utf-8", "replace"))
            sys.stdout.flush()
            stream_console(min(30.0, deadline - time.time()))
            return 0

        ok, out = try_sync()
        if ok:
            log(f"ROUND {rnd}: SYNC OK")
            print(out, flush=True)
            stream_console(min(30.0, deadline - time.time()))
            return 0

        log(f"ROUND {rnd}: silent (no bytes, no sync)")
        time.sleep(args.interval)

    log("gave up: board never responded")
    return 1


if __name__ == "__main__":
    sys.exit(main())
