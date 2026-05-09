# Pico controller sketch for Nintendo Switch automation

This folder contains the Raspberry Pi Pico / Pico H Arduino sketch used in my Switch automation setup.

The sketch identifies the Pico as a Switch compatible HID controller and accepts simple serial commands over `Serial1` at `115200` baud. Each supported command triggers a corresponding button press or D-pad input on the console.

## What this is for

This code is provided as a reference for the Pico side of the setup. It may be useful for people who want to understand, reproduce, or adapt the controller input portion of the method.

## Requirements

- Raspberry Pi Pico or Pico H
- Arduino IDE or another compatible Arduino build environment for Pico boards
- The required Switch HID support dependency used by the sketch:
  - `switch_tinyusb.h` [link](https://github.com/touchgadget/switch_tinyusb/blob/main/switch_tinyusb.h)

## Supported serial commands

Send one of the following commands followed by a newline:

- `A`
- `B`
- `X`
- `Y`
- `UP`
- `DOWN`
- `LEFT`
- `RIGHT`
- `HOME`
- `ABXY`
- `STOP`

## Command behavior

- `A`, `B`, `X`, `Y`, and `HOME` perform a short button press
- `UP`, `DOWN`, `LEFT`, and `RIGHT` perform a short D-pad press, then return to centered
- `ABXY` presses A, B, X, and Y together for about 1 second, then releases
- `STOP` releases all held inputs

## Implementation notes

- `Serial1` is initialized at `115200`
- The sketch waits for the USB device to mount before continuing
- The USB device ID is set in `setup()`
- Input handling is intentionally simple and command based

## Files

- `pico_switch_controller.ino` - main Pico sketch

## Notes

This is a minimal reference implementation, not a polished end user package. Anyone using it should review the code, verify the required dependencies, and test carefully on their own hardware.

Use at your own risk.
