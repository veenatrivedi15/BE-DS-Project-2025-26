import { useState, useEffect } from 'react';

export const useMockSensorData = () => {
  const [sensorData, setSensorData] = useState({
    soilMoisture: 65,
    temperature: 25,
    humidity: 70,
    rainPrediction: 'Clear Skies',
    pumpStatus: false,
    lastUpdated: new Date().toISOString()
  });

  useEffect(() => {
    // Simulate real-time data updates every 5 seconds
    const interval = setInterval(() => {
      setSensorData(prev => ({
        ...prev,
        soilMoisture: Math.max(0, Math.min(100, prev.soilMoisture + (Math.random() - 0.5) * 10)),
        temperature: Math.max(15, Math.min(40, prev.temperature + (Math.random() - 0.5) * 3)),
        humidity: Math.max(30, Math.min(90, prev.humidity + (Math.random() - 0.5) * 8)),
        rainPrediction: Math.random() > 0.7 ? 'Rain Expected' : 'Clear Skies',
        lastUpdated: new Date().toISOString()
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const togglePump = () => {
    setSensorData(prev => ({
      ...prev,
      pumpStatus: !prev.pumpStatus,
      lastUpdated: new Date().toISOString()
    }));
  };

  const getRecommendation = () => {
    if (sensorData.soilMoisture < 30) {
      return sensorData.rainPrediction === 'Rain Expected' 
        ? 'Low soil moisture detected, but rain is expected. Monitor closely.'
        : 'Low soil moisture detected. Consider turning on irrigation.';
    } else if (sensorData.soilMoisture > 80) {
      return 'Soil moisture is high. No irrigation needed.';
    } else {
      return 'Soil moisture levels are optimal.';
    }
  };

  return {
    sensorData,
    togglePump,
    recommendation: getRecommendation()
  };
};