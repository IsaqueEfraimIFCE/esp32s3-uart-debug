"""Listen on COM5 across all four DTR/RTS states, set BEFORE the port opens.

On boards with the auto-reset transistor pair, opening a port with DTR/RTS
asserted can pin EN low and hold the chip in reset forever -- which looks
exactly like a dead board. Setting the lines before open avoids that.
"""
import time

import serial

PORT = "COM5"
LISTEN = 5.0

for dtr in (False, True):
    for rts in (False, True):
        try:
            ser = serial.Serial()
            ser.port = PORT
            ser.baudrate = 115200
            ser.timeout = 0.3
            ser.dtr = dtr          # applied at open, not after
            ser.rts = rts
            ser.open()
        except Exception as e:
            print(f"dtr={dtr:<5} rts={rts:<5} : OPEN FAILED {e.__class__.__name__}: {e}")
            continue

        with ser:
            buf = b""
            end = time.time() + LISTEN
            while time.time() < end:
                buf += ser.read(4096)

        print(f"dtr={dtr:<5} rts={rts:<5} : {len(buf):>5} bytes")
        if buf:
            print("   " + repr(buf.decode("utf-8", "replace")[:600]))
