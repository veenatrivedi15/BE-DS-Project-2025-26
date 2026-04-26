import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  Image,
  Dimensions,
  Text,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import DiseaseService from './services/diseaseService';  // Fixed import path

const { width } = Dimensions.get('window');

export default function DiagnosisScreen() {
  const { user } = useAuth();
  const [selectedImage, setSelectedImage] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [diagnosis, setDiagnosis] = useState(null);
  const [serverStatus, setServerStatus] = useState(null);

  React.useEffect(() => {
    if (!user) {
      router.replace('/');
    } else {
      checkServerStatus();
    }
  }, [user]);

  const checkServerStatus = async () => {
    const isOnline = await DiseaseService.checkServerHealth();
    setServerStatus(isOnline);
    if (!isOnline) {
      Alert.alert(
        'Disease Diagnosis Server Offline',
        'The AI diagnosis server is not responding. Please make sure the backend server is running.\n\nServer URL: ' + DiseaseService.getApiUrl(),
        [{ text: 'OK' }]
      );
    }
  };

  const showImagePickerOptions = () => {
    Alert.alert(
      'Select Image',
      'Choose how you want to select an image',
      [
        { text: 'Camera', onPress: () => selectImageFromCamera() },
        { text: 'Gallery', onPress: () => selectImageFromGallery() },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const selectImageFromCamera = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Please grant camera permissions');
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,  // Disabled cropping
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        setSelectedImage({
          uri: result.assets[0].uri,
          fileName: `plant_camera_${Date.now()}.jpg`,
          type: 'image/jpeg',
        });
        setDiagnosis(null);
      }
    } catch (error) {
      console.error('Camera error:', error);
      Alert.alert('Error', 'Failed to open camera');
    }
  };

  const selectImageFromGallery = async () => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Please grant gallery permissions');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,  // Disabled cropping
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        setSelectedImage({
          uri: result.assets[0].uri,
          fileName: `plant_gallery_${Date.now()}.jpg`,
          type: 'image/jpeg',
        });
        setDiagnosis(null);
      }
    } catch (error) {
      console.error('Gallery error:', error);
      Alert.alert('Error', 'Failed to open gallery');
    }
  };

  const analyzePlant = async () => {
    if (!selectedImage) {
      Alert.alert('Error', 'Please select an image first');
      return;
    }

    if (!serverStatus) {
      Alert.alert(
        'Server Offline',
        'Disease diagnosis server is not responding. Please start the backend server and try again.',
        [
          { text: 'Check Again', onPress: checkServerStatus },
          { text: 'Cancel', style: 'cancel' }
        ]
      );
      return;
    }

    setIsAnalyzing(true);
    
    try {
      console.log('🔍 Starting plant analysis...');
      const response = await DiseaseService.diagnoseDisease(selectedImage.uri);
      
      console.log('📦 Full API response:', JSON.stringify(response, null, 2));
      
      if (response.success) {
        const diagnosisData = response.data;
        
        console.log('✅ Response is successful');
        console.log('📊 Diagnosis data:', JSON.stringify(diagnosisData, null, 2));
        console.log('🏥 isHealthy:', diagnosisData.isHealthy);
        console.log('🦠 disease:', diagnosisData.disease);
        console.log('🎯 confidence:', diagnosisData.confidence);
        console.log('⚠️ severity:', diagnosisData.severity);
        
        // Format recommendations
        const formattedRecs = DiseaseService.formatRecommendations(diagnosisData.recommendations);
        
        console.log('💊 Formatted recommendations:', JSON.stringify(formattedRecs, null, 2));
        
        const finalDiagnosis = {
          ...diagnosisData,
          formattedRecommendations: formattedRecs
        };
        
        console.log('🎬 Final diagnosis object:', JSON.stringify(finalDiagnosis, null, 2));
        
        setDiagnosis(finalDiagnosis);
        
        if (diagnosisData.isHealthy) {
          Alert.alert(
            'Good News! ✅',
            'Your plant appears to be healthy! No diseases detected.',
            [{ text: 'Great!' }]
          );
        } else {
          Alert.alert(
            'Disease Detected',
            `${diagnosisData.disease}\nConfidence: ${diagnosisData.confidence}%\nSeverity: ${diagnosisData.severity}`,
            [{ text: 'View Treatment' }]
          );
        }
      } else {
        console.log('❌ Response success flag is false');
      }
    } catch (error) {
      console.error('💥 Diagnosis error:', error);
      Alert.alert(
        'Diagnosis Failed',
        error.message || 'Failed to diagnose plant. Please try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getSeverityColor = (severity) => {
    if (!severity) return '#4CAF50';
    const lower = severity.toLowerCase();
    if (lower === 'high' || lower === 'severe') return '#F44336';
    if (lower === 'moderate' || lower === 'medium') return '#FF9800';
    if (lower === 'low' || lower === 'mild') return '#FFC107';
    return '#4CAF50';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return '#4CAF50';
    if (confidence >= 60) return '#FF9800';
    return '#F44336';
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#4CAF50" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Plant Diagnosis</Text>
        <TouchableOpacity onPress={checkServerStatus} style={styles.statusButton}>
          <View
            style={[
              styles.statusDot,
              { backgroundColor: serverStatus ? '#4CAF50' : '#F44336' },
            ]}
          />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scrollView}>
        <View style={styles.headerContent}>
          <Ionicons name="search" size={40} color="#4CAF50" />
          <Text style={styles.headerSubtitle}>
            AI-powered pest and disease detection
          </Text>
          {serverStatus !== null && (
            <Text style={[styles.serverStatusText, { color: serverStatus ? '#4CAF50' : '#F44336' }]}>
              {serverStatus ? '● Diagnosis Server Online' : '● Diagnosis Server Offline'}
            </Text>
          )}
        </View>

        {/* Image Selection Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Upload Plant Image</Text>
          
          {selectedImage ? (
            <View style={styles.imageContainer}>
              <Image 
                source={{ uri: selectedImage.uri }} 
                style={styles.selectedImage}
                resizeMode="cover"
              />
              <TouchableOpacity
                style={styles.changeImageButton}
                onPress={showImagePickerOptions}
              >
                <Text style={styles.changeImageButtonText}>Change Image</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.imagePlaceholder}>
              <Ionicons name="image" size={80} color="#ccc" />
              <Text style={styles.placeholderText}>No image selected</Text>
            </View>
          )}

          <View style={styles.buttonContainer}>
            <TouchableOpacity
              style={[styles.button, styles.selectButton]}
              onPress={showImagePickerOptions}
            >
              <Ionicons name="image" size={20} color="white" style={styles.buttonIcon} />
              <Text style={styles.buttonText}>
                {selectedImage ? 'Change Image' : 'Select Image'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.button, 
                styles.analyzeButton,
                (!selectedImage || isAnalyzing || !serverStatus) && styles.buttonDisabled
              ]}
              onPress={analyzePlant}
              disabled={!selectedImage || isAnalyzing || !serverStatus}
            >
              {isAnalyzing ? (
                <ActivityIndicator size="small" color="white" style={styles.buttonIcon} />
              ) : (
                <Ionicons name="search" size={20} color="white" style={styles.buttonIcon} />
              )}
              <Text style={styles.buttonText}>
                {isAnalyzing ? 'Analyzing...' : 'Diagnose Plant'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Analysis Results Card */}
        {diagnosis && (
          <View style={styles.card}>
            <View style={styles.resultsHeader}>
              <Ionicons 
                name={diagnosis.isHealthy ? "checkmark-circle" : "clipboard"} 
                size={28} 
                color={diagnosis.isHealthy ? "#4CAF50" : "#FF9800"} 
              />
              <Text style={styles.cardTitle}>Diagnosis Results</Text>
            </View>

            <View style={styles.diagnosisContainer}>
              <View style={styles.diseaseHeader}>
                <Text style={styles.diseaseName}>{diagnosis.disease}</Text>
                {!diagnosis.isHealthy && (
                  <View style={[
                    styles.severityChip,
                    { backgroundColor: getSeverityColor(diagnosis.severity) }
                  ]}>
                    <Text style={styles.severityChipText}>{diagnosis.severity}</Text>
                  </View>
                )}
              </View>

              {diagnosis.crop && diagnosis.crop !== 'Unknown plant' && (
                <View style={styles.cropInfo}>
                  <Ionicons name="leaf" size={18} color="#4CAF50" />
                  <Text style={styles.cropText}>Crop: {diagnosis.crop}</Text>
                </View>
              )}

              <View style={styles.confidenceContainer}>
                <Text style={styles.confidenceLabel}>Confidence:</Text>
                <Text style={[
                  styles.confidenceValue,
                  { color: getConfidenceColor(diagnosis.confidence) }
                ]}>
                  {Math.round(diagnosis.confidence)}%
                </Text>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Description</Text>
                <Text style={styles.sectionContent}>{diagnosis.description}</Text>
              </View>

              {/* Dynamic Treatment Recommendations */}
              {diagnosis.formattedRecommendations && diagnosis.formattedRecommendations.hasData && (
                <View style={styles.treatmentContainer}>
                  <Text style={styles.treatmentMainTitle}>Treatment Recommendations</Text>
                  
                  {diagnosis.formattedRecommendations.sections.map((section, index) => (
                    <View key={index} style={styles.treatmentSection}>
                      <View style={[styles.sectionHeader, { borderLeftColor: section.color }]}>
                        <Ionicons name={section.icon} size={22} color={section.color} />
                        <Text style={styles.sectionHeaderTitle}>{section.title}</Text>
                      </View>
                      
                      {section.content && (
                        <Text style={styles.treatmentContent}>{section.content}</Text>
                      )}
                      
                      {section.items && section.items.length > 0 && (
                        <View style={styles.treatmentList}>
                          {section.items.map((item, itemIndex) => (
                            <View key={itemIndex} style={styles.treatmentItem}>
                              <View style={[styles.bullet, { backgroundColor: section.color }]} />
                              <Text style={styles.treatmentItemText}>{item}</Text>
                            </View>
                          ))}
                        </View>
                      )}
                    </View>
                  ))}
                </View>
              )}
            </View>
          </View>
        )}

        {/* Instructions Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Tips for Best Results</Text>
          <View style={styles.tipsList}>
            <View style={styles.tip}>
              <Ionicons name="camera" size={20} color="#4CAF50" />
              <Text style={styles.tipText}>Take clear, well-lit photos</Text>
            </View>
            <View style={styles.tip}>
              <Ionicons name="scan" size={20} color="#4CAF50" />
              <Text style={styles.tipText}>Focus on affected areas</Text>
            </View>
            <View style={styles.tip}>
              <Ionicons name="resize" size={20} color="#4CAF50" />
              <Text style={styles.tipText}>Include entire leaf when possible</Text>
            </View>
            <View style={styles.tip}>
              <Ionicons name="sunny" size={20} color="#4CAF50" />
              <Text style={styles.tipText}>Use natural lighting</Text>
            </View>
          </View>
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
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2E7D32',
  },
  statusButton: {
    padding: 8,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  placeholder: {
    width: 40,
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  headerContent: {
    alignItems: 'center',
    marginBottom: 20,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
  },
  serverStatusText: {
    fontSize: 12,
    marginTop: 4,
    fontWeight: '500',
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
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  imageContainer: {
    alignItems: 'center',
    marginBottom: 16,
  },
  selectedImage: {
    width: width - 80,
    height: 200,
    borderRadius: 8,
    marginBottom: 12,
  },
  changeImageButton: {
    borderWidth: 1,
    borderColor: '#4CAF50',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  changeImageButtonText: {
    color: '#4CAF50',
    fontSize: 14,
    fontWeight: '500',
  },
  imagePlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
    height: 200,
    borderWidth: 2,
    borderColor: '#ddd',
    borderStyle: 'dashed',
    borderRadius: 8,
    marginBottom: 16,
  },
  placeholderText: {
    color: '#999',
    fontSize: 16,
    marginTop: 8,
  },
  buttonContainer: {
    gap: 12,
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    borderRadius: 8,
    gap: 8,
  },
  buttonIcon: {
    marginRight: 8,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  selectButton: {
    backgroundColor: '#4CAF50',
  },
  analyzeButton: {
    backgroundColor: '#2196F3',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  resultsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  diagnosisContainer: {
    gap: 16,
  },
  diseaseHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  diseaseName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  severityChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
  },
  severityChipText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 12,
  },
  cropInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#f0f8f0',
    borderRadius: 8,
  },
  cropText: {
    fontSize: 14,
    color: '#2E7D32',
    fontWeight: '500',
  },
  confidenceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  confidenceLabel: {
    fontSize: 16,
    color: '#666',
  },
  confidenceValue: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  section: {
    gap: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  sectionContent: {
    fontSize: 14,
    lineHeight: 20,
    color: '#666',
  },
  treatmentContainer: {
    marginTop: 8,
    gap: 16,
  },
  treatmentMainTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  treatmentSection: {
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
    padding: 12,
    gap: 12,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderLeftWidth: 3,
    paddingLeft: 8,
  },
  sectionHeaderTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  treatmentContent: {
    fontSize: 14,
    lineHeight: 20,
    color: '#555',
    paddingLeft: 4,
  },
  treatmentList: {
    gap: 8,
  },
  treatmentItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  bullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginTop: 6,
  },
  treatmentItemText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: '#555',
  },
  tipsList: {
    gap: 12,
  },
  tip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  tipText: {
    fontSize: 14,
    color: '#666',
    flex: 1,
  },
});


