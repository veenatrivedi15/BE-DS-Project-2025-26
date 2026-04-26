// firebase/config.js
import { initializeApp } from 'firebase/app';
import { getAuth, initializeAuth, getReactNativePersistence } from 'firebase/auth';
import { getDatabase } from 'firebase/database';
import AsyncStorage from '@react-native-async-storage/async-storage';

const firebaseConfig = {
  apiKey: "AIzaSyCyyyfAvqm466Dqs7Y3PYn8ChiIBpCWp-M",
  authDomain: "soilstream.firebaseapp.com",
  projectId: "soilstream",
  storageBucket: "soilstream.firebasestorage.app",
  messagingSenderId: "780179674989",
  appId: "1:780179674989:web:bf25b1178687e40010ec64",
  measurementId: "G-0JPSH4X442",
  databaseURL: "https://soilstream-default-rtdb.firebaseio.com/"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth with AsyncStorage persistence
const auth = initializeAuth(app, {
  persistence: getReactNativePersistence(AsyncStorage)
});

// Initialize Realtime Database
const database = getDatabase(app);

console.log('🔥 Firebase initialized:', app.name);
console.log('🔐 Auth initialized:', auth.app.name);
console.log('📧 Auth config check:', auth.config);

export { auth, database };
export default app;