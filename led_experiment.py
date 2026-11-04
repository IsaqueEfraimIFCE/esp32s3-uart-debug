"""Three clearly-separated phases so a human can correlate LED behaviour.

We want to distinguish:
  * blue LED == TX activity (data leaving the host toward the ESP32)
  * whether toggling DTR/RTS actually drives EN/BOOT on this board
Each phase is announced and slow enough to watch by eye.
"""
import sys
import time

import serial

PORT = "COM5"


def banner(msg):
    print("\n" + "=" * 60, flush=True)
    print(msg, flush=True)
    print("=" * 60, flush=True)


def open_port():
    ser = serial.Serial()
    ser.port = PORT
    ser.baudrate = 115200
    ser.timeout = 0.2
    ser.dtr = False
    ser.rts = False
    ser.open()
    return ser


try:
    ser = open_port()
except Exception as e:
    print(f"cannot open {PORT}: {e}")
    sys.exit(1)

rx_total = 0

banner("GET READY -- look at the board now.\n"
       "Phase 1 starts in 10 seconds. Watch the BLUE LED.")
for n in range(10, 0, -1):
    print(f"  starting in {n}...", flush=True)
    time.sleep(1.0)

with ser:
    banner("PHASE 1 (10s): SENDING DATA CONTINUOUSLY -- watch the BLUE LED.\n"
           "If blue is a TX light it should blink steadily for 10 seconds.")
    end = time.time() + 10
    while time.time() < end:
        ser.write(b"U" * 64)   # 0x55 = alternating bits, maximum edges
        ser.flush()
        rx_total += len(ser.read(4096))
        time.sleep(0.1)
    print(f"phase 1 done. bytes received back: {rx_total}", flush=True)

    banner("PHASE 2 (10s): COMPLETE SILENCE -- sending nothing at all.\n"
           "The BLUE LED should be DARK/STILL this whole time.")
    end = time.time() + 10
    got = 0
    while time.time() < end:
        got += len(ser.read(4096))
    rx_total += got
    print(f"phase 2 done. bytes received unprompted: {got}", flush=True)

    banner("PHASE 3 (~16s): SLOW RESET PULSES -- watch BOTH LEDs.\n"
           "4 cycles: EN held LOW 2s, then released 2s.\n"
           "If reset wiring works the board reboots on each release.")
    for i in range(1, 5):
        print(f"  cycle {i}: EN LOW  (RTS asserted) ...", flush=True)
        ser.setRTS(True)
        ser.setDTR(False)
        time.sleep(2.0)
        print(f"  cycle {i}: EN HIGH (released)  ...", flush=True)
        ser.setRTS(False)
        time.sleep(2.0)
        got = len(ser.read(4096))
        rx_total += got
        if got:
            print(f"  >>> cycle {i} PRODUCED {got} BYTES", flush=True)

print(f"\nTOTAL BYTES EVER RECEIVED FROM BOARD: {rx_total}")
