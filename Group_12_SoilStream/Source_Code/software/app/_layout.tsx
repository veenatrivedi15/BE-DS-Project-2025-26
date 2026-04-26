import React from 'react';
import { Stack } from 'expo-router';
import { AuthProvider } from '../contexts/AuthContext';

export default function RootLayout() {
  return (
    <AuthProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="signup" />
        <Stack.Screen name="dashboard" />
        <Stack.Screen name="diagnosis" />
        <Stack.Screen name="crop-analysis" />
      </Stack>
    </AuthProvider>
  );
}