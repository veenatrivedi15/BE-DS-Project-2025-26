```markdown
# 🌾 AgriAid+ - Smart Farming Platform

## 👥 Group Members
* **Monish Mudaliar** (A. P. Shah Institute of Technology)
* **Rishi Mane** (A. P. Shah Institute of Technology)
* **Kalpana Mohanty** (A. P. Shah Institute of Technology)
* **Sharayu Mahajan** (A. P. Shah Institute of Technology)

## 📖 Short Project Description
AgriAid+ is a comprehensive, AI-driven agricultural dashboard designed to empower farmers with data-backed decisions. Built with a Flask backend and a modern Vanilla HTML/CSS/JS frontend, the platform integrates advanced machine learning and real-time data to provide a complete farming ecosystem. 

**Key Features Include:**
* **AI Crop & Fertilizer Prediction:** Utilizes XGBoost and LightGBM models to recommend the best crops and fertilizers based on soil parameters (N, P, K, pH, rainfall).
* **Smart Weather Forecasting:** A robust GRU (Gated Recurrent Unit) neural network that fetches historical data to predict 7-day weather patterns.
* **Multilingual RAG Chatbot:** An intelligent assistant powered by Google Gemini and FAISS vector databases, capable of answering complex agricultural queries in the user's native language based on official farming guidelines.
* **Farmer's Marketplace:** A MongoDB-powered e-commerce platform allowing farmers to list, view, and sell their produce directly, featuring image uploads and dynamic cart management.
* **Market Trends:** Real-time analysis of crop prices and demand across different cities.

---

## 🚀 Step-by-Step Setup Guide

Follow these instructions strictly to get the project running on your local machine.

### Step 1: System Prerequisites
Before you begin, ensure you have the following installed on your system:
1. **Python (3.8 to 3.12):** Download from [python.org](https://www.python.org/downloads/). Verify by running `python --version` in your terminal.
2. **MongoDB Community Server:** Download from [mongodb.com](https://www.mongodb.com/try/download/community). Ensure the MongoDB service is actively running on your machine (Default port: `27017`).
3. **Git:** To clone the repository.

### Step 2: Clone the Repository
Open your terminal or command prompt and run:
```bash
git clone <your-repository-url>
cd AgriAid
```

### Step 3: Set Up a Virtual Environment (Highly Recommended)
Creating a virtual environment ensures that project dependencies do not interfere with your global Python installation.

**For Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**For macOS and Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```
*(Note: Once activated, you should see `(venv)` at the beginning of your terminal prompt.)*

### Step 4: Install Python Dependencies
With the virtual environment activated, install all required packages using the `requirements.txt` file:
```bash
pip install -r requirements.txt
```
*Note: This will install Flask, TensorFlow, Scikit-Learn, LangChain, PyMongo, and other necessary libraries.*

### Step 5: Configure Environment Variables
The application requires API keys (like Google Gemini) to function. 
1. Create a new file named exactly `.env` in the root folder of the project.
2. Add your API keys to this file. It should look like this:
```env
# Google Gemini API Key for the RAG Chatbot
GOOGLE_API_KEY=your_gemini_api_key_here

# (Optional) Add any other environment variables your app uses
FLASK_ENV=development
```

### Step 6: Initialize the AI Knowledge Base (RAG Chatbot)
For the chatbot to answer agricultural questions, it needs to process your reference documents into a vector database.
1. Place your agricultural reference PDFs (e.g., crop guidelines, pest management manuals) inside the `knowledge_base/` folder.
2. Run the engine script to generate the FAISS vector database:
```bash
python chatbot_engine.py
```
*Wait for the terminal to print `✅ Vector database created successfully!` before proceeding.*

### Step 7: Verify MongoDB is Running
Ensure your local MongoDB database is running. If you are using MongoDB Compass, connect to `mongodb://127.0.0.1:27017/` to ensure the connection is active. The application will automatically create the `agriaidplus` database upon starting.

### Step 8: Start the Flask Server
Run the main application file:
```bash
python app.py
```
You should see output indicating that the ML models have loaded and the Flask server is running.

### Step 9: Access the Platform
Open your preferred web browser and navigate to:
```text
[http://127.0.0.1:5000/](http://127.0.0.1:5000/)
```
You are now ready to use AgriAid+!
```