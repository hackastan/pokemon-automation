## What this is for

This code is provided as a reference for the Pico W side of a setup. It may be useful for people who want to understand, reproduce, or create their own automation on a switch.

## Requirements

- Raspberry Pi Pico 2 W
- Arduino IDE or another compatible Arduino build environment for Pico boards
- [this pico library](https://github.com/earlephilhower/arduino-pico)
- The required Switch HID support dependency used by the sketch:
  - `switch_tinyusb.h` [link](https://github.com/touchgadget/switch_tinyusb/blob/main/switch_tinyusb.h)

## Supported serial commands

Send one of the following commands followed by a newline:

- `curl http://IP_HERE/press?cmd=A`
- `curl http://IP_HERE/press?cmd=B`
- `curl http://IP_HERE/press?cmd=X`
- `curl http://IP_HERE/press?cmd=Y`
- `curl http://IP_HERE/press?cmd=UP`
- `curl http://IP_HERE/press?cmd=DOWN`
- `curl http://IP_HERE/press?cmd=LEFT`
- `curl http://IP_HERE/press?cmd=RIGHT`
- `curl http://IP_HERE/press?cmd=HOME`
- `curl http://IP_HERE/press?cmd=ABXY`
- `curl http://IP_HERE/press?cmd=STOP`

## Command behavior

- `A`, `B`, `X`, `Y`, and `HOME` perform a short button press
- `UP`, `DOWN`, `LEFT`, and `RIGHT` perform a short D-pad press, then return to centered
- `ABXY` presses A, B, X, and Y together for about 1 second, then releases
- `STOP` releases all held inputs

## Implementation notes

- The USB device ID is set in `setup()`
- Input handling is intentionally simple and command based

## Files

- `pico_w_switch_controller.ino` - main Pico sketch

## Notes

This is a minimal reference implementation, not a polished end user package. Anyone using it should review the code, verify the required dependencies, and test carefully on their own hardware.

Use at your own risk.
