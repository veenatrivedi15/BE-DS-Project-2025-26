// services/databaseService.js
import { getDatabase, ref, onValue, off, get } from 'firebase/database';
import app from '../firebase/config';

const database = getDatabase(app);

class DatabaseService {
  /**
   * Subscribe to real-time sensor data updates
   * @param {string} deviceId - Device identifier
   * @param {function} callback - Function to call when data updates
   * @returns {function} - Unsubscribe function
   */
  subscribeSensorData(deviceId, callback) {
    const sensorRef = ref(database, `devices/${deviceId}`);
    
    const unsubscribe = onValue(sensorRef, (snapshot) => {
      if (snapshot.exists()) {
        const data = snapshot.val();
        console.log('📊 Sensor data updated:', data);
        callback(data);
      } else {
        console.log('⚠️ No sensor data found for device:', deviceId);
        callback(null);
      }
    }, (error) => {
      console.error('❌ Error reading sensor data:', error);
      callback(null);
    });

    // Return unsubscribe function
    return () => off(sensorRef);
  }

  /**
   * Get sensor data once (no real-time updates)
   * @param {string} deviceId - Device identifier
   * @returns {Promise<Object|null>} - Sensor data or null
   */
  async getSensorData(deviceId) {
    try {
      const sensorRef = ref(database, `devices/${deviceId}`);
      const snapshot = await get(sensorRef);
      
      if (snapshot.exists()) {
        return snapshot.val();
      } else {
        console.log('⚠️ No data found for device:', deviceId);
        return null;
      }
    } catch (error) {
      console.error('❌ Error fetching sensor data:', error);
      throw error;
    }
  }

  /**
   * Get all devices for current user
   * @param {string} userId - User ID
   * @returns {Promise<Array>} - List of devices
   */
  async getUserDevices(userId) {
    try {
      const devicesRef = ref(database, `users/${userId}/devices`);
      const snapshot = await get(devicesRef);
      
      if (snapshot.exists()) {
        const devices = snapshot.val();
        return Object.keys(devices).map(key => ({
          id: key,
          ...devices[key]
        }));
      } else {
        return [];
      }
    } catch (error) {
      console.error('❌ Error fetching user devices:', error);
      return [];
    }
  }

  /**
   * Format moisture level to user-friendly text
   * @param {number} moisture - Moisture percentage
   * @returns {Object} - Status info
   */
  getMoistureStatus(moisture) {
    if (moisture >= 70) {
      return {
        level: 'high',
        text: 'Very Wet',
        color: '#2196F3',
        icon: 'water',
        action: 'No watering needed'
      };
    } else if (moisture >= 40) {
      return {
        level: 'good',
        text: 'Optimal',
        color: '#4CAF50',
        icon: 'checkmark-circle',
        action: 'Moisture level is good'
      };
    } else if (moisture >= 20) {
      return {
        level: 'low',
        text: 'Needs Water',
        color: '#FF9800',
        icon: 'water-outline',
        action: 'Consider watering soon'
      };
    } else {
      return {
        level: 'critical',
        text: 'Very Dry',
        color: '#F44336',
        icon: 'alert-circle',
        action: 'Water immediately!'
      };
    }
  }
}

export default new DatabaseService();