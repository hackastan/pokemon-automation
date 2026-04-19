# Pokémon Automation

Closed-loop automation scripts for Pokémon FireRed/LeafGreen using a Raspberry Pi Pico,
a USB capture card, and Python/OpenCV for visual detection.

## Projects

### `shiny_hunter.py`
Automates soft-reset shiny hunting. Detects the yellow star indicator via HSV color
detection and stops the macro automatically when a shiny is found. Optionally saves
an OBS replay buffer clip on detection.

### `nugget_bridge.py`
Automates the Nugget Bridge trainer loop in FireRed/LeafGreen. Walks the route,
fights the Rattata trainer, and loops back. Uses purple pixel detection to know
when the battle ends.

## Hardware Required

- Raspberry Pi Pico (flashed with the controller firmware)
- USB capture card (Elgato HD60 X or Magewell USB Capture HDMI Gen 2)
- GBA or Switch running FireRed/LeafGreen via capture card

## Software Dependencies

```bash
pip install opencv-python numpy pyserial obsws-python
```

## Setup

1. Flash your Raspberry Pi Pico with the controller firmware
2. Run `tools/find_devices.py` to find your capture card index
3. Open the script you want to use and set `COM_PORT` to your Pico's port
   - Windows: `"COM5"` (check Device Manager)
   - Mac/Linux: `"/dev/ttyACM0"`
4. Set `CAPTURE_INDEX` to the number from step 2, or leave it as `None` to auto-detect
5. Run the script and type `STARTMACRO` to begin

## Tools

| Script | Purpose |
|---|---|
| `tools/find_devices.py` | Lists all capture card indices and resolutions |
| `tools/check_res.py` | Checks what resolution each capture index reports |
| `tools/find_coords.py` | Click on a live frame to get pixel coordinates |
| `tools/star_test.py` | Live preview of shiny star detection region and mask |

## Commands (while running)

| Command | Effect |
|---|---|
| `STARTMACRO` | Begin the macro |
| `STOPMACRO` | Stop the macro (program stays open) |
| `EXIT` | Close the program |
| `TESTDETECT` | Run detection on the current screen (`nugget_bridge.py`) |
| `TESTMACRO` | Run detection on the current screen (`shiny_hunter.py`) |
| `STARTWALK` | Skip straight to the walk sequence (`nugget_bridge.py`) |
| `A B X Y UP DOWN LEFT RIGHT` | Send a single button press manually |

## Notes

- Log files are saved automatically in the same folder as the script
- `shiny_hunter.py` requires OBS to be open with WebSocket and Replay Buffer enabled for clip saving — it works without OBS but won't save clips
- Detection regions are tuned for a 1920x1080 capture feed — if your resolution differs, use `tools/find_coords.py` to recalibrate
