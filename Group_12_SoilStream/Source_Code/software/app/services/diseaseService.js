// services/diseaseService.js

// IMPORTANT: Update this with your actual server address
// For development:
// - Android Emulator: http://10.0.2.2:5000
// - iOS Simulator: http://localhost:5000
// - Physical Device: http://YOUR_LOCAL_IP:5000
const API_URL = 'http://YOUR_LOCAL_IP:5000'; // Replace with your IP

class DiseaseService {
  /**
   * Diagnose plant disease from image
   * @param {string} imageUri - Local URI of the plant image
   * @returns {Promise<Object>} - Disease diagnosis and treatment recommendations
   */
  async diagnoseDisease(imageUri) {
    try {
      console.log('Diagnosing disease from image:', imageUri);

      const formData = new FormData();
      
      // Prepare image for upload
      const imageFile = {
        uri: imageUri,
        type: 'image/jpeg',
        name: 'plant_disease.jpg',
      };

      formData.append('image', imageFile);

      const response = await fetch(`${API_URL}/api/diagnose-disease`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'multipart/form-data',
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Disease diagnosis failed');
      }

      console.log('✓ Disease diagnosis response:', JSON.stringify(data, null, 2));
      console.log('Disease diagnosed:', data.data.disease);
      console.log('Is Healthy?:', data.data.isHealthy);
      console.log('Confidence:', data.data.confidence);
      
      return data;

    } catch (error) {
      console.error('Disease diagnosis error:', error);
      throw new Error(
        error.message || 'Failed to diagnose disease. Please check your connection.'
      );
    }
  }

  /**
   * Check if disease diagnosis server is running
   * @returns {Promise<boolean>} - Server health status
   */
  async checkServerHealth() {
    try {
      const response = await fetch(`${API_URL}/health`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      const data = await response.json();
      return data.status === 'healthy' && 
             data.kindwise_api === 'configured' && 
             data.gemini_api === 'configured';

    } catch (error) {
      console.error('Health check error:', error);
      return false;
    }
  }

  /**
   * Get the API URL (useful for debugging)
   * @returns {string} - API URL
   */
  getApiUrl() {
    return API_URL;
  }

  /**
   * Format treatment recommendations for display
   * @param {Object} recommendations - Raw recommendations from API
   * @returns {Object} - Formatted recommendations
   */
  formatRecommendations(recommendations) {
    if (!recommendations) {
      return {
        sections: [],
        hasData: false
      };
    }

    const sections = [];

    // Chemical Treatment
    if (recommendations.chemicalTreatment && 
        recommendations.chemicalTreatment !== 'N/A' &&
        recommendations.chemicalTreatment !== 'Consult local agricultural expert') {
      sections.push({
        title: '💊 Chemical Treatment',
        icon: 'medical',
        content: recommendations.chemicalTreatment,
        color: '#2196F3'
      });
    }

    // Organic Treatment
    if (recommendations.organicTreatment && 
        recommendations.organicTreatment !== 'N/A') {
      sections.push({
        title: '🌿 Organic Treatment',
        icon: 'leaf',
        content: recommendations.organicTreatment,
        color: '#4CAF50'
      });
    }

    // Immediate Actions
    if (recommendations.immediateActions && recommendations.immediateActions.length > 0) {
      sections.push({
        title: '⚡ Immediate Actions',
        icon: 'flash',
        items: recommendations.immediateActions,
        color: '#FF9800'
      });
    }

    // Prevention
    if (recommendations.prevention && recommendations.prevention.length > 0) {
      sections.push({
        title: '🛡️ Prevention',
        icon: 'shield-checkmark',
        items: recommendations.prevention,
        color: '#9C27B0'
      });
    }

    // Timeline
    if (recommendations.timeline && recommendations.timeline !== 'N/A') {
      sections.push({
        title: '⏰ Timeline',
        icon: 'time',
        content: recommendations.timeline,
        color: '#00BCD4'
      });
    }

    // Warning Signs
    if (recommendations.warningSigns && recommendations.warningSigns.length > 0) {
      sections.push({
        title: '⚠️ Warning Signs',
        icon: 'warning',
        items: recommendations.warningSigns,
        color: '#F44336'
      });
    }

    return {
      sections,
      hasData: sections.length > 0
    };
  }
}

export default new DiseaseService();