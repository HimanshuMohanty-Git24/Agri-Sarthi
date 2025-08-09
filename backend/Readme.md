# 🌾 Agri Sarthi - Smart Farming Assistant Backend

> **Advanced AI-Powered Agricultural Advisory Platform for Indian Farmers**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama3-orange.svg)](https://groq.com)
[![Twilio](https://img.shields.io/badge/Voice-Twilio-red.svg)](https://twilio.com)
[![UV](https://img.shields.io/badge/Package%20Manager-UV-purple.svg)](https://github.com/astral-sh/uv)

## 🚀 Overview

Agri Sarthi is a comprehensive agricultural advisory platform that combines multiple AI agents with voice capabilities to provide Indian farmers with real-time assistance on:

- 🌱 **Soil Analysis & Crop Recommendations**
- 💰 **Market Prices & Mandi Rates**
- 🏦 **Government Schemes & Financial Planning**
- 🌤️ **Weather Forecasts & Disaster Alerts**
- 📞 **Voice-Based Consultations in Hindi**

## 🏗️ Architecture

### Voice Processing Pipeline

```text
📞 Twilio Call → 🎤 WebSocket Stream → 🧠 Sarvam AI (STT) → 🤖 Groq LLM → 🔊 Sarvam AI (TTS) → 📱 Audio Response
```

## 📁 Project Structure

```text
backend/
├── 📁 voice/                    # Voice agent module
│   ├── models.py               # Pydantic models for voice calls
│   ├── services.py             # Core voice processing services
│   ├── views.py                # WebSocket handlers & API endpoints
│   ├── utils.py                # Audio processing utilities
│   └── urls.py                 # URL routing (legacy)
│
├── 📁 faiss_vector_store/       # RAG vector database
│   ├── index.faiss            # FAISS index for soil data
│   └── index.pkl              # Metadata pickle file
│
├── 📁 recordings/              # Voice call recordings
│
├── 📄 Core Files
│   ├── main.py                # FastAPI application & routing
│   ├── agent.py               # Multi-agent workflow system
│   ├── tools.py               # Specialized tools & APIs
│   ├── rag.py                 # RAG system for soil data
│   ├── settings.py            # Configuration settings
│   └── soildata.csv           # Soil composition database
│
└── 📋 Configuration
    ├── .env                   # Environment variables
    ├── .env.example          # Environment template
    ├── pyproject.toml        # UV project configuration
    ├── requirements.txt      # Python dependencies
    └── uv.lock              # UV lock file
```

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.12+**
- **UV Package Manager** (Recommended for faster dependency management)
- **API Keys** for various services (see configuration section)

### 1. Install UV Package Manager

```bash
# Install UV (faster and better than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or on Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/HimanshuMohanty-Git24/Agri-Sarthi.git
cd agri_sarthi_project/backend

# Create virtual environment and install dependencies with UV
uv venv
uv add -r requirements.txt

# Activate virtual environment
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env
```

## 🔑 Required API Keys & Configuration

Create a `.env` file with the following configurations:

```env
# 🤖 Core AI Services
GROQ_API_KEY=your_groq_api_key                    # Get from https://console.groq.com/keys
GOOGLE_API_KEY=your_google_api_key                # Get from Google AI Studio
TAVILY_API_KEY=your_tavily_api_key                # Get from https://tavily.com/

# 🔍 Search & Data Services
SERPAPI_API_KEY=your_serpapi_key                  # Get from https://serpapi.com/
OPENWEATHERMAP_API_KEY=your_openweather_key      # Get from https://openweathermap.org/

# 📞 Voice Services
SARVAM_API_KEY=your_sarvam_api_key                # Get from https://api.sarvam.ai
TWILIO_ACCOUNT_SID=your_twilio_sid                # Get from https://twilio.com
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number

# 🌐 Server Configuration
NGROK_URL=https://your-ngrok-url.ngrok-free.app   # For voice webhooks
HOST=0.0.0.0
PORT=8000

# 📊 Optional: LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=Agri Sarthi Project
```

## 🚀 Running the Application

### Development Server

```bash
# Using UV (recommended)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Traditional method
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
# With UV
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Traditional
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Voice Service Setup (Optional)

```bash
# Install ngrok for voice webhooks
npm install -g ngrok

# Expose local server
ngrok http 8000

# Update NGROK_URL in .env with the generated URL
```

## 📡 API Endpoints

### Core Chat API

```http
POST /chat
Content-Type: application/json

{
  "message": "What crops are suitable for sandy soil in Punjab?",
  "thread_id": "user_session_id"
}
```

### Voice Agent APIs

```http
# Voice call management
POST /voice/outbound-call        # Create outbound call
GET  /voice/call-history         # Get call history
GET  /voice/call-transcript/:id  # Get call transcript

# Twilio webhooks
POST /voice/incoming-call        # Handle incoming calls
WS   /ws/voice-stream           # WebSocket for audio streaming
```

### Health & Debug

```http
GET  /                          # Root health check
GET  /health                    # Detailed health status
GET  /debug/routes              # List all routes
GET  /voice/test                # Voice service test
```

## 🤖 Agent Capabilities

### 1. **Supervisor Agent** 🎯

- **Role**: Intelligent query routing and conversation management
- **Capabilities**:
  - Natural language intent recognition
  - Context-aware agent selection
  - Multi-language support (Hindi/English)

### 2. **SoilCropAdvisor Agent** 🌱

- **Role**: Soil analysis and crop recommendations
- **Tools**:
  - `soil_data_retriever`: RAG-based soil database search
  - `weather_alert_tool`: Real-time weather forecasts
  - `disaster_alert_tool`: NDMA disaster alerts
- **Data Source**: 10,000+ soil samples across Indian districts

### 3. **MarketAnalyst Agent** 💰

- **Role**: Market prices and trading information
- **Tools**:
  - `serpapi_market_price_tool`: Real-time mandi prices
- **Coverage**: Major mandis across India

### 4. **FinancialAdvisor Agent** 🏦

- **Role**: Government schemes and financial planning
- **Tools**:
  - Web search tools for scheme information
  - Focus on Indian central & state schemes
- **Specialization**: PM-KUSUM, electricity subsidies, agricultural loans

## 🎙️ Voice Agent Features

### Audio Processing

- **Speech-to-Text**: Sarvam AI (Hindi/English)
- **Text-to-Speech**: Sarvam AI with Indian voice models
- **Format**: μ-law ↔ WAV conversion for Twilio compatibility
- **Real-time**: WebSocket-based streaming

### Call Management

- **Inbound Calls**: Automatic TwiML generation
- **Outbound Calls**: Programmatic call initiation
- **Transcription**: Real-time conversation logging
- **Session Management**: Per-call state tracking

### Language Support

- **Primary**: Hindi (hi-IN)
- **Secondary**: English (en-IN)
- **Voice**: Female voice optimized for Indian farmers

## 🔧 Advanced Features

### RAG System

```python
# Powered by Google Gemini embeddings + FAISS
- Vector store: 10,000+ soil data points
- Retrieval: Top-3 relevant documents
- Chunking: 500 chars with 50 char overlap
```

### Multi-Tool Coordination

```python
# Example: Weather + Disaster alerts
def handle_weather_disaster_query():
    weather_data = weather_alert_tool(location)
    disaster_data = disaster_alert_tool(location)
    return combined_analysis(weather_data, disaster_data)
```

### Error Handling & Resilience

- Graceful fallbacks for API failures
- Service health monitoring
- Automatic retry mechanisms
- Comprehensive logging

## 📊 Performance Benefits of UV

UV package manager provides significant advantages over traditional pip:

| Feature | UV | pip |
|---------|----|----|
| **Installation Speed** | 10-100x faster | Baseline |
| **Dependency Resolution** | Faster & more accurate | Slower |
| **Lock File Support** | Native (uv.lock) | Requires pip-tools |
| **Virtual Environment** | Integrated | External tools needed |
| **Cross-platform** | Consistent behavior | Platform differences |
| **Memory Usage** | Lower | Higher |

### UV Commands

```bash
# Install dependencies
uv add package_name

# Update all packages
uv add --upgrade -r requirements.txt

# Add new dependency
uv add package_name

# Remove dependency
uv remove package_name

# Create lock file
uv lock

# Install from lock file
uv add -r uv.lock
```

## 🔍 Monitoring & Debugging

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Voice service test
curl http://localhost:8000/voice/test

# Route debugging
curl http://localhost:8000/debug/routes
```

### Logging

- **Application Logs**: Console output with detailed timestamps
- **Voice Logs**: Separate logging for call events
- **Error Tracking**: Comprehensive exception handling

### LangSmith Integration (Optional)

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
```

## 🚀 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.12-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY . .

# Install dependencies with UV
RUN uv pip install --system -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Traditional Deployment

```bash
# Production setup
uv pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🔒 Security Considerations

- **API Key Protection**: Environment-based configuration
- **CORS**: Configured for production domains
- **Input Validation**: Pydantic models for all inputs
- **Rate Limiting**: Implement as needed
- **Voice Security**: Twilio webhook validation

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Use UV** for dependency management
4. **Test** your changes thoroughly
5. **Commit** changes (`git commit -m 'Add amazing feature'`)
6. **Push** to branch (`git push origin feature/amazing-feature`)
7. **Open** Pull Request

### Development Setup

```bash
# Use UV for development
uv add -e .[dev]

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .
```

## 📞 Support & Contact

- **Issues**: Create GitHub issues for bugs
- **Features**: Submit feature requests via GitHub
- **Documentation**: Check inline code documentation
- **Performance**: UV provides 10-100x faster package management

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

> Built with ❤️ for Indian Farmers using cutting-edge AI technology and UV package management
