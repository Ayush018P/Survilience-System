---
title: NeuroGuard AI
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---
# NeuroGuard AI 🛡️

**Privacy-First Offline AI Surveillance Powered by Hybrid CNN-SNN Intelligence**

NeuroGuard AI is a state-of-the-art surveillance platform designed for real-time edge processing and absolute privacy. Built to function entirely offline, it leverages a unique hybrid AI architecture combining traditional Convolutional Neural Networks (CNN) for robust feature extraction and Spiking Neural Networks (SNN) for rapid, energy-efficient classification.

## 🌟 Key Features

*   **Hybrid AI Pipeline:** Combines the robustness of `InceptionResnetV1` (CNN) with the efficiency of Leaky Integrate-and-Fire (LIF) `snntorch` neurons (SNN).
*   **100% Offline Capable:** Runs locally using SQLite, eliminating the need to transmit sensitive biometric data to external APIs.
*   **Real-Time Processing:** WebSocket-driven architecture achieves high FPS streaming and instantaneous "Stranger" vs "Recognized" alerting.
*   **Redis Event Bus:** Utilizes Redis Pub/Sub for real-time event broadcasting to the React dashboard.
*   **Privacy-First Design:** Stores only 512-dimensional vector embeddings instead of raw faces (raw images are only temporarily retained for verified "Stranger" alerts).
*   **Dark Glassmorphism UI:** A stunning, responsive React + Vite frontend dashboard.

## 🏗️ Architecture Stack

### Backend (FastAPI)
*   **API Framework:** FastAPI, Pydantic
*   **Database:** SQLite (WAL mode) + SQLAlchemy ORM
*   **Cache & Pub/Sub:** Redis
*   **Authentication:** JWT (Stateless)
*   **AI Models:** 
    *   MTCNN (`facenet-pytorch`) - Face Detection
    *   InceptionResnetV1 (`facenet-pytorch`) - Embeddings
    *   SNN (`snntorch`, `PyTorch`) - Classification

### Frontend (React + Vite)
*   **UI Framework:** React 18, React Router v6
*   **Styling:** Custom CSS with Glassmorphism, Lucide Icons
*   **Charts:** Recharts
*   **Networking:** Axios, WebSockets

## 🚀 Quick Start (Docker)

The easiest way to run the entire stack locally is using Docker Compose.

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/neuroguard-ai.git
    cd neuroguard-ai
    ```
2.  Start the stack:
    ```bash
    docker-compose up -d --build
    ```
3.  Access the applications:
    *   **Frontend Dashboard:** `http://localhost:3000`
    *   **Backend API Docs (Swagger):** `http://localhost:8000/docs`

*Default Login Credentials: `admin` / `admin`*

## 💻 Manual Setup (Development)

### 1. Prerequisites
*   Python 3.11+
*   Node.js 18+
*   Redis server running locally on port 6379

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cp .env.example .env      # Edit .env if needed
uvicorn backend.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## ☁️ Deployment to Render.com

This repository includes a `render.yaml` Blueprint for 1-click deployment to Render's Infrastructure as Code.

1.  Push this code to a GitHub repository.
2.  Log in to Render.com and create a new "Blueprint Instance".
3.  Connect your GitHub repository.
4.  Render will automatically provision:
    *   A Redis instance
    *   A FastAPI backend web service (with persistent disk for SQLite)
    *   A static site for the React frontend

## 🔒 Security Note
This system uses static admin credentials in the MVP build (`admin`/`admin`). Before deploying to a public-facing production environment, implement proper password hashing and a user management table.


