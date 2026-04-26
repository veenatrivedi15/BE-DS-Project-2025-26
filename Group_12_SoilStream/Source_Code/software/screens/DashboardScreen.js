import React from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Dimensions,
  Text,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../contexts/AuthContext';
import { useMockSensorData } from '../hooks/useMockSensorData';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

export default function DashboardScreen() {
  const { user, signOut } = useAuth();
  const { sensorData, togglePump, recommendation } = useMockSensorData();
  const [refreshing, setRefreshing] = React.useState(false);

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 1000);
  }, []);

  const getSoilMoistureColor = (moisture) => {
    if (moisture < 30) return '#F44336'; // Red
    if (moisture < 60) return '#FF9800'; // Orange
    return '#4CAF50'; // Green
  };

  const getSoilMoistureStatus = (moisture) => {
    if (moisture < 30) return 'Low - Needs Water';
    if (moisture < 60) return 'Moderate';
    return 'Optimal';
  };

  const getLastUpdatedTime = () => {
    const date = new Date(sensorData.lastUpdated);
    return date.toLocaleTimeString();
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Smart Irrigation</Text>
          <Text style={styles.headerSubtitle}>
            Welcome, {user?.email?.split('@')[0]}
          </Text>
        </View>
        <TouchableOpacity onPress={signOut} style={styles.logoutButton}>
          <Ionicons name="log-out" size={24} color="#4CAF50" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Soil Moisture Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="water" size={28} color={getSoilMoistureColor(sensorData.soilMoisture)} />
            <Text style={styles.cardTitle}>Soil Moisture</Text>
          </View>
          
          <View style={styles.moistureContainer}>
            <Text style={[styles.moistureValue, { color: getSoilMoistureColor(sensorData.soilMoisture) }]}>
              {Math.round(sensorData.soilMoisture)}%
            </Text>
            <View style={styles.progressBarContainer}>
              <View style={styles.progressBarBackground}>
                <View 
                  style={[
                    styles.progressBarFill, 
                    { 
                      width: `${sensorData.soilMoisture}%`,
                      backgroundColor: getSoilMoistureColor(sensorData.soilMoisture)
                    }
                  ]} 
                />
              </View>
            </View>
            <View style={[styles.statusChip, { backgroundColor: getSoilMoistureColor(sensorData.soilMoisture) + '20' }]}>
              <Text style={[styles.statusChipText, { color: getSoilMoistureColor(sensorData.soilMoisture) }]}>
                {getSoilMoistureStatus(sensorData.soilMoisture)}
              </Text>
            </View>
          </View>
        </View>

        {/* Weather Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="thermometer" size={28} color="#FF9800" />
            <Text style={styles.cardTitle}>Weather Conditions</Text>
          </View>
          
          <View style={styles.weatherContainer}>
            <View style={styles.weatherItem}>
              <Ionicons name="thermometer" size={20} color="#FF5722" />
              <Text style={styles.weatherLabel}>Temperature</Text>
              <Text style={styles.weatherValue}>{Math.round(sensorData.temperature)}°C</Text>
            </View>
            
            <View style={styles.weatherItem}>
              <Ionicons name="water-outline" size={20} color="#2196F3" />
              <Text style={styles.weatherLabel}>Humidity</Text>
              <Text style={styles.weatherValue}>{Math.round(sensorData.humidity)}%</Text>
            </View>
          </View>
        </View>

        {/* Rain Prediction Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons 
              name={sensorData.rainPrediction === 'Rain Expected' ? 'cloud' : 'sunny'} 
              size={28} 
              color={sensorData.rainPrediction === 'Rain Expected' ? '#2196F3' : '#FFC107'} 
            />
            <Text style={styles.cardTitle}>Weather Forecast</Text>
          </View>
          
          <View style={[
            styles.forecastChip,
            {
              backgroundColor: sensorData.rainPrediction === 'Rain Expected' ? '#2196F3' : '#FFC107',
            }
          ]}>
            <Text style={styles.forecastChipText}>{sensorData.rainPrediction}</Text>
          </View>
        </View>

        {/* Pump Control Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons 
              name="settings" 
              size={28} 
              color={sensorData.pumpStatus ? '#4CAF50' : '#757575'} 
            />
            <Text style={styles.cardTitle}>Pump Control</Text>
          </View>
          
          <View style={styles.pumpContainer}>
            <View style={styles.pumpStatus}>
              <Text style={styles.pumpStatusText}>
                Status: {sensorData.pumpStatus ? 'ON' : 'OFF'}
              </Text>
              <View style={[
                styles.pumpChip,
                {
                  backgroundColor: sensorData.pumpStatus ? '#4CAF50' : '#757575',
                }
              ]}>
                <Text style={styles.pumpChipText}>
                  {sensorData.pumpStatus ? 'ACTIVE' : 'INACTIVE'}
                </Text>
              </View>
            </View>
            
            <View style={styles.switchContainer}>
              <Text style={styles.switchLabel}>Manual Override</Text>
              <TouchableOpacity
                style={[
                  styles.switch,
                  { backgroundColor: sensorData.pumpStatus ? '#4CAF50' : '#ccc' }
                ]}
                onPress={togglePump}
              >
                <View style={[
                  styles.switchThumb,
                  { transform: [{ translateX: sensorData.pumpStatus ? 20 : 2 }] }
                ]} />
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* System Recommendation Card */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="bulb" size={28} color="#FFC107" />
            <Text style={styles.cardTitle}>System Recommendation</Text>
          </View>
          
          <Text style={styles.recommendationText}>
            {recommendation}
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    backgroundColor: 'white',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
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
  logoutButton: {
    padding: 8,
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
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
  weatherContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  weatherItem: {
    alignItems: 'center',
    flex: 1,
  },
  weatherLabel: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
    marginBottom: 4,
  },
  weatherValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  forecastChip: {
    alignSelf: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
  },
  forecastChipText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
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
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.3,
    shadowRadius: 2,
    elevation: 2,
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
});