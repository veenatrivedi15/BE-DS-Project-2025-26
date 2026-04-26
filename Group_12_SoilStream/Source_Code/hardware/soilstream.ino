// ESP32 Complete Smart Irrigation System
// Install libraries:
// 1. Firebase ESP32 Client (by Mobizt)
// 2. Adafruit BME280 Library
// 3. Adafruit Unified Sensor

#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

// ==========================================
// CONFIGURATION
// ==========================================
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define API_KEY "YOUR_FIREBASE_API_KEY"
#define DATABASE_URL "YOUR_FIREBASE_DATABASE_URL" // e.g. https://your-project.firebaseio.com/
#define DEVICE_ID "DEVICE_001"

// ==========================================
// PIN CONFIGURATION
// ==========================================
const int sensorPin = 34;     // Soil moisture sensor (analog)
const int pump = 5;           // Pump relay pin
const int dryValue = 4000;
const int wetValue = 3000;

// BME280 I2C: SDA = GPIO 21, SCL = GPIO 22

// ==========================================
// OBJECTS
// ==========================================
Adafruit_BME280 bme;
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

unsigned long sendDataPrevMillis = 0;
unsigned long pumpCheckMillis = 0;
bool signupOK = false;

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=================================");
  Serial.println("ESP32 Smart Irrigation System");
  Serial.println("=================================\n");
  
  // Initialize pump
  pinMode(pump, OUTPUT);
  digitalWrite(pump, LOW); // Pump OFF initially
  
  // Initialize I2C for BME280
  Wire.begin(21, 22);
  
  // Initialize BME280
  Serial.println("Initializing BME280 sensor...");
  if (!bme.begin(0x77)) {  // Try 0x77, change to 0x76 if needed
    Serial.println("❌ Could not find BME280 sensor!");
    Serial.println("Check wiring: SDA=GPIO21, SCL=GPIO22, VCC=3.3V");
    // Continue without BME280 (only soil moisture will work)
  } else {
    Serial.println("✓ BME280 initialized successfully\n");
  }
  
  // Connect to WiFi
  connectWiFi();
  
  // Configure Firebase
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  
  // Firebase signup
  Serial.println("Signing up to Firebase...");
  if (Firebase.signUp(&config, &auth, "", "")) {
    Serial.println("✓ Firebase signup successful");
    signupOK = true;
  } else {
    Serial.printf("✗ Signup failed: %s\n", config.signer.signupError.message.c_str());
  }
  
  config.token_status_callback = tokenStatusCallback;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  
  Serial.println("\n✓ Setup complete! Starting monitoring...\n");
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
  // Send sensor data every 5 seconds
  if (Firebase.ready() && signupOK && (millis() - sendDataPrevMillis > 5000 || sendDataPrevMillis == 0)) {
    sendDataPrevMillis = millis();
    
    // Read soil moisture
    int soilRaw = analogRead(sensorPin);
    int moisturePercent = map(soilRaw, dryValue, wetValue, 0, 100);
    moisturePercent = constrain(moisturePercent, 0, 100);
    
    // Read BME280 data
    float temperature = bme.readTemperature();
    float humidity = bme.readHumidity();
    float pressure = bme.readPressure() / 100.0F; // Convert to hPa
    
    // Determine soil status
    String status;
    if (moisturePercent >= 70) {
      status = "Very Wet";
    } else if (moisturePercent <= 30) {
      status = "Dry - Needs Water";
    } else {
      status = "Moist (Good)";
    }
    
    // Print to Serial Monitor
    Serial.println("-----------------------------");
    Serial.println("📊 SENSOR READINGS:");
    Serial.print("Soil Moisture: ");
    Serial.print(moisturePercent);
    Serial.println("%");
    Serial.print("Raw Value: ");
    Serial.println(soilRaw);
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" °C");
    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.println(" %");
    Serial.print("Pressure: ");
    Serial.print(pressure);
    Serial.println(" hPa");
    Serial.print("Status: ");
    Serial.println(status);
    
    // Upload sensor data to Firebase
    String sensorPath = "devices/" + String(DEVICE_ID) + "/sensors";
    FirebaseJson sensorJson;
    sensorJson.set("moisture", moisturePercent);
    sensorJson.set("rawValue", soilRaw);
    sensorJson.set("temperature", temperature);
    sensorJson.set("humidity", humidity);
    sensorJson.set("pressure", pressure);
    sensorJson.set("status", status);
    sensorJson.set("timestamp", (int)millis());
    sensorJson.set("deviceId", DEVICE_ID);
    
    Serial.print("📤 Uploading sensor data... ");
    if (Firebase.RTDB.setJSON(&fbdo, sensorPath.c_str(), &sensorJson)) {
      Serial.println("✓ SUCCESS");
    } else {
      Serial.println("✗ FAILED");
      Serial.println("Reason: " + fbdo.errorReason());
    }
    
    // Trigger rainfall prediction
    String predictionPath = "devices/" + String(DEVICE_ID) + "/predictionTrigger";
    FirebaseJson triggerJson;
    triggerJson.set("temperature", temperature);
    triggerJson.set("humidity", humidity);
    triggerJson.set("pressure", pressure);
    triggerJson.set("soilMoisture", moisturePercent);
    triggerJson.set("requestTime", (int)millis());
    
    Serial.print("🌧️ Triggering rainfall prediction... ");
    if (Firebase.RTDB.setJSON(&fbdo, predictionPath.c_str(), &triggerJson)) {
      Serial.println("✓ SENT");
    } else {
      Serial.println("✗ FAILED");
    }
    
    Serial.println("-----------------------------\n");
  }
  
  // Check pump control from Firebase every 2 seconds
  if (Firebase.ready() && signupOK && (millis() - pumpCheckMillis > 2000 || pumpCheckMillis == 0)) {
    pumpCheckMillis = millis();
    
    String pumpCommandPath = "devices/" + String(DEVICE_ID) + "/pumpControl/command";
    
    Serial.println("\n========== PUMP CHECK ==========");
    Serial.print("Reading from: ");
    Serial.println(pumpCommandPath);
    
    if (Firebase.RTDB.getBool(&fbdo, pumpCommandPath.c_str())) {
      bool shouldPumpBeOn = fbdo.boolData();
      
      Serial.print("✅ Got command from Firebase: ");
      Serial.println(shouldPumpBeOn ? "TRUE (should be ON)" : "FALSE (should be OFF)");
      
      // Use ORIGINAL logic (HIGH = ON)
      digitalWrite(pump, shouldPumpBeOn ? HIGH : LOW);
      
      Serial.print("⚡ Set GPIO 5 to: ");
      Serial.println(shouldPumpBeOn ? "HIGH" : "LOW");
      
      Serial.print("💧 PUMP: ");
      Serial.println(shouldPumpBeOn ? "ON ✓" : "OFF ✗");
      
      // Update pump status in Firebase
      String pumpStatusPath = "devices/" + String(DEVICE_ID) + "/pumpControl/status";
      if (Firebase.RTDB.setBool(&fbdo, pumpStatusPath.c_str(), shouldPumpBeOn)) {
        Serial.println("✅ Updated status in Firebase");
      } else {
        Serial.println("❌ Failed to update status");
      }
      
    } else {
      Serial.println("❌ FAILED to read pump command from Firebase!");
      Serial.print("Error reason: ");
      Serial.println(fbdo.errorReason());
      Serial.print("Error code: ");
      Serial.println(fbdo.httpCode());
    }
    
    Serial.println("================================\n");
  }
}

// ==========================================
// CONNECT TO WIFI
// ==========================================
void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ WiFi connection failed!");
  }
}