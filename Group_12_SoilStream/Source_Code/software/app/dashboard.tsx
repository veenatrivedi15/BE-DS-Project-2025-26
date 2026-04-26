import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Dimensions,
  Text,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { ref, onValue, off, set } from 'firebase/database';
import { database } from '../firebase/config';

const { width } = Dimensions.get('window');

// Define the sensor data type based on your Arduino code
interface SensorData {
  moisture: number;
  rawMoisture: number;
  temperature: number;
  humidity: number;
  pressure: number;
  status: string;
  timestamp: number;
}

interface RainfallPrediction {
  willRain: boolean;
  rainStatus: string;
  confidence: string;
  recommendation: string;
  predictedAt: number;
}

interface PumpControl {
  command: boolean;
  status: boolean;
  reason: string;
  lastUpdated: number;
}

export default function DashboardScreen() {
  const { user, logout } = useAuth();
  const [refreshing, setRefreshing] = useState(false);
  const [sensorData, setSensorData] = useState<SensorData | null>(null);
  const [rainfallPrediction, setRainfallPrediction] = useState<RainfallPrediction | null>(null);
  const [pumpControl, setPumpControl] = useState<PumpControl | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Device ID should match the one in your Arduino code
  const DEVICE_ID = 'DEVICE_001';

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!user) {
      router.replace('/');
    }
  }, [user]);

  // Fetch real-time data from Firebase
  useEffect(() => {
    if (!user) return;

    // Listen to sensor data
    const sensorRef = ref(database, `devices/${DEVICE_ID}/sensors`);
    const sensorUnsubscribe = onValue(
      sensorRef,
      (snapshot) => {
        if (snapshot.exists()) {
          const data = snapshot.val() as SensorData;
          setSensorData(data);
          setLastUpdated(new Date());
        }
      },
      (error) => {
        console.error('Sensor data error:', error);
      }
    );

    // Listen to rainfall prediction
    const predictionRef = ref(database, `devices/${DEVICE_ID}/rainfallPrediction`);
    const predictionUnsubscribe = onValue(
      predictionRef,
      (snapshot) => {
        if (snapshot.exists()) {
          const data = snapshot.val() as RainfallPrediction;
          setRainfallPrediction(data);
        }
      },
      (error) => {
        console.error('Prediction data error:', error);
      }
    );

    // Listen to pump control
    const pumpRef = ref(database, `devices/${DEVICE_ID}/pumpControl`);
    const pumpUnsubscribe = onValue(
      pumpRef,
      (snapshot) => {
        setIsLoading(false);
        setError(null);
        
        if (snapshot.exists()) {
          const data = snapshot.val() as PumpControl;
          setPumpControl(data);
        }
      },
      (error) => {
        setIsLoading(false);
        setError(`Firebase error: ${error.message}`);
      }
    );

    // Cleanup listeners on unmount
    return () => {
      off(sensorRef);
      off(predictionRef);
      off(pumpRef);
    };
  }, [user]);

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    // The data will refresh automatically via the real-time listener
    setTimeout(() => setRefreshing(false), 1000);
  }, []);

  const getSoilMoistureColor = (moisture: number) => {
    if (moisture < 30) return '#F44336'; // Red - Dry
    if (moisture < 60) return '#FF9800'; // Orange - Moderate
    return '#4CAF50'; // Green - Wet
  };

  const getSoilMoistureStatus = (moisture: number) => {
    if (moisture < 30) return 'Dry - Needs Water';
    if (moisture < 60) return 'Moderate';
    return 'Optimal';
  };

  const getLastUpdatedTime = () => {
    return lastUpdated.toLocaleTimeString();
  };

  const handleSignOut = async () => {
    await logout();
    router.replace('/');
  };

  const togglePump = async () => {
    if (!pumpControl) return;
    
    const newState = !pumpControl.status;
    
    try {
      // Update manual override in Firebase
      const manualOverrideRef = ref(database, `devices/${DEVICE_ID}/pumpControl/manualOverride`);
      await set(manualOverrideRef, newState);
      
      Alert.alert(
        'Pump Control',
        `Pump turned ${newState ? 'ON' : 'OFF'} manually`,
        [{ text: 'OK' }]
      );
    } catch (error) {
      console.error('Error toggling pump:', error);
      Alert.alert('Error', 'Failed to control pump');
    }
  };

  // Show loading state
  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContainer}>
          <Text style={styles.loadingText}>Loading sensor data...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Show error state
  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>SoilStream</Text>
            <Text style={styles.headerSubtitle}>
              Welcome, {user?.email?.split('@')[0]}
            </Text>
          </View>
          <TouchableOpacity onPress={handleSignOut} style={styles.logoutButton}>
            <Ionicons name="log-out" size={24} color="#4CAF50" />
          </TouchableOpacity>
        </View>
        <View style={styles.centerContainer}>
          <Ionicons name="alert-circle" size={64} color="#F44336" />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={onRefresh}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // Show no data state
  if (!sensorData) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>SoilStream</Text>
            <Text style={styles.headerSubtitle}>
              Welcome, {user?.email?.split('@')[0]}
            </Text>
          </View>
          <TouchableOpacity onPress={handleSignOut} style={styles.logoutButton}>
            <Ionicons name="log-out" size={24} color="#4CAF50" />
          </TouchableOpacity>
        </View>
        <View style={styles.centerContainer}>
          <Ionicons name="wifi-outline" size={64} color="#666" />
          <Text style={styles.noDataText}>
            Waiting for sensor data...
          </Text>
          <Text style={styles.noDataSubtext}>
            Make sure your ESP32 is powered on and connected
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>SoilStream</Text>
          <Text style={styles.headerSubtitle}>
            Welcome, {user?.email?.split('@')[0]}
          </Text>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={() => router.push('/diagnosis')} style={styles.navButton}>
            <Ionicons name="search" size={24} color="#4CAF50" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push('/crop-analysis')} style={styles.navButton}>
            <Ionicons name="leaf" size={24} color="#4CAF50" />
          </TouchableOpacity>
          <TouchableOpacity onPress={handleSignOut} style={styles.logoutButton}>
            <Ionicons name="log-out" size={24} color="#4CAF50" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Live Status Indicator */}
        <View style={styles.liveIndicator}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>Live Data</Text>
        </View>

        {/* Soil Moisture Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="water" size={28} color={getSoilMoistureColor(sensorData.moisture)} />
            <Text style={styles.cardTitle}>Soil Moisture</Text>
          </View>
          
          <View style={styles.moistureContainer}>
            <Text style={[styles.moistureValue, { color: getSoilMoistureColor(sensorData.moisture) }]}>
              {Math.round(sensorData.moisture)}%
            </Text>
            <View style={styles.progressBarContainer}>
              <View style={styles.progressBarBackground}>
                <View 
                  style={[
                    styles.progressBarFill, 
                    { 
                      width: `${sensorData.moisture}%`,
                      backgroundColor: getSoilMoistureColor(sensorData.moisture)
                    }
                  ]} 
                />
              </View>
            </View>
            <View style={[styles.statusChip, { backgroundColor: getSoilMoistureColor(sensorData.moisture) + '20' }]}>
              <Text style={[styles.statusChipText, { color: getSoilMoistureColor(sensorData.moisture) }]}>
                {sensorData.status}
              </Text>
            </View>
          </View>

          {/* Raw Sensor Value */}
          <View style={styles.rawValueContainer}>
            <Text style={styles.rawValueLabel}>Raw Sensor Reading</Text>
            <Text style={styles.rawValueText}>{sensorData.rawMoisture}</Text>
          </View>
        </View>

        {/* Device Information Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="hardware-chip" size={28} color="#2196F3" />
            <Text style={styles.cardTitle}>Device Information</Text>
          </View>
          
          <View style={styles.deviceInfoContainer}>
            <View style={styles.deviceInfoRow}>
              <Text style={styles.deviceInfoLabel}>Device ID:</Text>
              <Text style={styles.deviceInfoValue}>{sensorData.deviceId}</Text>
            </View>
            <View style={styles.deviceInfoRow}>
              <Text style={styles.deviceInfoLabel}>Uptime:</Text>
              <Text style={styles.deviceInfoValue}>
                {Math.floor(sensorData.timestamp / 1000 / 60)} min
              </Text>
            </View>
          </View>
        </View>

        {/* Weather Card */}
        {sensorData && (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Ionicons name="thermometer" size={28} color="#FF9800" />
              <Text style={styles.cardTitle}>Weather Conditions</Text>
            </View>
            
            <View style={styles.weatherContainer}>
              <View style={styles.weatherItem}>
                <Ionicons name="thermometer" size={20} color="#FF5722" />
                <Text style={styles.weatherLabel}>Temperature</Text>
                <Text style={styles.weatherValue}>
                  {sensorData.temperature ? `${Math.round(sensorData.temperature)}°C` : 'N/A'}
                </Text>
              </View>
              
              <View style={styles.weatherItem}>
                <Ionicons name="water-outline" size={20} color="#2196F3" />
                <Text style={styles.weatherLabel}>Humidity</Text>
                <Text style={styles.weatherValue}>
                  {sensorData.humidity ? `${Math.round(sensorData.humidity)}%` : 'N/A'}
                </Text>
              </View>

              <View style={styles.weatherItem}>
                <Ionicons name="speedometer" size={20} color="#9C27B0" />
                <Text style={styles.weatherLabel}>Pressure</Text>
                <Text style={styles.weatherValue}>
                  {sensorData.pressure ? `${Math.round(sensorData.pressure)} hPa` : 'N/A'}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Rainfall Prediction Card */}
        {rainfallPrediction && (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Ionicons 
                name={rainfallPrediction.willRain ? "rainy" : "sunny"} 
                size={28} 
                color={rainfallPrediction.willRain ? "#2196F3" : "#FFC107"} 
              />
              <Text style={styles.cardTitle}>AI Rainfall Prediction</Text>
            </View>
            
            <View style={styles.predictionContainer}>
              <View style={styles.probabilityDisplay}>
                <Text style={[
                  styles.rainStatusValue,
                  { color: rainfallPrediction.willRain ? '#2196F3' : '#4CAF50' }
                ]}>
                  {rainfallPrediction.rainStatus}
                </Text>
                <Text style={styles.probabilityLabel}>Rain Forecast</Text>
              </View>

              <View style={[
                styles.predictionChip,
                {
                  backgroundColor: rainfallPrediction.willRain ? '#2196F3' : '#4CAF50',
                }
              ]}>
                <Text style={styles.predictionChipText}>
                  {rainfallPrediction.willRain ? '🌧️ Rain Expected' : '☀️ No Rain Expected'}
                </Text>
              </View>

              <View style={styles.confidenceBadge}>
                <Text style={styles.confidenceLabel}>Confidence: </Text>
                <Text style={[
                  styles.confidenceValue,
                  { color: rainfallPrediction.confidence === 'high' ? '#4CAF50' : 
                           rainfallPrediction.confidence === 'medium' ? '#FF9800' : '#F44336' }
                ]}>
                  {rainfallPrediction.confidence.toUpperCase()}
                </Text>
              </View>

              <Text style={styles.predictionRecommendation}>
                {rainfallPrediction.recommendation}
              </Text>
            </View>
          </View>
        )}

        {/* Pump Control Card */}
        {pumpControl && (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Ionicons 
                name="settings" 
                size={28} 
                color={pumpControl.status ? '#4CAF50' : '#757575'} 
              />
              <Text style={styles.cardTitle}>Pump Control</Text>
            </View>
            
            <View style={styles.pumpContainer}>
              <View style={styles.pumpStatus}>
                <Text style={styles.pumpStatusText}>
                  Status: {pumpControl.status ? 'ON' : 'OFF'}
                </Text>
                <View style={[
                  styles.pumpChip,
                  {
                    backgroundColor: pumpControl.status ? '#4CAF50' : '#757575',
                  }
                ]}>
                  <Text style={styles.pumpChipText}>
                    {pumpControl.status ? 'ACTIVE' : 'INACTIVE'}
                  </Text>
                </View>
              </View>

              <View style={styles.pumpReasonContainer}>
                <Ionicons name="information-circle" size={18} color="#666" />
                <Text style={styles.pumpReasonText}>{pumpControl.reason}</Text>
              </View>
              
              <View style={styles.switchContainer}>
                <Text style={styles.switchLabel}>Manual Override</Text>
                <TouchableOpacity
                  style={[
                    styles.switch,
                    { backgroundColor: pumpControl.status ? '#4CAF50' : '#ccc' }
                  ]}
                  onPress={togglePump}
                >
                  <View style={[
                    styles.switchThumb,
                    { transform: [{ translateX: pumpControl.status ? 20 : 2 }] }
                  ]} />
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}

        {/* Crop Analysis Card */}
        <TouchableOpacity 
          style={styles.card} 
          onPress={() => router.push('/crop-analysis')}
        >
          <View style={styles.cardHeader}>
            <Ionicons name="leaf" size={28} color="#4CAF50" />
            <Text style={styles.cardTitle}>Crop Analysis</Text>
            <Ionicons name="chevron-forward" size={20} color="#4CAF50" />
          </View>
          
          <Text style={styles.cardDescription}>
            Upload crop images to get watering and soil recommendations
          </Text>
        </TouchableOpacity>

        {/* System Recommendation Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="bulb" size={28} color="#FFC107" />
            <Text style={styles.cardTitle}>System Recommendation</Text>
          </View>
          
          <Text style={styles.recommendationText}>
            {rainfallPrediction 
              ? rainfallPrediction.recommendation
              : sensorData.moisture < 30 
              ? "💧 Low moisture detected! Consider watering your crops soon."
              : sensorData.moisture > 70 
              ? "✅ Soil moisture is high. No watering needed at this time."
              : "👍 Soil moisture is at optimal levels. Continue monitoring."}
          </Text>
        </View>

        {/* Last Updated */}
        <View style={styles.lastUpdated}>
          <Text style={styles.lastUpdatedText}>
            Last updated: {getLastUpdatedTime()}
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    fontSize: 16,
    color: '#666',
    marginTop: 16,
  },
  errorText: {
    fontSize: 16,
    color: '#F44336',
    textAlign: 'center',
    marginTop: 16,
    marginBottom: 20,
  },
  noDataText: {
    fontSize: 18,
    color: '#333',
    textAlign: 'center',
    marginTop: 16,
    fontWeight: '600',
  },
  noDataSubtext: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
  },
  retryButton: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    backgroundColor: 'white',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2E7D32',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
  },
  headerActions: {
    flexDirection: 'row',
    gap: 12,
  },
  navButton: {
    padding: 8,
  },
  logoutButton: {
    padding: 8,
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#4CAF50',
    marginRight: 8,
  },
  liveText: {
    fontSize: 12,
    color: '#4CAF50',
    fontWeight: 'bold',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  cardTitle: {
    marginLeft: 12,
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  moistureContainer: {
    alignItems: 'center',
  },
  moistureValue: {
    fontSize: 48,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  progressBarContainer: {
    width: width - 80,
    marginBottom: 16,
  },
  progressBarBackground: {
    height: 8,
    backgroundColor: '#eee',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  statusChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  statusChipText: {
    fontWeight: 'bold',
    fontSize: 14,
  },
  rawValueContainer: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#eee',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  rawValueLabel: {
    fontSize: 14,
    color: '#666',
  },
  rawValueText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  deviceInfoContainer: {
    gap: 12,
  },
  deviceInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  deviceInfoLabel: {
    fontSize: 14,
    color: '#666',
  },
  deviceInfoValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  cardDescription: {
    fontSize: 14,
    lineHeight: 20,
    color: '#666',
    marginTop: 8,
  },
  recommendationText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#333',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  lastUpdated: {
    alignItems: 'center',
    marginVertical: 20,
  },
  lastUpdatedText: {
    fontSize: 12,
    color: '#666',
  },
  predictionContainer: {
    gap: 16,
    alignItems: 'center',
  },
  probabilityDisplay: {
    alignItems: 'center',
    marginBottom: 8,
  },
  probabilityValue: {
    fontSize: 48,
    fontWeight: 'bold',
  },
  rainStatusValue: {
    fontSize: 56,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  probabilityLabel: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  predictionChip: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
    alignSelf: 'center',
  },
  predictionChipText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  confidenceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#f0f0f0',
    borderRadius: 20,
  },
  confidenceLabel: {
    fontSize: 14,
    color: '#666',
  },
  confidenceValue: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  predictionRecommendation: {
    fontSize: 14,
    lineHeight: 20,
    color: '#555',
    textAlign: 'center',
    fontStyle: 'italic',
    paddingHorizontal: 16,
  },
  pumpContainer: {
    gap: 16,
  },
  pumpStatus: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pumpStatusText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  pumpChip: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 15,
  },
  pumpChipText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  pumpReasonContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#f0f0f0',
    padding: 12,
    borderRadius: 8,
  },
  pumpReasonText: {
    flex: 1,
    fontSize: 13,
    color: '#555',
    lineHeight: 18,
  },
  switchContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  switchLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  switch: {
    width: 50,
    height: 26,
    borderRadius: 13,
    justifyContent: 'center',
    position: 'relative',
  },
  switchThumb: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: 'white',
    position: 'absolute',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.3,
    shadowRadius: 2,
    elevation: 2,
  },
});