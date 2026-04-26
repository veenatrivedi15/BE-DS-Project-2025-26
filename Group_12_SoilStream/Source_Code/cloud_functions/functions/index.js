// functions/index.js
const {onRequest} = require("firebase-functions/v2/https");
const {onValueWritten} = require("firebase-functions/v2/database");
const {initializeApp} = require("firebase-admin/app");
const {getDatabase} = require("firebase-admin/database");

initializeApp();

/**
 * Predicts rainfall for Konkan region - BINARY CLASSIFICATION
 * @param {number} temperature - Temperature in Celsius
 * @param {number} humidity - Humidity percentage
 * @param {number} pressure - Pressure in hPa
 * @param {number} month - Month (1-12)
 * @return {Object} Prediction result (YES/NO)
 */
function predictRainfallKonkan(temperature, humidity, pressure, month) {
  const monsoonMonths = [6, 7, 8, 9];
  const dryMonths = [12, 1, 2, 3];

  const isMonsoonSeason = monsoonMonths.includes(month);
  const isDrySeason = dryMonths.includes(month);

  let willRain = false;
  let confidence = "low";
  let matchedRule = "default";

  // SIMPLIFIED BINARY RULES - Will it rain? YES or NO

  // Rule 1: Monsoon + High humidity + Low pressure = YES
  if (isMonsoonSeason && humidity >= 80 && pressure <= 1010) {
    willRain = true;
    confidence = "high";
    matchedRule = "Monsoon + High Humidity + Low Pressure";
  }
  // Rule 2: Monsoon + Moderate humidity = YES
  else if (isMonsoonSeason && humidity >= 70 && pressure <= 1012) {
    willRain = true;
    confidence = "medium";
    matchedRule = "Monsoon + Moderate Humidity";
  }
  // Rule 3: High humidity + Low pressure (any season) = YES
  else if (humidity >= 80 && pressure <= 1011) {
    willRain = true;
    confidence = "medium";
    matchedRule = "High Humidity + Low Pressure";
  }
  // Rule 4: Dry season + Low humidity = NO
  else if (isDrySeason && humidity <= 60) {
    willRain = false;
    confidence = "high";
    matchedRule = "Dry Season + Low Humidity";
  }
  // Rule 5: Normal conditions = NO
  else {
    willRain = false;
    confidence = "low";
    matchedRule = "Normal Conditions";
  }

  const season = isMonsoonSeason ? "Monsoon Season" :
    isDrySeason ? "Dry Season" : "Transition Season";

  return {
    willRain: willRain,
    confidence: confidence,
    matchedRule: matchedRule,
    seasonalContext: season,
  };
}

/**
 * Determines pump control - SIMPLIFIED LOGIC
 * @param {number} soilMoisture - Soil moisture percentage
 * @param {boolean} willRain - Will it rain? (YES/NO)
 * @param {boolean} currentPumpState - Current pump state
 * @return {Object} Pump control decision
 */
function determinePumpControl(soilMoisture, willRain, currentPumpState) {
  let shouldPumpBeOn = false;
  let reason = "";

  // SIMPLE LOGIC:
  // 1. If RAIN = YES → Pump OFF (save water)
  // 2. If RAIN = NO and SOIL DRY → Pump ON
  // 3. If RAIN = NO and SOIL WET → Pump OFF
  // 4. If RAIN = NO and SOIL MODERATE → Keep current state

  if (willRain) {
    // Rain expected - Turn OFF pump
    shouldPumpBeOn = false;
    reason = "Rain expected. Pump OFF to save water.";
  } else if (soilMoisture < 30) {
    // No rain + Dry soil - Turn ON pump
    shouldPumpBeOn = true;
    const soil = Math.round(soilMoisture);
    reason = `No rain expected and soil is dry (${soil}%). Pump ON.`;
  } else if (soilMoisture > 70) {
    // No rain + Wet soil - Keep OFF
    shouldPumpBeOn = false;
    const soil = Math.round(soilMoisture);
    reason = `Soil moisture is sufficient (${soil}%). Pump OFF.`;
  } else {
    // No rain + Moderate soil - Maintain current state
    shouldPumpBeOn = currentPumpState;
    const soil = Math.round(soilMoisture);
    reason = `No rain, moderate soil (${soil}%). Maintaining pump state.`;
  }

  return {shouldPumpBeOn, reason};
}

/**
 * Firebase Function: Rainfall Prediction
 */
exports.predictRainfall = onValueWritten(
    "/devices/{deviceId}/predictionTrigger",
    async (event) => {
      try {
        const deviceId = event.params.deviceId;
        const newData = event.data.after.val();

        if (!newData) {
          console.log("No data to process");
          return null;
        }

        const {temperature, humidity, pressure, soilMoisture} = newData;
        
        // Validate data
        if (soilMoisture === undefined || soilMoisture === null) {
          console.error("❌ No soil moisture data in trigger!");
          return null;
        }
        
        const currentDate = new Date();
        const month = currentDate.getMonth() + 1;

        console.log(`🌧️ Rainfall Prediction for ${deviceId}`);
        console.log(
            `📊 DATA: Temp=${temperature}°C, Hum=${humidity}%, ` +
          `Pres=${pressure}hPa, Soil=${soilMoisture}%, Month=${month}`,
        );

        const prediction = predictRainfallKonkan(
            temperature,
            humidity,
            pressure,
            month,
        );

        console.log(
            `Prediction: ${prediction.willRain ? "YES - RAIN" : "NO - NO RAIN"} ` +
          `(${prediction.matchedRule})`,
        );

        // Use soil moisture from trigger data directly
        const currentSoilMoisture = soilMoisture;

        // Get current pump state
        const db = getDatabase();
        const pumpSnapshot = await db
            .ref(`/devices/${deviceId}/pumpControl/status`)
            .get();

        const currentPumpState = pumpSnapshot.val() || false;

        const pumpControl = determinePumpControl(
            currentSoilMoisture,
            prediction.willRain,
            currentPumpState,
        );

        console.log(`💧 Pump decision: ${pumpControl.shouldPumpBeOn ? "ON" : "OFF"}`);
        console.log(`Reason: ${pumpControl.reason}`);

        const recommendation = prediction.willRain ?
          `🌧️ Rain expected - ${prediction.seasonalContext}. ${pumpControl.reason}` :
          `☀️ No rain expected - ${prediction.seasonalContext}. ${pumpControl.reason}`;

        const updates = {};

        updates[`/devices/${deviceId}/rainfallPrediction`] = {
          willRain: prediction.willRain,
          rainStatus: prediction.willRain ? "YES" : "NO",
          confidence: prediction.confidence,
          recommendation: recommendation,
          matchedRule: prediction.matchedRule,
          seasonalContext: prediction.seasonalContext,
          predictedAt: Date.now(),
          inputData: {
            temperature,
            humidity,
            pressure,
            month,
            soilMoisture: currentSoilMoisture,
          },
        };

        updates[`/devices/${deviceId}/pumpControl/command`] =
          pumpControl.shouldPumpBeOn;
        updates[`/devices/${deviceId}/pumpControl/reason`] =
          pumpControl.reason;
        updates[`/devices/${deviceId}/pumpControl/lastUpdated`] =
          Date.now();

        await db.ref().update(updates);

        console.log("Prediction updated successfully");

        return null;
      } catch (error) {
        console.error("Error in rainfall prediction:", error);
        return null;
      }
    },
);

/**
 * Manual Pump Control
 */
exports.manualPumpControl = onValueWritten(
    "/devices/{deviceId}/pumpControl/manualOverride",
    async (event) => {
      try {
        const deviceId = event.params.deviceId;
        const manualState = event.data.after.val();

        if (manualState === null || manualState === undefined) {
          return null;
        }

        console.log(
            `Manual pump control for ${deviceId}: ` +
          `${manualState ? "ON" : "OFF"}`,
        );

        const db = getDatabase();
        const updates = {};
        updates[`/devices/${deviceId}/pumpControl/command`] = manualState;
        updates[`/devices/${deviceId}/pumpControl/status`] = manualState;
        updates[`/devices/${deviceId}/pumpControl/reason`] =
          "Manual override from app";
        updates[`/devices/${deviceId}/pumpControl/lastUpdated`] =
          Date.now();

        await db.ref().update(updates);

        console.log("Manual pump control applied");

        return null;
      } catch (error) {
        console.error("Error in manual pump control:", error);
        return null;
      }
    },
);

/**
 * Test Prediction Endpoint
 */
exports.testPrediction = onRequest(async (req, res) => {
  if (req.method !== "POST") {
    return res.status(405).send("Method Not Allowed");
  }

  const {temperature, humidity, pressure, month} = req.body;

  if (!temperature || !humidity || !pressure) {
    return res.status(400).send({
      error: "Missing parameters: temperature, humidity, pressure",
    });
  }

  const currentMonth = month || (new Date().getMonth() + 1);
  const prediction = predictRainfallKonkan(
      temperature,
      humidity,
      pressure,
      currentMonth,
  );

  return res.status(200).send({
    success: true,
    prediction: {
      willRain: prediction.willRain,
      rainStatus: prediction.willRain ? "YES" : "NO",
      confidence: prediction.confidence,
      matchedRule: prediction.matchedRule,
      seasonalContext: prediction.seasonalContext,
    },
    input: {temperature, humidity, pressure, month: currentMonth},
  });

});