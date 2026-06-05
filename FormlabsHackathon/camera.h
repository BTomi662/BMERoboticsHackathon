#include "esp_camera.h"
#include "ESP32_OV5640_AF.h"
#include <WiFi.h>

void setupCamera();
void setupWebServer(const char* ssid, const char* password);