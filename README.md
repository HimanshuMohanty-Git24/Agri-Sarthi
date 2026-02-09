# AgriSarthi — AI Farming Assistant

> **Databricks-powered multilingual farming assistant** with Web Chat, Voice Calls, and WhatsApp support.

Built for the Databricks Hackathon, AgriSarthi helps Indian farmers access crop prices, weather forecasts, government schemes, and soil health data — in their own language.

---

## Architecture

```
┌─────────────┐   ┌──────────────┐   ┌───────────────┐
│  React Web  │   │  Twilio Call  │   │  WhatsApp Bot │
│  Frontend   │   │  (Voice)     │   │  (WPPConnect) │
└─────┬───────┘   └──────┬───────┘   └───────┬───────┘
      │                  │                    │
      ▼                  ▼                    ▼
┌─────────────────────────────┐    ┌──────────────────┐
│     Backend Gateway         │    │  WhatsApp Server  │
│  (FastAPI — port 8000)      │    │  (FastAPI — 8001) │
│  - /chat (SSE streaming)    │    │  - /webhook       │
│  - /ws/voice-stream (WS)    │    │                   │
│  - /api/translate, /api/tts │    │                   │
└─────────────┬───────────────┘    └────────┬──────────┘
              │                             │
              ▼                             ▼
    ┌────────────────────────────────────────────┐
    │        Databricks Model Serving            │
    │   agents_agrisarthi-main-agrisarthi_agent  │
    │                                            │
    │   LangGraph Agent → 5 Tools:              │
    │   - Mandi Prices (Delta Lake + SQL API)   │
    │   - Weather (OpenWeatherMap)              │
    │   - Govt Schemes (Delta Lake)             │
    │   - Soil Health (Delta Lake)              │
    │   - Crop Advisory (LLM)                   │
    └────────────────────────────────────────────┘
```

### Databricks Technologies Used (16)

| # | Technology | Usage |
|---|-----------|-------|
| 1 | Unity Catalog | Data governance — `agrisarthi.main.*` tables |
| 2 | Delta Lake | Mandi prices, schemes, soil data, conversation logs |
| 3 | SQL Warehouse | Serverless SQL for agent tools |
| 4 | Databricks Notebooks | All ETL, agent code, dashboards |
| 5 | Model Serving | Agent endpoint (autoscaled, production) |
| 6 | MLflow | Model tracking, registry, versioning |
| 7 | Databricks AI Gateway | LLM access (`meta-llama-3.3-70b-instruct`) |
| 8 | Foundation Model API | Pay-per-token LLM serving |
| 9 | AI Agents (LangGraph) | Multi-tool farming agent |
| 10 | Models-from-Code | Agent logged as Python code (not pickle) |
| 11 | AI Playground | Interactive agent testing |
| 12 | Databricks Secrets | Secure API key management |
| 13 | Databricks Workflows | Scheduled mandi price ingestion |
| 14 | Databricks SQL Dashboard | Real-time analytics |
| 15 | Databricks CLI | Deployment automation |
| 16 | Lakebase | PostgreSQL session store |

---

## Project Structure

```
Agri-Sarthi/
├── backend/                  # Web + Voice Gateway (FastAPI)
│   ├── gateway.py            # Main app — chat, translate, TTS proxy, voice WS
│   ├── client.py             # DatabricksAgentClient + LakebaseSessionStore
│   ├── requirements.txt
│   └── voice/                # Twilio phone call module
│       ├── audio_utils.py    # mu-law ↔ WAV transcoding
│       ├── sarvam_voice.py   # Async Sarvam AI (STT/TTS/translate)
│       ├── twilio_handler.py # WebSocket handler + silence detection
│       ├── models.py         # Pydantic models
│       └── views.py          # Public API functions
│
├── whatsapp/                 # WhatsApp Bot (WPPConnect)
│   ├── main.py               # Webhook handler
│   ├── databricks_client.py  # Agent invocation
│   ├── sarvam.py             # Language detect, translate, TTS, STT
│   ├── requirements.txt
│   ├── config/               # Logger, Groq client setup
│   └── wppconnect/           # WhatsApp API wrapper
│
├── frontend/                 # React Web App
│   ├── src/components/       # Chat, Header, Footer, HomePage
│   └── src/services/         # Sarvam service (via gateway proxy)
│
├── notebooks/                # Databricks Notebooks
│   ├── 01_data_ingestion.py  # Upload CSV data to Delta Lake
│   ├── 02_agent_tools.py     # Define agent tools (SQL API)
│   ├── 03_agent_workflow.py  # LangGraph agent + MLflow logging
│   ├── 04_deploy_serving.py  # Deploy to Model Serving
│   ├── 05_dashboard.py       # SQL dashboard creation
│   ├── 06_evaluation.py      # Agent evaluation
│   └── 07_mandi_price_job.py # Scheduled mandi data ingestion
│
├── scripts/
│   └── ingest_mandi_local.py # Fetch live mandi prices → Delta Lake
│
├── docs/
│   ├── ARCHITECTURE.md       # Detailed architecture documentation
│   └── DEPLOYMENT_GUIDE.md   # Step-by-step deployment guide
│
├── .env.example              # Environment variable template
├── .gitignore
├── LICENSE
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Databricks workspace with Model Serving endpoint deployed
- Sarvam AI API key (for translation/TTS/STT)

### 1. Backend (Web Chat + Voice)

```bash
cd Agri-Sarthi
cp .env.example .env
# Fill in your credentials in .env

pip install -r backend/requirements.txt
uvicorn backend.gateway:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend (React)

```bash
cd frontend
npm install
npm start
# Opens http://localhost:3000
```

### 3. WhatsApp Bot

```bash
pip install -r whatsapp/requirements.txt
uvicorn whatsapp.main:app --reload --host 0.0.0.0 --port 8001
```

### 4. Voice Calls (Twilio)

```bash
# Start ngrok tunnel
ngrok http 8000

# Configure Twilio webhook:
#   Voice URL → https://your-ngrok-url.ngrok-free.app/voice/incoming-call
#   Method → POST

# Call your Twilio number to test!
```

### 5. Live Mandi Prices

```bash
python scripts/ingest_mandi_local.py
```

---

## Environment Variables

See [.env.example](.env.example) for the full list. Key variables:

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABRICKS_HOST` | All | Workspace URL |
| `DATABRICKS_TOKEN` | All | Personal access token |
| `SARVAM_API_KEY` | Backend | Sarvam AI key (voice module) |
| `SARVAM_AI_API_KEY` | WhatsApp | Sarvam AI key (WP bot) |
| `TWILIO_ACCOUNT_SID` | Backend | Twilio credentials |
| `WPPCONNECT_BASE_URL` | WhatsApp | WPPConnect server URL |
| `GROQ_API_KEY` | WhatsApp | Groq Whisper (voice messages) |

---

## API Endpoints

### Backend (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | SSE streaming chat |
| POST | `/chat/sync` | Synchronous chat |
| POST | `/api/translate` | Sarvam translation proxy |
| POST | `/api/tts` | Sarvam TTS proxy |
| WS | `/ws/voice-stream` | Twilio voice WebSocket |
| POST | `/voice/incoming-call` | Twilio webhook (TwiML) |
| GET | `/health` | Health check |

### WhatsApp Bot (port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhook` | WPPConnect message webhook |
| GET | `/health` | Health check |

---

## License

MIT — See [LICENSE](LICENSE)
