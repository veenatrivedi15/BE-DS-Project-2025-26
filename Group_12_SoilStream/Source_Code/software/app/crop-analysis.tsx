import React, { useState, useEffect } from "react";
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
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { useAuth } from "../contexts/AuthContext";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";

const { width } = Dimensions.get("window");

export default function CropAnalysisScreen() {
  const { user } = useAuth();
  const [selectedImage, setSelectedImage] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!user) {
      router.replace("/");
    }
  }, [user]);

  // ✅ Open camera or gallery
  const pickImage = async (from: "camera" | "gallery") => {
    let result;
    if (from === "camera") {
      await ImagePicker.requestCameraPermissionsAsync();
      result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 1,
      });
    } else {
      await ImagePicker.requestMediaLibraryPermissionsAsync();
      result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 1,
      });
    }

    if (!result.canceled) {
      const asset = result.assets[0];
      setSelectedImage({
        uri: asset.uri,
        fileName: `crop_${Date.now()}.jpg`,
        type: "image/jpeg",
      });
      setAnalysis(null);
    }
  };

  // ✅ Show options
  const showImagePickerOptions = () => {
    Alert.alert("Select Image", "Choose how you want to select an image", [
      { text: "Camera", onPress: () => pickImage("camera") },
      { text: "Gallery", onPress: () => pickImage("gallery") },
      { text: "Cancel", style: "cancel" },
    ]);
  };

  // ✅ Analyze crop via flask backend
  const analyzeCrop = async () => {
    if (!selectedImage) {
      Alert.alert("Error", "Please select an image first");
      return;
    }

    setIsAnalyzing(true);

    try {
      const formData = new FormData();
      formData.append("leaf", {
        uri: selectedImage.uri,
        type: selectedImage.type,
        name: selectedImage.fileName,
      } as any);

      const response = await fetch("http://YOUR_LOCAL_IP:5000/predict", {
        method: "POST",
        body: formData,
        headers: { "Content-Type": "multipart/form-data" },
      });

      const data = await response.json();
      console.log("Response data:", data);

      if (response.ok) {
        setAnalysis(data);
      } else {
        Alert.alert("Error", data.error || "Failed to analyze crop");
      }
    } catch (error) {
      console.error("❌ Analysis error:", error);
      Alert.alert("Error", "Failed to connect to server");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getWateringCapacityColor = (capacity: string) => {
    switch (capacity?.toLowerCase()) {
      case "(high)":
        return "#2196F3";
      case "(medium)":
        return "#FF9800";
      case "(low)":
        return "#4CAF50";
      default:
        return "#666";
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "#4CAF50";
    if (confidence >= 0.6) return "#FF9800";
    return "#F44336";
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#4CAF50" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Crop Analysis</Text>
        <View style={styles.placeholder} />
      </View>

      <ScrollView style={styles.scrollView}>
        <View style={styles.headerContent}>
          <Ionicons name="leaf" size={40} color="#4CAF50" />
          <Text style={styles.headerSubtitle}>
            AI-powered crop identification and live recommendations
          </Text>
        </View>

        {/* Upload Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Upload Crop Image</Text>

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
              <Ionicons name="image" size={20} color="white" />
              <Text style={styles.buttonText}>
                {selectedImage ? "Change Image" : "Select Image"}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.button,
                styles.analyzeButton,
                (!selectedImage || isAnalyzing) && styles.buttonDisabled,
              ]}
              onPress={analyzeCrop}
              disabled={!selectedImage || isAnalyzing}
            >
              {isAnalyzing ? (
                <ActivityIndicator size="small" color="white" />
              ) : (
                <Ionicons name="search" size={20} color="white" />
              )}
              <Text style={styles.buttonText}>
                {isAnalyzing ? "Analyzing..." : "Analyze Crop"}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* ✅ Real-time Analysis Results */}
        {analysis && (
          <View style={styles.card}>
            <View style={styles.resultsHeader}>
              <Ionicons name="analytics" size={28} color="#4CAF50" />
              <Text style={styles.cardTitle}>Analysis Results</Text>
            </View>

            <View style={styles.analysisContainer}>
              <View style={styles.cropHeader}>
                <Text style={styles.cropName}>{analysis.cropName}</Text>
                <View
                  style={[
                    styles.wateringChip,
                    {
                      backgroundColor: getWateringCapacityColor(
                        analysis.wateringCapacity
                      ),
                    },
                  ]}
                >
                  <Text style={styles.wateringChipText}>
                    {analysis.wateringCapacity}
                  </Text>
                </View>
              </View>

              <View style={styles.confidenceContainer}>
                <Text style={styles.confidenceLabel}>Confidence:</Text>
                <Text
                  style={[
                    styles.confidenceValue,
                    { color: getConfidenceColor(analysis.confidence) },
                  ]}
                >
                  {Math.round(analysis.confidence * 100)}%
                </Text>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Description</Text>
                <Text style={styles.sectionContent}>
                  {analysis.description || "No description available."}
                </Text>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Watering Requirements</Text>
                <View style={styles.infoRow}>
                  <Ionicons name="water" size={20} color="#2196F3" />
                  <Text style={styles.infoLabel}>Water requirements:</Text>
                  <Text style={styles.infoValue}>
                    {analysis.wateringFrequency || "N/A"}
                  </Text>
                </View>
                <View style={styles.infoRow}>
                  <Ionicons name="speedometer" size={20} color="#FF9800" />
                  <Text style={styles.infoLabel}>Water Quality:</Text>
                  <Text style={styles.infoValue}>
                    {analysis.wateringCapacity || "N/A"}
                  </Text>
                </View>
              </View>

              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Soil Requirements</Text>
                <View style={styles.infoRow}>
                  <Ionicons name="earth" size={20} color="#8BC34A" />
                  <Text style={styles.infoLabel}>Type:</Text>
                  <Text style={styles.infoValue}>{analysis.soilType || "N/A"}</Text>
                </View>
                <View style={styles.infoRow}>
                  <Ionicons name="flask" size={20} color="#9C27B0" />
                  <Text style={styles.infoLabel}>pH Level:</Text>
                  <Text style={styles.infoValue}>{analysis.soilPh || "N/A"}</Text>
                </View>
              </View>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// (keep your same styles here)
const styles = StyleSheet.create({ container: { flex: 1, backgroundColor: '#f5f5f5', }, header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 15, backgroundColor: 'white', shadowColor: '#000', shadowOffset: { width: 0, height: 2, }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3, }, backButton: { padding: 8, }, headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#2E7D32', }, placeholder: { width: 40, }, scrollView: { flex: 1, padding: 16, }, headerContent: { alignItems: 'center', marginBottom: 20, }, headerSubtitle: { fontSize: 14, color: '#666', textAlign: 'center', marginTop: 8, }, card: { backgroundColor: 'white', borderRadius: 12, padding: 20, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2, }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3, }, cardTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#333', }, imageContainer: { alignItems: 'center', marginBottom: 16, }, selectedImage: { width: width - 80, height: 200, borderRadius: 8, marginBottom: 12, }, changeImageButton: { borderWidth: 1, borderColor: '#4CAF50', borderRadius: 8, paddingHorizontal: 16, paddingVertical: 8, }, changeImageButtonText: { color: '#4CAF50', fontSize: 14, fontWeight: '500', }, imagePlaceholder: { alignItems: 'center', justifyContent: 'center', height: 200, borderWidth: 2, borderColor: '#ddd', borderStyle: 'dashed', borderRadius: 8, marginBottom: 16, }, placeholderText: { color: '#999', fontSize: 16, marginTop: 8, }, buttonContainer: { gap: 12, }, button: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 15, borderRadius: 8, gap: 8, }, buttonIcon: { marginRight: 8, }, buttonText: { color: 'white', fontSize: 16, fontWeight: 'bold', }, selectButton: { backgroundColor: '#4CAF50', }, analyzeButton: { backgroundColor: '#2196F3', }, buttonDisabled: { backgroundColor: '#ccc', }, resultsHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, }, analysisContainer: { gap: 16, }, cropHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', }, cropName: { fontSize: 20, fontWeight: 'bold', color: '#333', flex: 1, }, wateringChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 15, }, wateringChipText: { color: 'white', fontWeight: 'bold', fontSize: 12, }, confidenceContainer: { flexDirection: 'row', alignItems: 'center', gap: 8, }, confidenceLabel: { fontSize: 16, color: '#666', }, confidenceValue: { fontSize: 18, fontWeight: 'bold', }, section: { gap: 8, }, sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#333', }, sectionContent: { fontSize: 14, lineHeight: 20, color: '#666', }, wateringInfo: { gap: 8, }, soilInfo: { gap: 8, }, growthInfo: { gap: 8, }, infoRow: { flexDirection: 'row', alignItems: 'center', gap: 8, }, infoLabel: { fontSize: 14, color: '#666', fontWeight: '500', }, infoValue: { fontSize: 14, color: '#333', flex: 1, }, recommendationsList: { gap: 8, }, recommendationItem: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, }, recommendationText: { fontSize: 14, lineHeight: 20, color: '#666', flex: 1, }, tipsList: { gap: 12, }, tip: { flexDirection: 'row', alignItems: 'center', gap: 12, }, tipText: { fontSize: 14, color: '#666', flex: 1, }, });
