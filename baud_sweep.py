"""Reset the board and listen at several bauds, reporting raw byte counts.

If UART0 TX is alive but the console baud differs from the configured
115200, we still see *bytes* (garbage) rather than total silence. Total
silence at every baud means nothing is reaching the host at all.
"""
import time

import serial

PORT = "COM5"
BAUDS = [115200, 74880, 921600, 460800, 230400, 9600]


def hard_reset(ser):
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setDTR(True)
    ser.setRTS(False)
    time.sleep(0.05)
    ser.setDTR(False)


for baud in BAUDS:
    try:
        with serial.Serial(PORT, baud, timeout=0.3) as ser:
            hard_reset(ser)
            buf = b""
            end = time.time() + 3.0
            while time.time() < end:
                buf += ser.read(4096)
            cts = ser.cts
            dsr = ser.dsr
        printable = buf.decode("utf-8", "replace").strip()
        print(f"{baud:>7} : {len(buf):>5} bytes  cts={cts} dsr={dsr}")
        if buf:
            print(f"          {printable[:400]!r}")
    except Exception as e:
        print(f"{baud:>7} : ERROR {e.__class__.__name__}: {e}")
