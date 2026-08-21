# 🤖 DataChat AI

### AI-Powered Conversational Data Analysis Platform

DataChat AI is a conversational data analytics application that allows users to **upload datasets, ask questions in natural language, analyze data, and generate visualizations** without writing SQL or Python code.

---

## 🌐 Live Demo

**Frontend — Streamlit**
https://datachat1-ai.streamlit.app/

**Backend — Render**
https://datachat-ai-backend.onrender.com

> The Streamlit frontend is deployed separately and communicates with the FastAPI backend hosted on Render.

---

## ✨ Features

* 📂 Upload CSV / Excel datasets
* 👀 Preview uploaded data
* 💬 Ask questions using natural language
* 📊 AI-powered data analysis
* 📈 Generate visualizations
* ⚡ FastAPI REST backend
* 🤖 Google Gemini integration
* 🔌 LiteLLM-based LLM abstraction

---

## 🏗️ Architecture

```text
┌──────────────┐
│     USER     │
└──────┬───────┘
       ↓
┌──────────────────────┐
│  STREAMLIT FRONTEND  │
│ Upload • Preview     │
│ Chat • Visualization │
└──────────┬───────────┘
           │ HTTP / REST
           ↓
┌──────────────────────┐
│    FASTAPI BACKEND   │
│ Routes • Validation  │
│ File Processing      │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│       PANDASAI       │
│ Analysis • Queries   │
│ Visualization        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│       LITELLM        │
│   LLM Abstraction    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│     GOOGLE GEMINI    │
│  Natural Language AI │
└──────────────────────┘
```

---

## 🛠️ Tech Stack

| Technology        | Purpose          |
| ----------------- | ---------------- |
| Python            | Core development |
| Streamlit         | Frontend         |
| FastAPI           | Backend REST API |
| Pandas / PandasAI | Data analysis    |
| LiteLLM           | LLM abstraction  |
| Google Gemini     | Generative AI    |
| Git & GitHub      | Version control  |

---

## 🔄 How It Works

```text
Upload Dataset
      ↓
Ask a Question
      ↓
FastAPI Backend
      ↓
PandasAI + Gemini
      ↓
Data Analysis
      ↓
Result / Visualization
```

### Example

**User:**

> Which product generated the highest revenue?

**DataChat AI:**
Analyzes the uploaded dataset and returns the answer, along with a visualization when requested.

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/soniya11/datachat-ai.git
cd datachat-ai
```

### 2. Create virtual environment

```bash
python -m venv venv
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file:

```env
APIKEY=your_gemini_api_key
MODEL=your_model
```


### 4. Run the application

Start FastAPI:

```bash
uvicorn backend.main:app --reload
```

Start Streamlit in another terminal:

```bash
streamlit run frontend/app.py
```

---

## 🚀 Future Enhancements

* Database connectivity
* Advanced analytics & forecasting
* Authentication
* Interactive dashboards
* Multi-model LLM support
* Cloud deployment

---

## 👩‍💻 Author

**Soniya**
Computer Science & Engineering

⭐ If you find this project useful, consider starring the repository.

