# ESP32-S3 on COM5 — diagnostic findings

Session date: 2026-08-16. Project: `C:\Users\Isaque\Desktop\LIT\test_apps\esp-dl`.

## Conclusion

**The UART TX path from the ESP32-S3 to the CH343 bridge is physically severed.**
The user later reported that during desoldering, several pads tore the copper
away with them — VIN, GND, **and the TX pin**.

That single fact explains the entire symptom set. It is a hardware fault; no
software change can recover it.

**The chip itself is probably fine.** Every "the chip is dead" inference during
this session was drawn from silence, and a cut TX trace produces identical
silence from a perfectly healthy chip. It has likely been booting and printing
into a broken trace the whole time.

## The defining signature: a strictly one-way link

| Direction | How tested | Result |
|---|---|---|
| Host → ESP32 | Blue TX LED blinks steadily under continuous data, dark when idle | **Works** |
| ESP32 → Host | 6 baud rates, 4 DTR/RTS states, auto-reset, manual RESET, manual BOOT+RESET, `--before no-reset` sync | **0 bytes, every time** |

Not one byte was ever received from the board, under any condition, across the
whole session. Meanwhile outbound data demonstrably arrived. Only a broken
return path explains both at once.

## What was ruled out (with evidence)

- **Cable** — the same cable produced steady blue TX-activity blinks, proving its
  data lines carry traffic. Definitively not charge-only.
- **Power** — red LED lit from the native USB port alone.
- **Baud rate** — swept 115200 / 74880 / 921600 / 460800 / 230400 / 9600. A wrong
  baud yields garbage bytes; we got *zero* bytes, which is a different failure.
- **DTR/RTS holding the chip in reset** — all four line states tested with the
  lines set *before* port open. Silent in every combination.
- **Driver / config** — CH343 enumerated fine; `sdkconfig` correctly specifies
  `esp32s3`, UART0, 115200.
- **Firmware state** — manual BOOT+RESET forces ROM download mode regardless of
  what is on flash. Still silent.

## Unresolved

- **Native USB (USB-Serial-JTAG, `VID_303A&PID_1001`) never enumerated** this
  session, despite having worked on this machine before as **COM15** with MAC
  `24:EC:4A:C7:F5:38`. It runs on GPIO19/20, independent of UART0 and the torn
  TX pad, so it *should* be unaffected by that damage.
- Suspected cause: **the torn GND pads**. USB needs a solid ground return; a
  marginal ground can pass enough current to light an LED while still failing
  USB signalling.
- **Never tested:** BOOT-hold-while-plugging on the native USB port, and a
  multimeter continuity check on ground. These were the two open action items.

## Also observed

The CH343 repeatedly enumerated and dropped off the bus on its own (same serial
`5A45061937`, same location `1-7`), including disconnecting mid-read. Possibly
related to the damaged VIN/GND pads. It later held stable for minutes at a time,
so this is intermittent, not the primary fault.

## Recommended next steps

1. **Prefer the native USB port** — it bypasses the CH343, UART0, and the torn TX
   pad entirely, and gives both flashing and console. Fix ground first.
2. **Check ground continuity** — multimeter continuity between the native USB
   connector shell and the ESP32 module GND; should be ~0Ω. Usually an easy bodge.
3. **If the UART path is wanted back** — bodge a thin wire from the module's TX
   castellation (GPIO43 / U0TXD) to the CH343's RX pin.
4. Measure EN — should sit at ~3.3V; near 0V means it is held in reset.

## Scripts kept here

- `serial_watch.py` — retrying opener/reader for one port, optional reset pulse.
- `keep_connecting.py` — alternates esptool sync with post-reset passive listen.
- `watch_any_port.py` — polls the whole port list, pounces on any new port,
  logs VID:PID, survives mid-read disconnects.
- `baud_sweep.py` — reset + listen across six baud rates.
- `line_matrix.py` — listens across all four DTR/RTS states, set before open.
- `led_experiment.py` — three labeled phases for correlating LEDs by eye
  (continuous TX / silence / slow reset pulses). Run it yourself so the phase
  labels print live while you watch the board.

`task-output/` holds the raw background-task logs.

### Caveat on the LED experiment

Phase 3 asked whether either LED moved during reset pulses, to test if DTR/RTS
drives EN. **That test was invalid**: red is a power LED (a reset does not drop
the 3.3V rail) and blue is a TX-activity light (no data was sent in that phase).
Neither LED can indicate a reset, so "nothing happened" proved nothing about the
auto-reset wiring. That question remains open — though it is now moot, since
manual BOOT+RESET bypasses auto-reset and also failed.
