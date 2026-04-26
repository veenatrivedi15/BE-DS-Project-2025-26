# 🌱 SoilStream – Smart Solar-Powered IoT Irrigation System

SoilStream is an AI-powered smart agriculture system designed to automate irrigation, monitor real-time soil conditions, predict rainfall, diagnose crop diseases, and provide crop-specific recommendations using IoT sensors, machine learning, and intelligent APIs.

---

## 👥 Group Members

- Raj Choudhary (22107044)
- Siddesh Patil (22107031)
- Varun Lad (22107043)
- Devesh Patil (22107038)

---

## 📝 Project Description

SoilStream addresses the inefficient water management and crop vulnerability faced by small-scale farmers in the Thane region. The system uses an **ESP32 microcontroller** with a **Capacitive Soil Moisture Sensor** and **BME280** (temperature, humidity, pressure) to continuously monitor field conditions and push data to **Firebase** in real-time. A **VGG16 CNN model** identifies the crop type from a leaf photo, while **SVR/LightGBM/GRU models** predict rainfall probability to intelligently schedule irrigation. The **Kindwise API** diagnoses pests and diseases from farmer-uploaded images, and the **Gemini API** generates crop-specific soil-water recommendations — all accessible through a **React Native mobile app**.

---

## 🚀 How to Run the Project

Follow these steps to set up and run SoilStream on your local machine:

### 1. Prerequisites

Ensure you have the following installed:
- **Python 3.9+**
- **Node.js 18+**
- **Expo CLI** — `npm install -g expo-cli`
- **Arduino IDE** (for flashing the ESP32)

### 2. Clone the Repository

```bash
git clone https://github.com/RajChoudhary99/SoilStream.git
cd SoilStream
```

### 3. Set Up the Hardware

- Connect your **ESP32** to your PC via USB
- Open `hardware/soilstream.ino` in Arduino IDE
- Install the required Arduino libraries:
  - Firebase ESP32 Client (by Mobizt)
  - Adafruit BME280 Library
  - Adafruit Unified Sensor
- Update your credentials inside the `.ino` file:

```cpp
#define WIFI_SSID      "your_wifi_name"
#define WIFI_PASSWORD  "your_wifi_password"
#define API_KEY        "your_firebase_api_key"
#define DATABASE_URL   "https://your-project.firebaseio.com/"
```

- Flash the code to your ESP32

### 4. Download Model Weights

The VGG16 model file is too large for GitHub. Download it and place it at the correct path:

> 📥 **Download `model_vgg16.h5`** from: [Google Drive Link](#) *(replace with actual link)*  
> 📂 Place it at: `software/backend/model/model_vgg16.h5`

### 5. Run the Backend

Open a terminal, navigate to the backend folder, and start the Flask server:

```bash
cd software/backend
python app.py
```

The backend will start running at `http://localhost:5000`

### 6. Run the Frontend

Open a **second terminal**, navigate to the software folder, and start the Expo app:

```bash
cd software
npx expo start
```

Then scan the QR code with the **Expo Go** app on your phone, or press `a` for Android emulator / `i` for iOS simulator.

### 7. Set Up Environment Variables

Create a `.env` file inside the `software/` folder:

```
FIREBASE_API_KEY=your_key
GEMINI_API_KEY=your_key
KINDWISE_API_KEY=your_key
```

---

## 🛠️ Tech Stack

- **Hardware:** ESP32, Capacitive Soil Moisture Sensor, BME280, 5V Relay, Solar Panel
- **Mobile App:** React Native (Expo)
- **Backend:** Python, Flask
- **Database:** Firebase Realtime Database, Firestore
- **Cloud Functions:** Node.js (Firebase)
- **ML Models:** VGG16, SVR, LightGBM, GRU (TensorFlow, scikit-learn)
- **AI APIs:** Gemini 2.5 Flash, Kindwise (PlantWise)

---

## 🔍 Key Features

- **Real-Time Soil Monitoring:** ESP32 reads soil moisture, temperature, humidity, and pressure every 5 seconds and syncs to Firebase.
- **Automated Irrigation:** Water pump is triggered automatically based on soil moisture thresholds and rainfall predictions.
- **ML-Based Rainfall Prediction:** SVR, LightGBM, and GRU models trained on regional weather data prevent unnecessary watering.
- **Crop Identification:** VGG16 CNN identifies crop type from a farmer-uploaded leaf image and calibrates watering rules accordingly.
- **Pest & Disease Diagnosis:** Kindwise API analyzes plant images and provides treatment recommendations.
- **AI Recommendations:** Gemini API delivers crop-specific soil and water management advice based on live sensor data.
- **Solar Powered:** Operates off-grid using a 6V solar panel, TP4056 charge controller, and 18650 Li-ion battery.
