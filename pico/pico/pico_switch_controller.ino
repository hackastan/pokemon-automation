#include "switch_tinyusb.h"

Adafruit_USBD_HID G_usb_hid;
NSGamepad Gamepad(&G_usb_hid);

void setup() {
  USBDevice.setID(0x0f0d, 0x0092);
  Gamepad.begin();
  while (!USBDevice.mounted()) delay(1);
  Serial1.begin(115200);
}

void pressButton(uint8_t button, int duration_ms) {
  Gamepad.press(button);
  if (Gamepad.ready()) Gamepad.loop();
  delay(duration_ms);
  Gamepad.releaseAll();
  if (Gamepad.ready()) Gamepad.loop();
  delay(50);
}

void loop() {
  if (Serial1.available()) {
    String cmd = Serial1.readStringUntil('\n');
    cmd.trim();

    if (cmd == "A")          pressButton(NSButton_A, 100);
    else if (cmd == "B")     pressButton(NSButton_B, 100);
    else if (cmd == "X")     pressButton(NSButton_X, 100);
    else if (cmd == "Y")     pressButton(NSButton_Y, 100);
    else if (cmd == "UP")    { Gamepad.dPad(NSGAMEPAD_DPAD_UP);    if(Gamepad.ready()) Gamepad.loop(); delay(100); Gamepad.dPad(NSGAMEPAD_DPAD_CENTERED); if(Gamepad.ready()) Gamepad.loop(); }
    else if (cmd == "DOWN")  { Gamepad.dPad(NSGAMEPAD_DPAD_DOWN);  if(Gamepad.ready()) Gamepad.loop(); delay(100); Gamepad.dPad(NSGAMEPAD_DPAD_CENTERED); if(Gamepad.ready()) Gamepad.loop(); }
    else if (cmd == "LEFT")  { Gamepad.dPad(NSGAMEPAD_DPAD_LEFT);  if(Gamepad.ready()) Gamepad.loop(); delay(100); Gamepad.dPad(NSGAMEPAD_DPAD_CENTERED); if(Gamepad.ready()) Gamepad.loop(); }
    else if (cmd == "RIGHT") { Gamepad.dPad(NSGAMEPAD_DPAD_RIGHT); if(Gamepad.ready()) Gamepad.loop(); delay(100); Gamepad.dPad(NSGAMEPAD_DPAD_CENTERED); if(Gamepad.ready()) Gamepad.loop(); }
    else if (cmd == "HOME")  pressButton(NSButton_Home, 100);
    else if (cmd == "ABXY") {
      Gamepad.press(NSButton_A);
      Gamepad.press(NSButton_B);
      Gamepad.press(NSButton_X);
      Gamepad.press(NSButton_Y);
      if (Gamepad.ready()) Gamepad.loop();
      delay(1000);
      Gamepad.releaseAll();
      if (Gamepad.ready()) Gamepad.loop();
      delay(50);
    }
    else if (cmd == "STOP")  Gamepad.releaseAll();
  }
}