# Chatbot Setup Guide

## Prerequisites
- Python 3.8+
- Node.js 16+
- Git

## Setup Steps

### 1. Clone Repository
```bash
git clone [YOUR_AZURE_REPO_URL]
cd planalytics-genai-solution
git checkout develop/chatbot-initial
```

### 2. Backend Setup
```
cd backend
# Create .env file with your environment variables

# Setup virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python main.py
```
### 3. Frontend Setup
```
cd frontend

# Install dependencies
npm install

# Run frontend
npm run dev
```
