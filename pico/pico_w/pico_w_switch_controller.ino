#include "switch_tinyusb.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiServer.h>

// ---------------------------------------------------------------------------
// Wi-Fi credentials
// ---------------------------------------------------------------------------
const char *WIFI_SSID = "your_wifi_name_here";
const char *WIFI_PASS = "your_wifi_password_here";

// ---------------------------------------------------------------------------
// Gamepad setup — identical to your friend's code
// ---------------------------------------------------------------------------
Adafruit_USBD_HID G_usb_hid;
NSGamepad Gamepad(&G_usb_hid);

WiFiServer server(80);

// ---------------------------------------------------------------------------
// setup
// ---------------------------------------------------------------------------
void setup() {
  USBDevice.setID(0x0f0d, 0x0092);
  Gamepad.begin();
  while (!USBDevice.mounted()) delay(1);

  // Optional: keep Serial for debug output via USB serial monitor
  Serial.begin(115200);

  // Connect to Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected! IP: ");
  Serial.println(WiFi.localIP());

  server.begin();
}

// ---------------------------------------------------------------------------
// Button press helper — copied directly from your friend's code
// ---------------------------------------------------------------------------
void pressButton(uint8_t button, int duration_ms) {
  Gamepad.press(button);
  if (Gamepad.ready()) Gamepad.loop();
  delay(duration_ms);
  Gamepad.releaseAll();
  if (Gamepad.ready()) Gamepad.loop();
  delay(50);
}

// ---------------------------------------------------------------------------
// DPad press helper
// ---------------------------------------------------------------------------
void pressDpad(uint8_t direction, int duration_ms) {
  Gamepad.dPad(direction);
  if (Gamepad.ready()) Gamepad.loop();
  delay(duration_ms);
  Gamepad.dPad(NSGAMEPAD_DPAD_CENTERED);
  if (Gamepad.ready()) Gamepad.loop();
  delay(50);
}

// ---------------------------------------------------------------------------
// Execute a command string — same logic as friend's UART parser,
// now shared by both HTTP and UART paths
// ---------------------------------------------------------------------------
String executeCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "A")          { pressButton(NSButton_A, 100);     return "{\"ok\":true,\"cmd\":\"A\"}"; }
  else if (cmd == "B")     { pressButton(NSButton_B, 100);     return "{\"ok\":true,\"cmd\":\"B\"}"; }
  else if (cmd == "X")     { pressButton(NSButton_X, 100);     return "{\"ok\":true,\"cmd\":\"X\"}"; }
  else if (cmd == "Y")     { pressButton(NSButton_Y, 100);     return "{\"ok\":true,\"cmd\":\"Y\"}"; }
  else if (cmd == "L")     { pressButton(NSButton_LeftTrigger, 100);  return "{\"ok\":true,\"cmd\":\"L\"}"; }
  else if (cmd == "R")     { pressButton(NSButton_RightTrigger, 100); return "{\"ok\":true,\"cmd\":\"R\"}"; }
  else if (cmd == "ZL")    { pressButton(NSButton_LeftThrottle, 100);  return "{\"ok\":true,\"cmd\":\"ZL\"}"; }
  else if (cmd == "ZR")    { pressButton(NSButton_RightThrottle, 100); return "{\"ok\":true,\"cmd\":\"ZR\"}"; }
  else if (cmd == "PLUS")  { pressButton(NSButton_Plus, 100);  return "{\"ok\":true,\"cmd\":\"PLUS\"}"; }
  else if (cmd == "MINUS") { pressButton(NSButton_Minus, 100); return "{\"ok\":true,\"cmd\":\"MINUS\"}"; }
  else if (cmd == "HOME")  { pressButton(NSButton_Home, 100);  return "{\"ok\":true,\"cmd\":\"HOME\"}"; }
  else if (cmd == "CAPTURE") { pressButton(NSButton_Capture, 100); return "{\"ok\":true,\"cmd\":\"CAPTURE\"}"; }
  else if (cmd == "UP")    { pressDpad(NSGAMEPAD_DPAD_UP, 100);    return "{\"ok\":true,\"cmd\":\"UP\"}"; }
  else if (cmd == "DOWN")  { pressDpad(NSGAMEPAD_DPAD_DOWN, 100);  return "{\"ok\":true,\"cmd\":\"DOWN\"}"; }
  else if (cmd == "LEFT")  { pressDpad(NSGAMEPAD_DPAD_LEFT, 100);  return "{\"ok\":true,\"cmd\":\"LEFT\"}"; }
  else if (cmd == "RIGHT") { pressDpad(NSGAMEPAD_DPAD_RIGHT, 100); return "{\"ok\":true,\"cmd\":\"RIGHT\"}"; }
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
    return "{\"ok\":true,\"cmd\":\"ABXY\"}";
  }
  else if (cmd == "STOP") {
    Gamepad.releaseAll();
    if (Gamepad.ready()) Gamepad.loop();
    return "{\"ok\":true,\"cmd\":\"STOP\"}";
  }

  return "{\"ok\":false,\"error\":\"unknown command\"}";
}

// ---------------------------------------------------------------------------
// HTTP request handler
//
// Accepts two styles:
//   POST /press        body: A
//   GET  /press?cmd=A  (handy for curl -G or browser testing)
//   GET  /status
// ---------------------------------------------------------------------------
void handleClient(WiFiClient &client) {
  String request = "";
  unsigned long timeout = millis() + 2000;

  // Read until blank line (end of headers) or timeout
  while (client.connected() && millis() < timeout) {
    if (client.available()) {
      char c = client.read();
      request += c;
      if (request.endsWith("\r\n\r\n")) break;
    }
  }

  // Read body if Content-Length is present
  String body = "";
  int cl_idx = request.indexOf("Content-Length:");
  if (cl_idx != -1) {
    int cl_end = request.indexOf("\r\n", cl_idx);
    int content_length = request.substring(cl_idx + 15, cl_end).toInt();
    timeout = millis() + 1000;
    while ((int)body.length() < content_length && millis() < timeout) {
      if (client.available()) body += (char)client.read();
    }
  }

  String response_body = "{\"ok\":false,\"error\":\"not found\"}";
  int status_code = 200;

  // Route: GET /status
  if (request.startsWith("GET /status")) {
    response_body = "{\"ok\":true,\"status\":\"ready\"}";
  }
  // Route: POST /press  (body is the command, e.g. "A")
  else if (request.startsWith("POST /press")) {
    body.trim();
    response_body = executeCommand(body);
  }
  // Route: GET /press?cmd=A  (useful for quick browser/curl testing)
  else if (request.startsWith("GET /press")) {
    int cmd_idx = request.indexOf("cmd=");
    if (cmd_idx != -1) {
      int cmd_end = request.indexOf(' ', cmd_idx);
      String cmd = request.substring(cmd_idx + 4, cmd_end);
      response_body = executeCommand(cmd);
    } else {
      status_code = 400;
      response_body = "{\"ok\":false,\"error\":\"missing cmd param\"}";
    }
  }
  else {
    status_code = 404;
  }

  // Send HTTP response
  client.print("HTTP/1.1 ");
  client.print(status_code);
  client.println(status_code == 200 ? " OK" :
                 status_code == 400 ? " Bad Request" : " Not Found");
  client.println("Content-Type: application/json");
  client.println("Connection: close");
  client.println();
  client.println(response_body);
  client.flush();
}

// ---------------------------------------------------------------------------
// loop
// ---------------------------------------------------------------------------
void loop() {
  // Handle HTTP clients
  WiFiClient client = server.available();
  if (client) {
    handleClient(client);
    client.stop();
  }

  // Keep UART working too — same as friend's original code
  // Useful for local debug or as a fallback
  if (Serial1.available()) {
    String cmd = Serial1.readStringUntil('\n');
    executeCommand(cmd);
  }
}