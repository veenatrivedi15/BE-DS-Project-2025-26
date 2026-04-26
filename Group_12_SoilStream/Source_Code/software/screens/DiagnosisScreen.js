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
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

// Mock diagnosis responses
const mockDiagnoses = [
  {
    disease: 'Leaf Spot Disease',
    confidence: 0.85,
    description: 'Fungal infection causing brown spots on leaves. Common in humid conditions.',
    treatment: 'Apply fungicide spray every 7-10 days. Remove affected leaves and improve air circulation.',
    severity: 'Moderate',
  },
  {
    disease: 'Healthy Plant',
    confidence: 0.92,
    description: 'No signs of disease detected. Plant appears to be in good health.',
    treatment: 'Continue current care routine. Monitor regularly for any changes.',
    severity: 'None',
  },
  {
    disease: 'Powdery Mildew',
    confidence: 0.78,
    description: 'White powdery fungal growth on leaf surfaces. Thrives in warm, dry conditions.',
    treatment: 'Use sulfur-based fungicide or neem oil. Increase air circulation and avoid overhead watering.',
    severity: 'High',
  },
  {
    disease: 'Nutrient Deficiency',
    confidence: 0.73,
    description: 'Yellowing leaves indicate possible nitrogen or magnesium deficiency.',
    treatment: 'Apply balanced fertilizer. Consider soil testing to determine specific nutrient needs.',
    severity: 'Low',
  },
];

export default function DiagnosisScreen() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [diagnosis, setDiagnosis] = useState(null);

  const showImagePickerOptions = () => {
    Alert.alert(
      'Select Image',
      'Choose how you want to select an image',
      [
        { text: 'Camera', onPress: () => selectMockImage('camera') },
        { text: 'Gallery', onPress: () => selectMockImage('gallery') },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const selectMockImage = (source) => {
    // Mock image selection - in real app this would use react-native-image-picker
    const mockImage = {
      uri: 'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=300&h=300&fit=crop',
      fileName: `plant_${source}_${Date.now()}.jpg`,
      type: 'image/jpeg',
    };
    setSelectedImage(mockImage);
    setDiagnosis(null);
  };

  const analyzePlant = async () => {
    if (!selectedImage) {
      Alert.alert('Error', 'Please select an image first');
      return;
    }

    setIsAnalyzing(true);
    
    // Simulate API call delay
    setTimeout(() => {
      const randomDiagnosis = mockDiagnoses[Math.floor(Math.random() * mockDiagnoses.length)];
      setDiagnosis(randomDiagnosis);
      setIsAnalyzing(false);
    }, 2000);
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return '#F44336';
      case 'moderate':
        return '#FF9800';
      case 'low':
        return '#FFC107';
      default:
        return '#4CAF50';
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#4CAF50';
    if (confidence >= 0.6) return '#FF9800';
    return '#F44336';
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView}>
        <View style={styles.header}>
          <Ionicons name="search" size={40} color="#4CAF50" />
          <Text style={styles.headerTitle}>Plant Diagnosis</Text>
          <Text style={styles.headerSubtitle}>
            AI-powered pest and disease detection
          </Text>
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
                (!selectedImage || isAnalyzing) && styles.buttonDisabled
              ]}
              onPress={analyzePlant}
              disabled={!selectedImage || isAnalyzing}
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
              <Ionicons name="clipboard" size={28} color="#4CAF50" />
              <Text style={styles.cardTitle}>Diagnosis Results</Text>
            </View>

            <View style={styles.diagnosisContainer}>
              <View style={styles.diseaseHeader}>
                <Text style={styles.diseaseName}>{diagnosis.disease}</Text>
                <View style={[
                  styles.severityChip,
                  { backgroundColor: getSeverityColor(diagnosis.severity) }
                ]}>
                  <Text style={styles.severityChipText}>{diagnosis.severity}</Text>
                </View>
              </View>

              <View style={styles.confidenceContainer}>
                <Text style={styles.confidenceLabel}>Confidence:</Text>
                <Text style={[
                  styles.confidenceValue,
                  { color: getConfidenceColor(diagnosis.confidence) }
                ]}>
                  {Math.round(diagnosis.confidence * 100)}%
                </Text>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Description</Text>
                <Text style={styles.sectionContent}>{diagnosis.description}</Text>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Recommended Treatment</Text>
                <Text style={styles.sectionContent}>{diagnosis.treatment}</Text>
              </View>
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
  scrollView: {
    flex: 1,
    padding: 16,
  },
  header: {
    alignItems: 'center',
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2E7D32',
    marginTop: 8,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 4,
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