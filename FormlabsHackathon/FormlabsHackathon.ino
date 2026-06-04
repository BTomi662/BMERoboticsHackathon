#include "camera.h"

const char* ssid = "Yodaphone 5G";
const char* password = "Abqdzwre-m1n1";

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Connected");
  delay(500);

  setupCamera();
  setupWebServer(ssid,password);

}

void loop() {
  delay(10);
}
