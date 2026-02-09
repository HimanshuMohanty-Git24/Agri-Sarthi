# AgriSarthi v2 — Databricks-Powered Architecture

## Overview

AgriSarthi v2 migrates the AI core from standalone Groq/FAISS/Google Embeddings to a **fully Databricks-native** architecture, leveraging the latest Databricks technologies for production-grade performance, governance, and scalability — while keeping the farmer-facing channels (Web, Voice Call, WhatsApp) intact.

---

## What Stays External (and Why)

| Component | Why External |
|-----------|-------------|
| **React Frontend** | UI must be deployed on CDN/Vercel for low-latency farmer access |
| **FastAPI Gateway** | Thin API layer on serverless (Railway/Render) for CORS, WebSocket (Twilio), WhatsApp webhooks |
| **Sarvam AI** | Indic-language STT/TTS/Translation — no Databricks equivalent |
| **Twilio** | PSTN voice calls — telephony infrastructure |
| **WPPConnect** | WhatsApp bridge — messaging infrastructure |
| **OpenWeatherMap API** | External weather data source |
| **NDMA Alerts** | Government disaster alert API |

## What Moves to Databricks

| Current Component | Databricks Replacement | Technology Used |
|---|---|---|
| Groq LLaMA3 LLM | **Databricks AI Gateway** → routes to DBRX / Llama3 / Claude via **Model Serving** | AI Gateway, Model Serving |
| FAISS Vector Store | **Databricks Vector Search** index on Delta table | Vector Search |
| Google Gemini Embeddings | **Databricks Foundation Model** embeddings (BGE / GTE) | Model Serving |
| CSV soil data (soildata.csv) | **Delta Lake** table in Unity Catalog | Delta Lake, Unity Catalog |
| Keyword-based supervisor routing | **Mosaic AI Agent Framework** with tool-calling | Agent Bricks |
| LangGraph agent workflow | **Databricks AI Agents** (LangGraph on Mosaic AI) | AI Agents Framework |
| In-memory state | **Lakebase** (Serverless PostgreSQL) for sessions | Lakebase |
| No monitoring | **MLflow** traces + **AI/BI Dashboards** + **Genie** | MLflow, AI/BI, Genie |
| Manual tool functions | **Unity Catalog Functions** as agent tools | UC Functions |
| No feature engineering | **Feature Store** for farmer profiles | Feature Store |

---

## Architecture Layers

### 1. Farmer Access Layer (External)
```
React Web App  ──┐
Twilio Voice    ──┼──→  FastAPI Gateway  ──→  Databricks Model Serving Endpoint
WhatsApp (WPP)  ──┘         │
                       Sarvam AI (STT/TTS/Translate)
```

### 2. AI Agent Layer (Databricks)
```
Model Serving Endpoint
    └── AI Gateway (routes LLM calls)
        └── Supervisor Agent (Mosaic AI)
            ├── SoilCropAdvisor → [soil_data_retriever, weather_tool, disaster_tool]
            ├── MarketAnalyst   → [market_price_tool]
            ├── FinancialAdvisor → [scheme_search_tool]
            └── FinalAnswerAgent → synthesizes response
```

### 3. Data Layer (Databricks)
```
Unity Catalog
├── agrisarthi.bronze.soil_data          (Delta table from CSV)
├── agrisarthi.bronze.mandi_prices       (Delta table, scheduled ingestion)
├── agrisarthi.bronze.govt_schemes       (Delta table, web-scraped)
├── agrisarthi.silver.soil_enriched      (Cleaned + enriched soil data)
├── agrisarthi.gold.farmer_recommendations  (Pre-computed recommendations)
└── agrisarthi.vectors.soil_index        (Vector Search index)
```

### 4. Observability Layer (Databricks)
```
MLflow
├── Agent traces (every conversation logged)
├── Tool call metrics
├── Latency tracking
└── Evaluation datasets

AI/BI Dashboards
├── Daily active farmers
├── Query distribution by agent
├── Response latency P50/P95
└── Tool success rates

Genie
└── Natural language analytics ("How many farmers asked about PM-KUSUM this week?")
```

---

## Databricks Technologies Used (All 16)

| # | Technology | Usage in AgriSarthi v2 |
|---|---|---|
| 1 | **Agent Bricks** | Multi-agent supervisor/specialist routing |
| 2 | **Lakebase** | Session state, conversation history (Serverless PostgreSQL) |
| 3 | **Unity Catalog** | Governance for all tables, models, functions, and vector indexes |
| 4 | **Databricks Vector Search** | Soil data RAG retrieval (replaces FAISS) |
| 5 | **Databricks AI Gateway** | LLM routing (can switch between DBRX, Llama3, Claude) |
| 6 | **AI/BI Dashboards** | Real-time usage analytics for the platform |
| 7 | **Genie** | Natural language analytics on farmer queries |
| 8 | **Databricks Model Serving** | Expose agent as REST endpoint with auto-scaling |
| 9 | **Databricks Mosaic AI** | Agent framework with tool-calling capabilities |
| 10 | **Databricks AutoML** | Auto-train crop recommendation model from soil features |
| 11 | **Feature Store** | Store farmer location profiles for personalized recommendations |
| 12 | **Delta Lake** | All data stored as Delta tables (soil, prices, schemes) |
| 13 | **MLflow** | Agent lifecycle tracking, evaluation, A/B testing |
| 14 | **Databricks AI Agents Framework** | LangGraph-based multi-agent orchestration |
| 15 | **Databricks RAG Framework** | Production RAG pipeline with Vector Search + chunk optimization |
| 16 | **Serverless Compute** | All notebooks, jobs, and agent inference run serverless |

---

## Deployment Strategy

### Phase 1: Data Ingestion (Day 1)
- Upload `soildata.csv` → Delta table `agrisarthi.bronze.soil_data`
- Create Vector Search index on soil data
- Set up Unity Catalog namespace

### Phase 2: Agent Migration (Day 1-2)
- Define agent tools as UC Functions
- Build multi-agent workflow using Mosaic AI Agent Framework
- Deploy agent on Model Serving endpoint
- Configure AI Gateway for LLM routing

### Phase 3: Gateway Integration (Day 2)
- Update FastAPI to call Databricks Model Serving endpoint
- Keep Sarvam AI / Twilio / WPPConnect as-is
- Add Lakebase for session persistence

### Phase 4: Observability (Day 2)
- Enable MLflow tracing on agent
- Build AI/BI Dashboard
- Connect Genie for NL analytics

---

## Cost Estimate (Hackathon Scope)

| Resource | Estimated Cost |
|---|---|
| Model Serving (serverless) | ~$2-5/day during hackathon |
| Vector Search | ~$1/day |
| Delta storage | < $0.10 |
| Lakebase | ~$1/day |
| **Total** | **~$5-10/day** |

---

## Key Advantages Over v1

1. **No API key sprawl** — AI Gateway handles all LLM routing centrally
2. **Production RAG** — Vector Search with auto-sync from Delta (no stale FAISS)
3. **Governance** — Every table, model, and tool tracked in Unity Catalog
4. **Observability** — Full MLflow tracing on every farmer conversation
5. **Scalability** — Serverless compute auto-scales from 0 to millions of requests
6. **Analytics** — AI/BI + Genie let stakeholders ask questions about farmer usage
7. **Persistence** — Lakebase stores conversation history (no data loss on restart)
