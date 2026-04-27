# DATAGENT: Data Analytics Toolkit for Automatic Generation of Dashboards and Tailored Insights

## Group Members
- Ansh Rathod (22107022)
- Ayush Sharma (22107028)
- Atharva Thube (22107062)
- Balkrishna Yadav (22107050)

## Project Description:
**DATAGENT** is an AI-powered data analytics platform that automates the entire workflow - from data cleaning to dashboard generation - using natural language inputs. Users can upload datasets, ask questions in simple language, and receive cleaned data, generated analysis scripts, and interactive dashboards.

It combines Artificial Intelligence, NLP, and Machine Learning to reduce manual effort and make data analysis accessible to both technical and non-technical users.

This README reflects the current code in this repository.

## How to run the project:

### Prerequisites

* Python 3.8 or above
* Node.js (for frontend, if applicable)
* Required Python libraries:

  * pandas
  * numpy
  * polars
  * scikit-learn
  * plotly
  * openpyxl
  * xlsxwriter
  * flask (or fastapi, depending on your backend)

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/datagent.git
cd datagent
```

---

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3: Setup Environment Variables

Create a `.env` file and add required API keys:

```
GEMINI_API_KEY=your_api_key_here
```

---

### Step 4: Run Backend Server

```bash
python app.py
```

---

### Step 5: Run Frontend (if applicable)

```bash
cd frontend
npm install
npm run dev
```

---

### Step 6: Access the Application

Open your browser and go to:

```
http://localhost:3000
```

---

### Step 7: Using the System

1. Upload your dataset (CSV/Excel)
2. Choose:

   * Data Cleaning OR Direct Analysis
3. Enter your business query (e.g., "Show sales trend by year")
4. View:

   * Cleaned dataset
   * Generated code
   * Insights
   * Interactive dashboards
5. Download reports (Excel/PDF)

---

### Notes

* Ensure all dependencies are installed correctly
* Use a valid API key for LLM-based features
* For Excel interactive dashboards, Windows environment is recommended (PyWin32 support)