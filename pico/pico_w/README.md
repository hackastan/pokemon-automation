## What this is for

This code is provided as a reference for the Pico W side of a setup. It may be useful for people who want to understand, reproduce, or create their own automation on a switch.

## Requirements

- Raspberry Pi Pico 2 W
- Arduino IDE or another compatible Arduino build environment for Pico boards
- [this pico library](https://github.com/earlephilhower/arduino-pico)
- The required Switch HID support dependency used by the sketch:
  - `switch_tinyusb.h` [link](https://github.com/touchgadget/switch_tinyusb/blob/main/switch_tinyusb.h)

## Supported http commands

Send one of the following commands followed by a newline:

### Buttons
- `curl http://IP_HERE/press?cmd=A`
- `curl http://IP_HERE/press?cmd=B`
- `curl http://IP_HERE/press?cmd=X`
- `curl http://IP_HERE/press?cmd=Y`
- `curl http://IP_HERE/press?cmd=L`
- `curl http://IP_HERE/press?cmd=R`
- `curl http://IP_HERE/press?cmd=ZL`
- `curl http://IP_HERE/press?cmd=ZR`
- `curl http://IP_HERE/press?cmd=PLUS`
- `curl http://IP_HERE/press?cmd=MINUS`
- `curl http://IP_HERE/press?cmd=HOME`
- `curl http://IP_HERE/press?cmd=CAPTURE`
- `curl http://IP_HERE/press?cmd=UP`
- `curl http://IP_HERE/press?cmd=DOWN`
- `curl http://IP_HERE/press?cmd=LEFT`
- `curl http://IP_HERE/press?cmd=RIGHT`
- `curl http://IP_HERE/press?cmd=ABXY`
- `curl http://IP_HERE/press?cmd=STOP`
- `curl http://IP_HERE/status`

## Command behavior

- All button and D-pad commands perform a 100 ms press then release
- D-pad commands return to centered after release
- `ABXY` presses A, B, X, and Y together for 1 second, then releases all
- `STOP` immediately releases all held inputs
- Commands are case-insensitive

## Implementation notes

- The USB device ID is set in `setup()`
- Input handling is intentionally simple and command based

## Files

- `pico_w_switch_controller.ino` - main Pico sketch

## Notes

This is a minimal reference implementation, not a polished end user package. Anyone using it should review the code, verify the required dependencies, and test carefully on their own hardware.

Use at your own risk.
