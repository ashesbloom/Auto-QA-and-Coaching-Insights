# Auto-QA and Coaching Insights

An AI-powered system that evaluates 100% of customer support calls, scores them across quality dimensions, and generates agent-level + city-level coaching insights with supervisor flagging for high-risk calls.

## 🏗️ Architecture Overview

```
┌─────────────────┐     WebRTC      ┌──────────────────┐
│  React Frontend │◄───────────────►│  LiveKit Server  │
│  (Customer UI)  │                 │  (Docker)        │
└────────┬────────┘                 └────────┬─────────┘
         │                                   │
         │ REST API                          │ Recording
         ▼                                   ▼
┌─────────────────┐                 ┌──────────────────┐
│  FastAPI Backend│                 │  S3 / Local      │
│  (Room Tokens)  │                 │  Storage         │
└─────────────────┘                 └──────────────────┘
```

## 🚀 Quick Start (Local Development)

### Prerequisites

- **Docker & Docker Compose** - For running LiveKit server
- **Python 3.11+** - For backend API
- **Node.js 18+** - For frontend

### 1. Start LiveKit Server

```bash
docker-compose up -d
```

This starts the LiveKit WebRTC server on `localhost:7880`.

### 2. Start Backend API

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at `http://localhost:8000`

### 3. Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Frontend will be available at `http://localhost:3000`

## 📁 Project Structure

```
Auto-QA-and-Coaching-Insights/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Environment configuration
│   │   ├── schemas.py         # Pydantic models
│   │   ├── routes/
│   │   │   └── rooms.py       # Room management endpoints
│   │   └── services/
│   │       └── livekit_service.py  # LiveKit integration
│   ├── requirements.txt
│   └── .env
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/
│   │   │   └── roomService.js # API client
│   │   └── components/
│   │       ├── LandingPage.jsx # Customer landing page
│   │       └── CallRoom.jsx    # WebRTC call interface
│   ├── package.json
│   └── vite.config.js
│
├── docs/                       # Documentation
│   ├── problem_statement.txt
│   └── Technical_srs.txt
│
└── docker-compose.yml          # LiveKit server config
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Health check |
| POST | `/api/v1/rooms/create` | Create a new support room |
| POST | `/api/v1/rooms/token` | Get token for existing room |

### Create Room Request
```json
{
  "customer_name": "John Doe",
  "customer_phone": "+1234567890"
}
```

### Create Room Response
```json
{
  "room_name": "support-20260131-120000-abc12345",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "livekit_url": "ws://localhost:7880",
  "created_at": "2026-01-31T12:00:00Z"
}
```

## 🛠️ Development Status

### Phase 1: Core Infrastructure ✅
- [x] Project structure setup
- [x] LiveKit Docker configuration
- [x] Backend API for room management
- [x] React landing page with "Help" button
- [x] WebRTC call interface
- [ ] AI Voice Agent (Pipecat) - *Next*

### Phase 2: QA Pipeline 🔜
- [ ] Call recording (LiveKit Egress)
- [ ] AWS Transcribe integration
- [ ] Bedrock LLM analysis
- [ ] DynamoDB storage
- [ ] SNS alerts

### Phase 3: Dashboard 🔜
- [ ] QA scorecards
- [ ] Agent performance trends
- [ ] City-level insights
- [ ] Supervisor alerts UI

## 📄 License

Internal use only - Battery Smart Hackathon 2026