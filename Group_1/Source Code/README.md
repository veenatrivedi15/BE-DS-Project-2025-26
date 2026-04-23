# 🌾 AgriAid+ - Smart Farming Platform

A comprehensive agricultural platform built with Python (Flask) backend and vanilla HTML/CSS/JavaScript frontend, featuring crop recommendations, weather predictions, market trends, and an e-commerce marketplace for farmers.

## ✨ Features

### 🏠 Home Page
- **4 Main Options**: Crop & Fertilizer Recommendation, Weather Prediction, Market Trends, E-commerce Marketplace
- **Responsive Design**: Modern UI with beautiful gradients and animations
- **Navigation**: Easy access to all platform features

### 🌱 Crop & Fertilizer Recommendation
- **Advanced Soil Analysis**: Input N, P, K levels, pH, and rainfall for precise recommendations

> 💾 **Database Setup**
> After running the Flask server you can initialize the MongoDB collections with:
> ```bash
> python init_db.py      # creates collections & indexes
> python seed_db.py      # (optional) insert sample records for testing
> ```
> The `db-status` endpoint (`GET /api/db-status`) returns collection names/counts and is logged to the browser console on each page load.
- **Machine Learning Models**: XGBoost and LightGBM algorithms trained on real agricultural data
- **Real Data**: Uses actual crop dataset (combined_crop_data.csv) for accurate predictions
- **Model Selection**: Choose between XGBoost (95.2% accuracy) or LightGBM (94.8% accuracy)
- **Probability Scores**: Get confidence levels and top 3 crop recommendations

### 🌤️ Weather Prediction
- **Current Weather**: Real-time temperature, humidity, rainfall, and wind speed
- **7-Day Forecast**: Extended weather predictions for farming planning
- **Visual Icons**: Weather conditions with intuitive emoji representations
- **Auto-refresh**: Get latest weather updates

### 📊 Market Trends
- **Price Tracking**: Current market prices for various crops
- **Trend Analysis**: Rising, falling, and stable price indicators
- **Demand Insights**: High, medium, and low demand classifications
- **Market Summary**: Quick overview of market conditions

### 🛒 E-commerce Marketplace
- **Product Listing**: Browse available agricultural products
- **Add Products**: Farmers can list their produce for sale
- **Contact Sellers**: Direct communication with product sellers
- **Location-based**: Products organized by geographical regions

### 💬 AI Chatbot
- **24/7 Support**: Available on all pages (bottom-right corner)
- **Groq AI Integration**: Powered by advanced language models for intelligent responses
- **Agricultural Expertise**: Specialized knowledge in farming, crops, soil health, and market trends
- **Context-Aware**: Understands farming terminology and provides relevant advice
- **Easy Access**: Click to open/close chat interface

## 🚀 Quick Start

1. **Install Dependencies**: Run `install_dependencies.bat` (Windows) or `pip install -r requirements.txt`
2. **Set API Key**: Create `.env` file with your Groq API key
3. **Start Backend**: Run `python app.py`
4. **Open Frontend**: Open `index.html` in your browser
5. **Test ML Models**: Go to Crop Recommendation page and input soil parameters

## 🚀 Technology Stack

### Backend
- **Python 3.8+**
- **Flask**: Web framework
- **Flask-CORS**: Cross-origin resource sharing
- **scikit-learn**: Machine learning for recommendations
- **pandas & numpy**: Data processing
- **XGBoost & LightGBM**: Advanced gradient boosting models
- **Groq AI**: Intelligent chatbot responses

### Frontend
- **HTML5**: Semantic markup structure
- **CSS3**: Modern styling with gradients, shadows, and animations
- **Vanilla JavaScript**: No framework dependencies, pure ES6+ JavaScript
- **Responsive Design**: Mobile-first approach

## 📋 Prerequisites

- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)
- `combined_crop_data.csv` file in the project root directory
- Groq AI API key (for chatbot functionality)

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd agricultural-platform
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run the Flask backend
python app.py

### 4. Environment Variables
Create a `.env` file in the project root with:
```
GROQ_API_KEY=your-groq-api-key-here
```

Get your API key from [Groq Console](https://console.groq.com/)
```

The backend will start on `http://localhost:5000`

### 3. Frontend Setup
Simply open `index.html` in your web browser! No build process or package installation required.

## 📊 Data Requirements

### Crop Dataset (combined_crop_data.csv)
The application requires a CSV file with the following columns:
- **N**: Nitrogen content in mg/kg (0-140)
- **P**: Phosphorus content in mg/kg (5-145)  
- **K**: Potassium content in mg/kg (5-205)
- **ph**: Soil pH level (3.5-10.0)
- **rainfall**: Rainfall in mm (20-300)
- **label**: Crop name (target variable)

The ML models will automatically train on this data to provide accurate crop recommendations.

## 🌐 API Endpoints

### Crop Recommendation
- `POST /api/crop-recommendation`
- Input: N, P, K, ph, rainfall, model_choice
- Output: predicted crop, top 3 recommendations, probabilities, model accuracy

### Weather Prediction
- `GET /api/weather-prediction`
- Output: current weather and 7-day forecast

### Market Trends
- `GET /api/market-trends`
- Output: current market prices and trends

### Products
- `GET /api/products` - List all products
- `POST /api/products` - Add new product

### Chatbot
- `POST /api/chatbot`
- Input: message
- Output: AI-powered agricultural advice

### Model Information
- `GET /api/model-info`
- Output: ML model status and details

### Market Trends
- `GET /api/market-trends`
- Output: current market prices and trends

### E-commerce Marketplace (via `marketplace` blueprint)
- `GET /api/marketplace/list` - List all products stored in MongoDB
- `POST /api/marketplace/add` - Add new product (JSON body with category, mode, name, price, quantity, description, username, role)
- `PUT /api/marketplace/update/<product_id>` - Update existing product (must be owner or admin)
- `DELETE /api/marketplace/delete/<product_id>` - Delete a product (owner/admin required)
- `GET /api/marketplace/my-list?username=<user>` - Get listings created by a specific user
- `POST /api/marketplace/order` - Place an order (requires product_id, username, quantity)
- `GET /api/db-status` - (debug) returns document counts for each collection

### Legacy Products endpoints (in-memory)
- `GET /api/products` - List all products (static fallback)
- `POST /api/products` - Add new product (static fallback)

### Chatbot
- `POST /api/chatbot`
- Input: user message
- Output: AI-generated response

## 🎯 Usage Examples

### Getting Crop Recommendations
1. Navigate to "Crop & Fertilizer Recommendation"
2. Enter soil pH (e.g., 6.5)
3. Select water availability (e.g., Moderate)
4. Choose season (e.g., Kharif)
5. Click "Get Recommendations"
6. View personalized crop suggestions

### Checking Weather
1. Go to "Weather Prediction"
2. View current weather conditions
3. Browse 7-day forecast
4. Use weather data for farming decisions

### Market Analysis
1. Visit "Market Trends"
2. Analyze current crop prices
3. Identify rising/falling trends
4. Understand market demand

### Selling Products
1. Navigate to "E-commerce Marketplace"
2. Click "Add New Product"
3. Fill product details
4. List your produce for sale

## 🔧 Customization

### Adding New Crops
Edit the `crop_data` dictionary in `app.py`:
```python
crop_data = {
    "new_crop": {
        "soil_ph": "6.0-7.0",
        "water": "Moderate",
        "fertilizer": "NPK 18-18-18"
    }
}
```

### Modifying Weather Data
Update the weather generation logic in the weather prediction endpoint.

### Extending Market Trends
Add new crops and their market data to the `market_trends` list.

### Frontend Customization
- **Styling**: Modify `styles.css` for visual changes
- **Functionality**: Edit `script.js` for behavior changes
- **Structure**: Update `index.html` for layout changes

## 🚀 Deployment

### Backend Deployment
```bash
# Install gunicorn for production
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Frontend Deployment
Simply upload the HTML, CSS, and JavaScript files to any web server or hosting service.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Open an issue on GitHub
- Contact the development team
- Check the documentation

## 🔮 Future Enhancements

- **Real-time Weather API**: Integration with OpenWeatherMap or similar
- **Advanced ML Models**: More sophisticated crop recommendation algorithms
- **Payment Integration**: Secure payment processing for marketplace
- **Mobile App**: Progressive Web App (PWA) capabilities
- **IoT Integration**: Sensor data for precision agriculture
- **Multi-language Support**: Localization for different regions
- **Offline Support**: Service worker for offline functionality

## 💡 Why Vanilla JavaScript?

- **No Dependencies**: Faster loading, smaller bundle size
- **Better Performance**: Direct DOM manipulation without framework overhead
- **Easier Maintenance**: No build tools or package management required
- **Universal Compatibility**: Works in all modern browsers without compilation
- **Learning Value**: Better understanding of web fundamentals

---

**Built with ❤️ for the farming community**
