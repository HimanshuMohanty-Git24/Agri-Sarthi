# AgriSarthi — Master Design Document

> **The Mother of All Docs**  
> Complete architecture, design, data flows, and technical deep-dive for AgriSarthi — a Databricks-powered multilingual AI farming assistant.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Why Databricks? — Old vs New Architecture](#4-why-databricks--old-vs-new-architecture)
5. [High-Level Design (HLD)](#5-high-level-design-hld)
6. [Databricks Technologies — All 16 Explained](#6-databricks-technologies--all-16-explained)
7. [System Architecture — Layer by Layer](#7-system-architecture--layer-by-layer)
8. [Channel Deep-Dive — Web, Voice, WhatsApp](#8-channel-deep-dive--web-voice-whatsapp)
9. [AI Agent Workflow — How the Brain Works](#9-ai-agent-workflow--how-the-brain-works)
10. [Data Layer — Delta Lake, Unity Catalog, Vector Search](#10-data-layer--delta-lake-unity-catalog-vector-search)
11. [Notebooks — The Deployment Pipeline](#11-notebooks--the-deployment-pipeline)
12. [Observability & Evaluation](#12-observability--evaluation)
13. [Multilingual & Voice Architecture](#13-multilingual--voice-architecture)
14. [Security & Secrets Management](#14-security--secrets-management)
15. [Project Structure — Complete Codebase Map](#15-project-structure--complete-codebase-map)
16. [API Reference](#16-api-reference)
17. [Deployment Guide — End to End](#17-deployment-guide--end-to-end)
18. [Cost Analysis](#18-cost-analysis)
19. [Future Roadmap](#19-future-roadmap)

---

## 1. Executive Summary

**AgriSarthi** (कृषि सारथी — "Agricultural Charioteer") is an AI-powered farming assistant built for **Indian farmers**. It provides real-time crop prices, weather forecasts, soil health analysis, government scheme information, and personalized crop recommendations — all in **11 Indian languages** — through **three channels**:

| Channel | Technology | How Farmers Use It |
|---------|-----------|-------------------|
| 🌐 **Web Chat** | React + FastAPI + SSE | Open browser, type or speak |
| 📞 **Phone Call** | Twilio + WebSocket | Dial a phone number, talk naturally |
| 💬 **WhatsApp** | WPPConnect + Webhook | Send text or voice message on WhatsApp |

**All three channels connect to a single Databricks-hosted AI agent** — ensuring consistent, high-quality responses regardless of how the farmer reaches out.

### Key Numbers

| Metric | Value |
|--------|-------|
| Languages supported | 11 (Hindi, Bengali, Tamil, Telugu, etc.) |
| Databricks technologies used | **16** |
| Agent tools available | 6 (soil, market prices, weather, disasters, schemes, crop recommendations) |
| Mandi price records | 678+ (live from data.gov.in) |
| Government schemes | 10+ (PM-KISAN, PM-KUSUM, PMFBY, KCC, etc.) |
| Soil data records | 100+ districts across India |
| LLM model | Meta Llama 3.3 70B Instruct (via Databricks AI Gateway) |

---

## 2. Problem Statement

### The Farmer's Struggle

Indian agriculture employs **42% of the workforce** but farmers face critical information gaps:

1. **No access to real-time market prices** — Farmers sell at whatever price middlemen offer, often 30-40% below market rate
2. **No personalized crop advice** — Generic recommendations ignore local soil, weather, and market conditions
3. **Unaware of government schemes** — Billions in subsidies go unclaimed because farmers don't know they exist
4. **Language barrier** — Most agri-tech solutions are English-only; 90% of Indian farmers speak regional languages
5. **Digital divide** — Many farmers don't have smartphones or internet; phone calls are the most accessible channel

### What Existing Solutions Lack

| Gap | Impact |
|-----|--------|
| English-only interfaces | Excludes 90% of target users |
| No voice support | Illiterate farmers can't type |
| No WhatsApp integration | Miss the platform 500M+ Indians use daily |
| No real-time mandi data | Outdated static price lists |
| No enterprise-grade backend | Can't scale, no governance, no observability |

---

## 3. Solution Overview

AgriSarthi solves all of the above with a **three-channel, multilingual, AI-agent-powered** system:

```
                    ┌──────────────────────────────┐
                    │         INDIAN FARMER         │
                    │  (Hindi, Tamil, Bengali, ...) │
                    └──────┬───────┬───────┬────────┘
                           │       │       │
                    ┌──────▼──┐ ┌──▼───┐ ┌─▼──────┐
                    │  React  │ │Phone │ │WhatsApp│
                    │  Web UI │ │ Call │ │  Bot   │
                    └────┬────┘ └──┬───┘ └───┬────┘
                         │        │         │
                    ┌────▼────────▼─────────▼────┐
                    │     Language Processing     │
                    │    (Sarvam AI — 11 langs)   │
                    │  STT → Translate → TTS      │
                    └────────────┬────────────────┘
                                │
                    ┌───────────▼───────────────┐
                    │   DATABRICKS AI PLATFORM   │
                    │                            │
                    │  ┌─────────────────────┐   │
                    │  │ Model Serving        │   │
                    │  │ (AgriSarthi Agent)   │   │
                    │  └──────────┬──────────┘   │
                    │             │               │
                    │  ┌──────────▼──────────┐   │
                    │  │ LangGraph Supervisor │   │
                    │  │ → SoilCropAdvisor    │   │
                    │  │ → MarketAnalyst      │   │
                    │  │ → FinancialAdvisor   │   │
                    │  │ → FinalAnswerAgent   │   │
                    │  └──────────┬──────────┘   │
                    │             │               │
                    │  ┌──────────▼──────────┐   │
                    │  │ 6 Agent Tools        │   │
                    │  │ • Soil Data (VS)     │   │
                    │  │ • Mandi Prices (DL)  │   │
                    │  │ • Weather (API)      │   │
                    │  │ • Disasters (NDMA)   │   │
                    │  │ • Schemes (DL)       │   │
                    │  │ • Crop Recs (DL)     │   │
                    │  └─────────────────────┘   │
                    │                            │
                    │  ┌─────────────────────┐   │
                    │  │ Delta Lake Tables    │   │
                    │  │ Unity Catalog        │   │
                    │  │ Vector Search        │   │
                    │  │ MLflow Tracking      │   │
                    │  │ AI/BI Dashboards     │   │
                    │  └─────────────────────┘   │
                    └────────────────────────────┘
```

---

## 4. Why Databricks? — Old vs New Architecture

### 🔴 Old Architecture (v1) — Before Databricks

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│ React Web   │───→│ FastAPI      │───→│ LangGraph    │
│ (port 3000) │    │ (port 8000)  │    │ Agent (local)│
└─────────────┘    └──────────────┘    └──────┬───────┘
                                              │
                   ┌──────────────────────────┤
                   │                          │
           ┌───────▼──────┐          ┌────────▼───────┐
           │ Groq Cloud   │          │ FAISS          │
           │ LLaMA 3 8B   │          │ (in-memory)    │
           │ (API key)     │          │ + Google Gemini│
           └──────────────┘          │ Embeddings     │
                                     └────────────────┘
                                              │
           ┌──────────────┐          ┌────────▼───────┐
           │ CSV files    │          │ SerpAPI        │
           │ (soildata.csv)│         │ (web search)   │
           └──────────────┘          └────────────────┘
```

**Problems with v1:**

| Issue | Impact |
|-------|--------|
| ❌ **Groq API key sprawl** | Single point of failure, no fallback, rate limited |
| ❌ **FAISS in-memory** | Lost on restart, no persistence, no governance |
| ❌ **Google Gemini embeddings** | Yet another API key, no data lineage |
| ❌ **CSV files as database** | No ACID, no versioning, no access control |
| ❌ **SerpAPI for market prices** | Slow, unreliable, expensive web scraping |
| ❌ **No monitoring** | Zero visibility into what agents are doing |
| ❌ **No evaluation** | No way to measure response quality |
| ❌ **No session persistence** | Conversation context lost between restarts |
| ❌ **Single machine** | Can't scale beyond one server |
| ❌ **No data governance** | No audit trail, no access control, no lineage |

---

### 🟢 New Architecture (v2) — With Databricks

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ React    │  │ Twilio   │  │ WhatsApp │
│ Web Chat │  │ Phone    │  │ Bot      │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └──────┬──────┘──────┬──────┘
            │             │
     ┌──────▼──────┐  ┌──▼───────────┐
     │ FastAPI     │  │ WhatsApp     │
     │ Gateway     │  │ Server       │
     │ (port 8000) │  │ (port 8001)  │
     └──────┬──────┘  └──────┬───────┘
            │                │
            └───────┬────────┘
                    │
     ┌──────────────▼──────────────────────┐
     │  DATABRICKS MODEL SERVING           │
     │  (auto-scaled, production, secure)  │
     │                                      │
     │  Agent: agrisarthi-main-agrisarthi  │
     │  LLM:   Llama 3.3 70B (AI Gateway) │
     │  Tools: 6 (Delta Lake + APIs)       │
     │  Logs:  MLflow auto-capture         │
     └──────────────────────────────────────┘
```

### 🏆 Side-by-Side Comparison

| Aspect | ❌ Old (v1) | ✅ New (v2 — Databricks) | Improvement |
|--------|------------|------------------------|-------------|
| **LLM** | Groq Cloud (Llama3 8B) | Databricks AI Gateway (Llama3.3 70B) | **10x larger model, no API key management, auto-routing** |
| **Vector Search** | FAISS (in-memory) | Databricks Vector Search (managed, auto-sync) | **Persistent, auto-syncs with Delta, no cold start** |
| **Embeddings** | Google Gemini API | Databricks BGE-Large-EN (built-in) | **No external API, no cost, runs inside Databricks** |
| **Soil Data** | CSV file on disk | Delta Lake table in Unity Catalog | **ACID transactions, versioning, governance, SQL queryable** |
| **Market Prices** | SerpAPI web scraping | Delta Lake + data.gov.in live API | **Real government data, 678+ records, daily refresh** |
| **Scheme Search** | DuckDuckGo/Tavily scraping | Delta Lake curated table | **Accurate, structured, always available** |
| **Agent Framework** | Raw LangGraph + Groq | Mosaic AI Agent Framework + AI Gateway | **Production-grade, auto-scaling, built-in tracing** |
| **Monitoring** | None (zero visibility) | MLflow traces + AI/BI Dashboards | **Every conversation logged, visualized, queryable** |
| **Evaluation** | None | MLflow Agent Evaluation (14 test cases) | **Automated quality checks before deployment** |
| **Sessions** | In-memory (lost on restart) | Lakebase (Serverless PostgreSQL) | **Persistent across restarts, multi-server** |
| **Security** | API keys in .env files | Databricks Secrets + Unity Catalog ACLs | **Enterprise-grade, audit trail, role-based** |
| **Scaling** | Single machine | Serverless auto-scaling (0 to ∞) | **Handles 1 to 1,000,000 farmers automatically** |
| **Data Governance** | None | Unity Catalog (full lineage) | **Every table, model, and tool tracked** |
| **Deployment** | Manual `python main.py` | Databricks Workflows + Model Serving | **One-click deploy, rollback, A/B testing** |
| **Analytics** | None | AI/BI Dashboards + Genie | **Stakeholders can ask questions in English** |
| **Voice Channel** | Not available in v1 | Twilio + Sarvam AI + WebSocket | **🆕 New capability — phone call support** |
| **WhatsApp** | Standalone Python bot | Databricks-connected via webhook | **Same AI brain as web and voice** |

> **Bottom line: Databricks turned a fragile prototype into a production-grade, enterprise-ready platform that can serve millions of farmers — with zero operational overhead.**

---

## 5. High-Level Design (HLD)

### 5.1 The Big Picture — Everything at a Glance

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        AGRISARTHI SYSTEM ARCHITECTURE                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌─────────────────── FARMER ACCESS LAYER ──────────────────────────────┐  ║
║  │                                                                      │  ║
║  │  🌐 React Web App        📞 Twilio Phone       💬 WhatsApp Bot     │  ║
║  │  (localhost:3000)        (+91-XXXXXXXXXX)      (WPPConnect)         │  ║
║  │       │                       │                      │               │  ║
║  │       ▼                       ▼                      ▼               │  ║
║  │  HTTP POST /chat         WebSocket                HTTP POST          │  ║
║  │  + SSE streaming         /ws/voice-stream         /webhook           │  ║
║  │                                                                      │  ║
║  └──────────────────────────────────────────────────────────────────────┘  ║
║                          │                    │                            ║
║  ┌───────────────── GATEWAY LAYER ──────────────────────────────────────┐  ║
║  │                                                                      │  ║
║  │  FastAPI Gateway (port 8000)          WhatsApp Server (port 8001)   │  ║
║  │  ├── /chat (SSE streaming)            ├── /webhook (msg handler)    │  ║
║  │  ├── /chat/sync (synchronous)         ├── Language detection        │  ║
║  │  ├── /api/translate (Sarvam proxy)    ├── Sarvam translate          │  ║
║  │  ├── /api/tts (Sarvam proxy)          └── Databricks agent call    │  ║
║  │  ├── /ws/voice-stream (Twilio WS)                                   │  ║
║  │  ├── /voice/incoming-call (TwiML)                                   │  ║
║  │  └── /health, /test                                                 │  ║
║  │                                                                      │  ║
║  └──────────────────────────────────────────────────────────────────────┘  ║
║                          │                    │                            ║
║  ┌───────────────── LANGUAGE LAYER ─────────────────────────────────────┐  ║
║  │                                                                      │  ║
║  │  Sarvam AI APIs (11 Indian languages)                               │  ║
║  │  ├── STT: saaras:v2.5 (speech-to-text-translate)                   │  ║
║  │  ├── Translation: mayura:v1 (text-to-text)                          │  ║
║  │  └── TTS: bulbul:v2 (text-to-speech)                               │  ║
║  │                                                                      │  ║
║  │  Groq Whisper (WhatsApp voice messages only)                        │  ║
║  │                                                                      │  ║
║  └──────────────────────────────────────────────────────────────────────┘  ║
║                          │                                                 ║
║  ╔═══════════════════ DATABRICKS PLATFORM ══════════════════════════════╗  ║
║  ║                                                                      ║  ║
║  ║  ┌──── AI AGENT LAYER ──────────────────────────────────────────┐   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  │  Model Serving Endpoint                                      │   ║  ║
║  ║  │  (agents_agrisarthi-main-agrisarthi_agent)                  │   ║  ║
║  ║  │       │                                                      │   ║  ║
║  ║  │       ▼                                                      │   ║  ║
║  ║  │  AI Gateway → Llama 3.3 70B Instruct                       │   ║  ║
║  ║  │       │                                                      │   ║  ║
║  ║  │       ▼                                                      │   ║  ║
║  ║  │  ┌────────────────────────────────────────┐                 │   ║  ║
║  ║  │  │        LangGraph Supervisor            │                 │   ║  ║
║  ║  │  │  Analyzes query → routes to specialist │                 │   ║  ║
║  ║  │  └──┬──────────┬──────────┬───────────────┘                 │   ║  ║
║  ║  │     │          │          │                                  │   ║  ║
║  ║  │     ▼          ▼          ▼                                  │   ║  ║
║  ║  │  ┌──────┐  ┌──────┐  ┌──────────┐                          │   ║  ║
║  ║  │  │Soil  │  │Market│  │Financial │                          │   ║  ║
║  ║  │  │Crop  │  │Analyst│  │Advisor  │                          │   ║  ║
║  ║  │  │Advsr │  │      │  │         │                          │   ║  ║
║  ║  │  └──┬───┘  └──┬───┘  └────┬────┘                          │   ║  ║
║  ║  │     │         │           │                                 │   ║  ║
║  ║  │     ▼         ▼           ▼                                 │   ║  ║
║  ║  │  ┌─────────────────────────────────────┐                   │   ║  ║
║  ║  │  │         FinalAnswerAgent            │                   │   ║  ║
║  ║  │  │  Synthesizes farmer-friendly reply  │                   │   ║  ║
║  ║  │  └─────────────────────────────────────┘                   │   ║  ║
║  ║  └──────────────────────────────────────────────────────────────┘   ║  ║
║  ║                                                                      ║  ║
║  ║  ┌──── TOOLS LAYER ────────────────────────────────────────────┐   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  │  🌱 soil_data_retriever    → Vector Search on Delta Lake    │   ║  ║
║  ║  │  📊 market_price_tool      → Delta Lake mandi_prices table  │   ║  ║
║  ║  │  🌤️ weather_alert_tool     → OpenWeatherMap API (external) │   ║  ║
║  ║  │  🚨 disaster_alert_tool    → NDMA API (external)           │   ║  ║
║  ║  │  📋 scheme_search_tool     → Delta Lake govt_schemes table  │   ║  ║
║  ║  │  🌾 crop_recommendation    → Delta Lake soil analysis      │   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  └──────────────────────────────────────────────────────────────┘   ║  ║
║  ║                                                                      ║  ║
║  ║  ┌──── DATA LAYER ─────────────────────────────────────────────┐   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  │  Unity Catalog: agrisarthi.main                             │   ║  ║
║  ║  │  ├── soil_data          (100+ districts, Vector Search idx) │   ║  ║
║  ║  │  ├── mandi_prices       (678+ live records from data.gov.in)│   ║  ║
║  ║  │  ├── govt_schemes       (10+ schemes with full details)     │   ║  ║
║  ║  │  ├── conversation_logs  (all interactions, all channels)    │   ║  ║
║  ║  │  └── farmer_features    (Feature Store — farmer profiles)   │   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  │  Vector Search: agrisarthi-vs-endpoint                      │   ║  ║
║  ║  │  └── soil_vector_index  (auto-synced from soil_data table)  │   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  └──────────────────────────────────────────────────────────────┘   ║  ║
║  ║                                                                      ║  ║
║  ║  ┌──── OBSERVABILITY LAYER ────────────────────────────────────┐   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  │  MLflow         → Agent traces, tool metrics, latency       │   ║  ║
║  ║  │  AI/BI Dashboard → Usage analytics, response times, trends  │   ║  ║
║  ║  │  Genie          → Natural language analytics queries        │   ║  ║
║  ║  │  Evaluation     → 14 test cases, fact-checking, per-domain  │   ║  ║
║  ║  │                                                              │   ║  ║
║  ║  └──────────────────────────────────────────────────────────────┘   ║  ║
║  ║                                                                      ║  ║
║  ╚══════════════════════════════════════════════════════════════════════╝  ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 5.2 Request Flow — From Farmer to Response

Here's what happens when a farmer asks **"गेहूं का भाव क्या है लखनऊ में?"** (What is wheat price in Lucknow?):

```
Step 1: FARMER INPUT
  └─ Farmer types in Hindi on WhatsApp / speaks on phone / types on web

Step 2: CHANNEL RECEIVES
  ├─ Web:      POST /chat → SSE stream
  ├─ Phone:    Twilio → WebSocket → mu-law audio chunks collected
  └─ WhatsApp: WPPConnect → POST /webhook → text extracted

Step 3: LANGUAGE PROCESSING
  ├─ Voice:    Sarvam STT (saaras:v2.5) → Hindi text
  ├─ Detect:   langdetect → "hi-IN"
  └─ Translate: Sarvam (mayura:v1) → English: "What is wheat price in Lucknow?"

Step 4: DATABRICKS AGENT INVOCATION
  └─ POST /serving-endpoints/agents_agrisarthi.../invocations
     {messages: [{role: "user", content: "What is wheat price in Lucknow?"}]}

Step 5: SUPERVISOR AGENT (LangGraph)
  └─ Analyzes query → detects "price" + "wheat" + "Lucknow"
     → Routes to: MarketAnalyst

Step 6: MARKET ANALYST AGENT
  └─ Calls tool: market_price_tool(crop_name="wheat", location="Lucknow")
     → SQL on Delta Lake: SELECT * FROM mandi_prices WHERE crop='wheat' AND market='Lucknow'
     → Returns: "Wheat at Lucknow: ₹2100-₹2350 (modal ₹2250/Quintal)"

Step 7: FINAL ANSWER AGENT
  └─ Synthesizes farmer-friendly response:
     "Lucknow mandi mein gehun ka bhav ₹2,100-₹2,350 per quintal hai.
      Average price ₹2,250 hai. Ye season mein price stable hai."

Step 8: RESPONSE DELIVERY
  ├─ Web:      SSE stream → word-by-word display
  ├─ Phone:    Sarvam TTS (bulbul:v2) → Hindi audio → mu-law chunks → Twilio playback
  └─ WhatsApp: Sarvam translate → Hindi text → WPPConnect → WhatsApp message

Step 9: LOGGING
  └─ Conversation logged to agrisarthi.main.conversation_logs (Delta Lake)
     MLflow trace captured automatically
```

**Total latency: ~3-8 seconds** (varies by SQL warehouse cold start and Sarvam API)

---

## 6. Databricks Technologies — All 16 Explained

### Complete Technology Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABRICKS TECHNOLOGY STACK                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  COMPUTE                         AI/ML                              │
│  ┌──────────────────┐           ┌──────────────────────────┐       │
│  │ 1. Serverless    │           │ 7. AI Gateway            │       │
│  │    Compute       │           │ 8. Foundation Model API  │       │
│  │ 2. SQL Warehouse │           │ 9. Mosaic AI Agents      │       │
│  └──────────────────┘           │10. Models-from-Code      │       │
│                                 │11. AI Playground         │       │
│  DATA                           └──────────────────────────┘       │
│  ┌──────────────────┐                                               │
│  │ 3. Delta Lake    │           OPERATIONS                          │
│  │ 4. Unity Catalog │           ┌──────────────────────────┐       │
│  │ 5. Vector Search │           │12. MLflow                │       │
│  │ 6. Lakebase      │           │13. Model Serving         │       │
│  └──────────────────┘           │14. Databricks Workflows  │       │
│                                 │15. Databricks CLI        │       │
│  ANALYTICS                      │16. Databricks Secrets    │       │
│  ┌──────────────────┐           └──────────────────────────┘       │
│  │ AI/BI Dashboards │                                               │
│  │ Genie            │                                               │
│  └──────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology-by-Technology Breakdown

#### 1. Unity Catalog — The Governance Brain
**What it does:** Central governance layer for ALL data, models, functions, and vector indexes.

**How AgriSarthi uses it:**
- Namespace: `agrisarthi.main` (catalog.schema)
- All Delta tables registered here with ACLs
- Agent model registered as `agrisarthi.main.agrisarthi_agent`
- Full data lineage from CSV → Delta → Vector Search → Agent
- Access control: Only the agent service principal can write to tables

```sql
CREATE CATALOG IF NOT EXISTS agrisarthi;
CREATE SCHEMA IF NOT EXISTS agrisarthi.main;
-- Every table, model, and index lives under this namespace
```

#### 2. Delta Lake — The Data Foundation
**What it does:** ACID-transactional data lake storage format with time travel, schema evolution, and Z-ordering.

**How AgriSarthi uses it:**
- `soil_data` — 100+ soil records with nutrients, pH, rainfall by district
- `mandi_prices` — 678+ live market prices from data.gov.in API
- `govt_schemes` — 10+ government agricultural schemes
- `conversation_logs` — Every farmer interaction across all channels

**Why it's better than CSV:**
| Feature | CSV (v1) | Delta Lake (v2) |
|---------|----------|-----------------|
| ACID transactions | ❌ | ✅ |
| Schema enforcement | ❌ | ✅ |
| Time travel | ❌ | ✅ (revert to any version) |
| Concurrent reads/writes | ❌ | ✅ |
| SQL queryable | Manual | ✅ Native |
| Auto-optimization | ❌ | ✅ (Z-order, compaction) |

#### 3. Vector Search — The RAG Engine
**What it does:** Managed vector similarity search service that auto-syncs embeddings from Delta tables.

**How AgriSarthi uses it:**
- Endpoint: `agrisarthi-vs-endpoint`
- Index: `agrisarthi.main.soil_vector_index`
- Source column: `soil_text` (generated from soil data fields)
- Embedding model: `databricks-bge-large-en` (built-in)
- Sync mode: TRIGGERED (syncs when Delta table updates)

**Why it's better than FAISS:**
| Feature | FAISS (v1) | Vector Search (v2) |
|---------|-----------|---------------------|
| Persistence | In-memory only | Managed, persistent |
| Auto-sync | ❌ Manual rebuild | ✅ Delta Sync |
| Scaling | Single machine | Distributed |
| Embeddings | External (Google Gemini) | Built-in (BGE-Large) |
| Governance | None | Unity Catalog managed |

#### 4. Databricks AI Gateway
**What it does:** Centralized LLM routing and management. Supports multiple LLM providers with a single API.

**How AgriSarthi uses it:**
- Endpoint: `databricks-meta-llama-3-3-70b-instruct`
- Used by all agents via `ChatDatabricks` LangChain integration
- Automatically handles rate limiting, load balancing, and failover

```python
from langchain_community.chat_models import ChatDatabricks

llm = ChatDatabricks(
    endpoint="databricks-meta-llama-3-3-70b-instruct",
    temperature=0,
)
```

#### 5. Foundation Model API
**What it does:** Pay-per-token access to foundation models hosted on Databricks.

**How AgriSarthi uses it:**
- Llama 3.3 70B Instruct for agent reasoning
- BGE-Large-EN for vector embeddings
- No GPU provisioning, no model hosting — just API calls

#### 6. Mosaic AI Agent Framework (Agent Bricks)
**What it does:** Production framework for building, testing, and deploying AI agents with tool-calling.

**How AgriSarthi uses it:**
- Multi-agent workflow: Supervisor → Specialist → FinalAnswer
- Tool-calling: 6 registered LangChain tools
- `databricks.agents.deploy()` for one-command deployment
- Auto-captures inference logs in Unity Catalog

#### 7. Model Serving
**What it does:** Auto-scaling REST endpoint infrastructure for serving ML models and agents.

**How AgriSarthi uses it:**
- Endpoint: `agents_agrisarthi-main-agrisarthi_agent`
- Auto-scales from 0 to handle traffic spikes
- REST API: `POST /serving-endpoints/.../invocations`
- Environment variables via Databricks Secrets

#### 8. MLflow
**What it does:** Complete ML lifecycle management — experiment tracking, model registry, tracing.

**How AgriSarthi uses it:**
- Experiment: `/Users/.../agrisarthi-agent-traces`
- Auto-logs all LangChain/LangGraph traces via `mlflow.langchain.autolog()`
- Model registered in Unity Catalog: `agrisarthi.main.agrisarthi_agent`
- Evaluation with 14 test cases across 5 domains

#### 9. Models-from-Code
**What it does:** Log ML models as Python code files (not pickled objects) for better reproducibility.

**How AgriSarthi uses it:**
- Agent code saved as `agrisarthi_agent_code.py`
- Contains full agent definition: state, tools, workflow graph
- `mlflow.models.set_model(agrisarthi_agent)` at the end
- MLflow loads and runs this code at serving time

#### 10. AI Playground
**What it does:** Interactive web UI for testing deployed agents and models.

**How AgriSarthi uses it:**
- Test agent responses before going live
- Try different prompts and verify tool-calling
- Accessible directly from Databricks workspace

#### 11. Databricks Secrets
**What it does:** Secure key-value store for sensitive configuration.

**How AgriSarthi uses it:**
- Scope: `agrisarthi`
- Keys: `databricks-host`, `databricks-token`, `sql-warehouse-id`, `openweathermap-key`, `datagov-api-key`, `sarvam-api-key`
- Referenced in Model Serving: `{{secrets/agrisarthi/openweathermap-key}}`

#### 12. Databricks Workflows (Jobs)
**What it does:** Scheduled and triggered data pipelines.

**How AgriSarthi uses it:**
- `07_mandi_price_job.py` runs daily at 6 AM IST
- Pulls fresh market prices from data.gov.in
- Upserts into `agrisarthi.main.mandi_prices` Delta table
- Agent automatically sees updated prices on next query

#### 13. AI/BI Dashboards
**What it does:** Live analytics dashboards powered by Delta Lake.

**How AgriSarthi uses it:**
- 7 analytics views created (daily queries, agent distribution, tool usage, etc.)
- Dashboard panels: Line charts, pie charts, bar charts, heatmaps
- Real-time farmer engagement metrics

#### 14. Genie
**What it does:** Natural language interface for data analytics ("How many farmers asked about weather?")

**How AgriSarthi uses it:**
- Connected to conversation_logs and farmer_features tables
- Stakeholders can ask questions without writing SQL
- Example: "Which government scheme is most popular?"

#### 15. Lakebase
**What it does:** Serverless PostgreSQL for operational data (sessions, state).

**How AgriSarthi uses it:**
- Tables: `sessions`, `messages`
- Stores conversation history per session
- Persists across restarts (unlike v1's in-memory state)
- Accessed via `asyncpg` connection pool

#### 16. Databricks CLI
**What it does:** Command-line tool for workspace automation.

**How AgriSarthi uses it:**
- Configure `databricks.yml` for project deployment
- Upload notebooks, manage secrets
- Automate CI/CD pipelines

---

## 7. System Architecture — Layer by Layer

### Layer 1: Farmer Access Layer

This is where farmers interact with AgriSarthi. Three independent frontends, each optimized for its channel:

| Component | Technology | Port | Protocol |
|-----------|-----------|------|----------|
| Web Chat | React 18 + react-markdown + Heroicons | 3000 | HTTP |
| Phone Call | Twilio Programmable Voice | PSTN | SIP/WebSocket |
| WhatsApp | WPPConnect Server + webhook | 8001 | HTTP |

### Layer 2: Gateway Layer

The **FastAPI Gateway** (`backend/gateway.py`) is the nerve center. It:
- Handles all HTTP/WebSocket/SSE connections
- Routes requests to the Databricks agent
- Proxies Sarvam AI calls (to avoid browser CORS issues)
- Manages voice WebSocket connections for Twilio

```python
app = FastAPI(title="AgriSarthi — Databricks-Powered Farming Assistant")

# Endpoints:
# POST /chat          → SSE streaming response
# POST /chat/sync     → Synchronous response
# POST /api/translate  → Sarvam translation proxy
# POST /api/tts        → Sarvam TTS proxy
# WS   /ws/voice-stream → Twilio media stream
# POST /voice/incoming-call → TwiML generation
# GET  /health         → System health check
```

### Layer 3: Language Layer

**Sarvam AI** handles all Indic language processing:

| Service | Model | Input → Output |
|---------|-------|----------------|
| STT | saaras:v2.5 | Hindi/Tamil/... audio → English text |
| Translation | mayura:v1 | English ↔ 11 Indian languages |
| TTS | bulbul:v2 | Text → Hindi/Tamil/... audio |

**Why Sarvam AI?**
- Best-in-class for Indian languages (better than Google for Indic scripts)
- Single API for STT + Translation + TTS
- `speech-to-text-translate` endpoint combines STT + translation in one call

### Layer 4: AI Agent Layer (on Databricks)

The heart of the system — see [Section 9](#9-ai-agent-workflow--how-the-brain-works) for the complete deep-dive.

### Layer 5: Data Layer (on Databricks)

All structured data in Delta Lake, vectors in Vector Search — see [Section 10](#10-data-layer--delta-lake-unity-catalog-vector-search).

### Layer 6: Observability Layer (on Databricks)

Every interaction is logged, traced, and visualized — see [Section 12](#12-observability--evaluation).

---

## 8. Channel Deep-Dive — Web, Voice, WhatsApp

### 8.1 Web Chat Channel

```
                    ┌──────────────────────┐
                    │     React Frontend    │
                    │  ┌────────────────┐   │
                    │  │   Chat.js      │   │
                    │  │  - Message list │   │
                    │  │  - SSE parser   │   │
                    │  │  - Markdown     │   │
                    │  └────────┬───────┘   │
                    │           │            │
                    │  ┌────────▼───────┐   │
                    │  │ sarvamService  │   │
                    │  │  - Translate   │   │
                    │  │  - TTS         │   │
                    │  └────────┬───────┘   │
                    └───────────┼────────────┘
                                │
                    POST /chat  │  (SSE streaming)
                                ▼
                    ┌──────────────────────┐
                    │   FastAPI Gateway     │
                    │   stream_generator()  │
                    │   → invoke_streaming  │
                    │   → word chunking     │
                    └──────────┬───────────┘
                               │
                    POST /invocations
                               ▼
                    ┌──────────────────────┐
                    │  Databricks Agent     │
                    └──────────────────────┘
```

**Key design decisions:**
- **SSE streaming via word chunking**: Databricks Model Serving doesn't support native SSE, so we invoke synchronously and break the response into 3-word chunks with 30ms delays
- **Sarvam proxy**: Translation and TTS calls go through the gateway (`/api/translate`, `/api/tts`) to avoid CORS issues from the browser
- **23 supported languages**: The frontend language selector supports all Sarvam-supported Indic languages

**User experience flow:**
1. Farmer types message (any language)
2. Frontend sends POST to `/chat`
3. Backend invokes Databricks agent
4. Response streams back as SSE word chunks
5. Farmer can click 🔊 to hear the response (via TTS)
6. Farmer can click 🌐 to translate to their language

### 8.2 Voice Call Channel (Twilio)

```
┌──────────┐    ┌─────────┐    ┌──────────────┐    ┌──────────────┐
│  Farmer  │───→│  Twilio │───→│  ngrok/host  │───→│  FastAPI     │
│  Phone   │    │  Cloud  │    │  tunnel      │    │  Gateway     │
│  (PSTN)  │←───│  (PSTN) │←───│              │←───│              │
└──────────┘    └─────────┘    └──────────────┘    └──────────────┘
                     │                                      │
                     │  POST /voice/incoming-call            │
                     ▼                                      │
                ┌─────────┐                                 │
                │  TwiML   │                                │
                │ <Connect>│                                │
                │  <Stream>│                                │
                │  wss://  │                                │
                └────┬────┘                                 │
                     │                                      │
                     │  WebSocket /ws/voice-stream          │
                     ▼                                      ▼
                ┌─────────────────────────────────────────────┐
                │           twilio_handler.py                  │
                │                                             │
                │  ┌─ Greeting TTS (Hindi) ────────┐         │
                │  │ "Namaste! Main Agri Sarthi..." │         │
                │  └───────────────────────────────┘         │
                │                                             │
                │  LOOP:                                      │
                │  ┌─ Collect mu-law audio chunks ──┐         │
                │  │ Silence detection (1.2s gap)   │         │
                │  │ Min speech: 800ms              │         │
                │  │ Max speech: 15s                │         │
                │  └──────────────┬─────────────────┘         │
                │                 │                            │
                │  ┌──────────────▼─────────────────┐         │
                │  │ mulaw_chunks → WAV (16kHz)     │         │
                │  │ Sarvam STT → English text      │         │
                │  │ Databricks Agent → Response     │         │
                │  │ Sarvam TTS → Hindi WAV         │         │
                │  │ WAV → mu-law chunks (640B)     │         │
                │  │ Send chunks to Twilio stream   │         │
                │  └────────────────────────────────┘         │
                │                                             │
                └─────────────────────────────────────────────┘
```

**Key technical details:**

| Parameter | Value | Why |
|-----------|-------|-----|
| Audio format (Twilio) | mu-law, 8kHz, mono | Twilio's native format for real-time streaming |
| Audio format (Sarvam) | WAV, 16kHz, mono | Sarvam's preferred input format |
| Silence threshold | 1000 RMS | Filters background noise while catching speech |
| Silence duration | 1200ms | 1.2 seconds of silence = end of utterance |
| Min speech | 800ms | Avoids processing accidental sounds |
| Max speech | 15,000ms | Force-process to prevent memory buildup |
| mu-law chunk size | 640 bytes | 80ms of audio at 8kHz, smooth playback |
| SQL warmup | SELECT 1 | Wakes up serverless warehouse before agent call |

**Voice-specific challenges solved:**
1. **`ws://` vs `wss://`**: Auto-detect via `X-Forwarded-Proto` header from ngrok
2. **Audio chunk size**: 640-byte base64 chunks prevent Twilio buffer overflow
3. **SQL warehouse cold start**: Warmup query + retry logic prevents timeouts
4. **Agent raw JSON in TTS**: Extract last `type=="ai"` message, skip tool_calls

### 8.3 WhatsApp Channel

```
┌───────────────┐     ┌──────────────┐     ┌──────────────┐
│  Farmer's     │────→│  WPPConnect  │────→│  FastAPI     │
│  WhatsApp     │     │  Server      │     │  (port 8001) │
│  App          │←────│  (Session)   │←────│  /webhook    │
└───────────────┘     └──────────────┘     └──────┬───────┘
                                                   │
                                    ┌──────────────┤
                                    │              │
                             ┌──────▼──────┐ ┌─────▼──────┐
                             │  Sarvam AI  │ │ Databricks │
                             │  translate  │ │ Agent      │
                             │  detect     │ │ invoke()   │
                             │  TTS        │ │            │
                             └─────────────┘ └────────────┘
```

**Message processing pipeline:**

```
1. WhatsApp message arrives
   └─ WPPConnect webhook → POST /webhook {event: "onmessage", body: "...", type: "chat"|"ptt"}

2. Message aggregation (WAIT_TIME = 2 seconds)
   └─ Multiple messages from same sender are combined

3. Voice message handling (type == "ptt")
   └─ base64 audio → Groq Whisper STT → text

4. Language detection
   └─ langdetect library → "hi" → mapped to "hi-IN"

5. Translation to English (if needed)
   └─ Sarvam mayura:v1 → English text

6. Databricks agent invocation
   └─ requests.post(databricks_endpoint, ...) → agent response

7. Translation back to farmer's language
   └─ Sarvam mayura:v1 → Hindi/Tamil/... text

8. Response delivery
   ├─ Text message → WPPConnect send_message()
   └─ Voice reply  → Sarvam TTS → WPPConnect send_voice()
```

**WhatsApp-specific features:**
- **Message aggregation**: Waits 2 seconds to combine multiple rapid messages
- **Voice message support**: Groq Whisper transcribes WhatsApp voice notes
- **Voice reply**: If farmer sent voice, bot replies with voice (TTS)
- **Error recovery**: Sends text fallback if TTS fails

---

## 9. AI Agent Workflow — How the Brain Works

### Multi-Agent Architecture

AgriSarthi uses a **Supervisor → Specialist → FinalAnswer** pattern, implemented as a LangGraph state machine:

```
                    ┌───────────────────┐
                    │   User Message    │
                    │  "What crops      │
                    │   should I grow   │
                    │   in Lucknow?"    │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │   SUPERVISOR      │
                    │   Agent           │
                    │                   │
                    │  Analyzes query:  │
                    │  "crop" + "grow"  │
                    │  → SoilCropAdvsr  │
                    └────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──────┐ ┌────▼─────┐ ┌──────▼───────┐
     │ SoilCrop      │ │ Market   │ │ Financial    │
     │ Advisor       │ │ Analyst  │ │ Advisor      │
     │               │ │          │ │              │
     │ Tools:        │ │ Tools:   │ │ Tools:       │
     │ • soil_data   │ │ • market │ │ • scheme     │
     │ • weather     │ │   _price │ │   _search    │
     │ • disaster    │ │          │ │              │
     │ • crop_rec    │ │          │ │              │
     └────────┬──────┘ └────┬─────┘ └──────┬───────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼──────────┐
                    │  TOOL EXECUTION   │
                    │  (ToolNode)       │
                    │                   │
                    │  Calls actual     │
                    │  functions:       │
                    │  SQL queries,     │
                    │  API calls, etc.  │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  FINAL ANSWER     │
                    │  Agent            │
                    │                   │
                    │  Synthesizes a    │
                    │  farmer-friendly  │
                    │  response in      │
                    │  simple language  │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  "Lucknow mein   │
                    │   Alluvial soil  │
                    │   hai (pH 7.2).  │
                    │   Wheat, Rice,   │
                    │   Maize ugaiye." │
                    └───────────────────┘
```

### Routing Rules

| Query Contains | Routes To | Tools Used |
|---------------|-----------|------------|
| soil, crop, farming, grow | SoilCropAdvisor | soil_data_retriever, crop_recommendation_tool |
| weather, rain, temperature | SoilCropAdvisor | weather_alert_tool |
| flood, cyclone, disaster | SoilCropAdvisor | disaster_alert_tool |
| price, mandi, market, rate | MarketAnalyst | market_price_tool |
| scheme, subsidy, loan, PM-KISAN | FinancialAdvisor | scheme_search_tool |
| hello, namaste, general | FinalAnswerAgent | (none — direct LLM response) |

### Agent State Machine

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: Literal["Supervisor", "SoilCropAdvisor", "MarketAnalyst",
                        "FinancialAdvisor", "FinalAnswerAgent", "end"]
```

### LangGraph Flow

```
Entry → Supervisor
         │
         ├─── SoilCropAdvisor ──┬── tools → FinalAnswerAgent → END
         │                      └── FinalAnswerAgent → END
         │
         ├─── MarketAnalyst ────┬── tools → FinalAnswerAgent → END
         │                      └── FinalAnswerAgent → END
         │
         ├─── FinancialAdvisor ─┬── tools → FinalAnswerAgent → END
         │                      └── FinalAnswerAgent → END
         │
         └─── FinalAnswerAgent → END
```

---

## 10. Data Layer — Delta Lake, Unity Catalog, Vector Search

### Schema: `agrisarthi.main`

#### Table: `soil_data`
| Column | Type | Description |
|--------|------|-------------|
| state | STRING | Indian state name |
| district | STRING | District name (primary key for VS) |
| soil_type | STRING | Soil classification (Alluvial, Red, Black, etc.) |
| ph | DOUBLE | pH level (0-14) |
| organic_carbon | DOUBLE | Organic carbon percentage |
| nitrogen | DOUBLE | Nitrogen content (kg/ha) |
| phosphorus | DOUBLE | Phosphorus content (kg/ha) |
| potassium | DOUBLE | Potassium content (kg/ha) |
| rainfall | DOUBLE | Average annual rainfall (mm) |
| temperature | DOUBLE | Average temperature (°C) |
| soil_text | STRING | Generated text for Vector Search embeddings |

#### Table: `mandi_prices`
| Column | Type | Description |
|--------|------|-------------|
| crop_name | STRING | Commodity name (Wheat, Rice, etc.) |
| state | STRING | Indian state |
| district | STRING | District name |
| market | STRING | Mandi/market name |
| min_price | DOUBLE | Minimum price (₹/Quintal) |
| max_price | DOUBLE | Maximum price (₹/Quintal) |
| modal_price | DOUBLE | Most common price (₹/Quintal) |
| unit | STRING | Unit of measurement (Quintal) |
| arrival_date | STRING | Date of price recording (YYYY-MM-DD) |

**Data source:** Government of India Open Data API (`data.gov.in`)
**Refresh:** Daily via Databricks Workflow (Notebook 07)

#### Table: `govt_schemes`
| Column | Type | Description |
|--------|------|-------------|
| scheme_name | STRING | Short name (PM-KISAN, PM-KUSUM, etc.) |
| full_name | STRING | Full official name |
| category | STRING | Category (Solar, Insurance, Credit, etc.) |
| description | STRING | Detailed description |
| eligibility | STRING | Who can apply |
| subsidy_percent | INT | Subsidy percentage |
| ministry | STRING | Responsible ministry |
| website | STRING | Official website URL |
| states | STRING | Coverage area |
| documents_required | STRING | Documents needed to apply |

**Schemes included:** PM-KUSUM, PM-KISAN, PMFBY, Soil Health Card, KCC, eNAM, SMAM, NMSA, PKVY, RKVY

#### Table: `conversation_logs`
| Column | Type | Description |
|--------|------|-------------|
| session_id | STRING | Unique session identifier |
| farmer_id | STRING | Farmer identifier (phone number or session) |
| channel | STRING | web, voice, or whatsapp |
| user_message | STRING | What the farmer said |
| agent_response | STRING | What the agent replied |
| language | STRING | Detected language code |
| response_time_ms | DOUBLE | End-to-end latency |
| timestamp | TIMESTAMP | When the conversation happened |

### Vector Search Index

```
Index: agrisarthi.main.soil_vector_index
├── Endpoint: agrisarthi-vs-endpoint
├── Source table: agrisarthi.main.soil_data
├── Embedding column: soil_text
├── Embedding model: databricks-bge-large-en
├── Primary key: district
├── Sync mode: TRIGGERED
└── Query example:
    index.similarity_search(
        query_text="soil data for Lucknow",
        columns=["state", "district", "soil_type", "ph", "soil_text"],
        num_results=3
    )
```

---

## 11. Notebooks — The Deployment Pipeline

AgriSarthi has **7 Databricks notebooks**, each handling a specific phase:

```
┌────────────────────────────────────────────────────────────────┐
│             NOTEBOOK EXECUTION PIPELINE                        │
│                                                                │
│  01_data_ingestion.py ──→ Load CSV data into Delta Lake       │
│         │                 Create Vector Search index            │
│         │                 Insert government schemes             │
│         ▼                 Set up mandi prices table             │
│  02_agent_tools.py ───→ Define 6 LangChain tools              │
│         │                 Connect to Vector Search               │
│         │                 Connect to Delta tables                │
│         ▼                                                       │
│  03_agent_workflow.py → Build LangGraph multi-agent            │
│         │                 Configure AI Gateway LLM              │
│         │                 Register on MLflow (models-from-code) │
│         ▼                                                       │
│  04_deploy_serving.py → Deploy via agents.deploy()             │
│         │                 Wait for endpoint READY               │
│         │                 Test with sample queries              │
│         ▼                                                       │
│  05_dashboard.py ─────→ Create 7 analytics SQL views           │
│         │                 Set up AI/BI Dashboard layout          │
│         │                 Configure Genie integration            │
│         ▼                                                       │
│  06_evaluation.py ────→ 14 test cases across 5 domains         │
│         │                 Fact-checking evaluator                │
│         │                 MLflow metrics logging                 │
│         ▼                                                       │
│  07_mandi_price_job.py → Scheduled daily at 6 AM IST          │
│                           Pull from data.gov.in API             │
│                           Deduplicate and MERGE INTO Delta      │
└────────────────────────────────────────────────────────────────┘
```

### Notebook Details

| # | Notebook | Duration | Technologies | Purpose |
|---|----------|----------|-------------|---------|
| 01 | `data_ingestion.py` | ~5 min | Delta Lake, Unity Catalog, Vector Search | Load all data into Databricks |
| 02 | `agent_tools.py` | ~1 min | Vector Search, Delta Lake, External APIs | Define 6 tools for the agent |
| 03 | `agent_workflow.py` | ~3 min | AI Gateway, LangGraph, MLflow | Build and register the multi-agent |
| 04 | `deploy_serving.py` | ~15 min | Model Serving, Agent Framework | Deploy agent as REST endpoint |
| 05 | `dashboard.py` | ~1 min | AI/BI, Genie, Delta Lake | Create analytics infrastructure |
| 06 | `evaluation.py` | ~5 min | MLflow, Model Serving | Test agent quality |
| 07 | `mandi_price_job.py` | ~2 min | Delta Lake, Workflows | Refresh mandi prices daily |

---

## 12. Observability & Evaluation

### MLflow Tracing

Every conversation through the agent is automatically traced:

```
MLflow Trace for: "What is wheat price in Lucknow?"
│
├── Supervisor Agent (45ms)
│   └── LLM call: "MarketAnalyst"
│
├── MarketAnalyst (120ms)
│   └── LLM call → tool_calls: [market_price_tool]
│
├── Tool: market_price_tool (800ms)
│   └── SQL query on Delta Lake
│   └── Result: "Wheat at Lucknow: ₹2100-₹2350..."
│
└── FinalAnswerAgent (200ms)
    └── LLM call: synthesize response
    └── Total: 1165ms
```

### Evaluation Framework

14 test cases across 5 domains:

| Domain | Test Cases | Expected Facts |
|--------|-----------|---------------|
| Soil/Crop | 3 | wheat, rice, soil, pH, Karnataka |
| Market | 3 | wheat, rice, ₹, price, quintal |
| Finance | 4 | PM-KISAN, PM-KUSUM, PMFBY, KCC, subsidy |
| Weather | 1 | temperature, humidity |
| Disaster | 1 | alert, flood |
| General | 2 | help, yield, fertilizer |

**Evaluation metric:** At least 50% of expected facts must appear in response.

### AI/BI Dashboard Views

| View | Chart Type | Metrics |
|------|-----------|---------|
| `v_daily_queries` | Line chart | Queries/day, unique farmers, P95 latency |
| `v_agent_distribution` | Pie chart | Which agent handles most queries |
| `v_tool_usage` | Heatmap | Tool calls by day |
| `v_language_distribution` | Donut chart | Hindi vs Tamil vs Bengali, etc. |
| `v_crop_interest` | Bar chart | Most asked-about crops |
| `v_state_engagement` | Map | Farmers by state |
| `v_scheme_interest` | Horizontal bar | Most popular government schemes |

---

## 13. Multilingual & Voice Architecture

### Language Support Matrix

| # | Language | Code | STT | Translation | TTS | Web | Phone | WhatsApp |
|---|----------|------|-----|------------|-----|-----|-------|----------|
| 1 | Hindi | hi-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | Bengali | bn-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | Tamil | ta-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | Telugu | te-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5 | Kannada | kn-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | Malayalam | ml-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 7 | Marathi | mr-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 8 | Gujarati | gu-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 9 | Odia | od-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 10 | Punjabi | pa-IN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 11 | English | en-IN | ✅ | — | ✅ | ✅ | ✅ | ✅ |

### Audio Processing Pipeline (Voice Calls)

```
                         TWILIO (mu-law, 8kHz)
                              │
                    ┌─────────▼──────────┐
                    │  Base64 decode      │
                    │  mu-law → PCM (8kHz)│
                    │  PCM → PCM (16kHz)  │  ← audioop.ratecv
                    │  PCM → WAV          │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Sarvam STT         │
                    │  (saaras:v2.5)      │
                    │  WAV → Text + Lang  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Databricks Agent   │
                    │  Text → Response    │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Sarvam TTS         │
                    │  (bulbul:v2)        │
                    │  Text → WAV (base64)│
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  WAV → PCM          │
                    │  PCM → PCM (8kHz)   │  ← audioop.ratecv
                    │  PCM → mu-law       │  ← audioop.lin2ulaw
                    │  mu-law → 640B chunks│
                    │  chunks → base64    │
                    └─────────┬──────────┘
                              │
                         TWILIO (mu-law, 8kHz)
```

---

## 14. Security & Secrets Management

### Secrets Architecture

```
┌──────────────────────────────────────────┐
│        DATABRICKS SECRETS                │
│        Scope: agrisarthi                 │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ databricks-host     → workspace URL│  │
│  │ databricks-token    → PAT         │  │
│  │ sql-warehouse-id    → Warehouse ID│  │
│  │ openweathermap-key  → Weather API │  │
│  │ datagov-api-key     → Mandi API   │  │
│  │ sarvam-api-key      → Sarvam AI   │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Referenced in Model Serving as:         │
│  {{secrets/agrisarthi/openweathermap-key}}│
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│        LOCAL .env FILE                   │
│        (NOT committed to git)            │
│                                          │
│  DATABRICKS_HOST=https://dbc-...         │
│  DATABRICKS_TOKEN=dapi...                │
│  SARVAM_API_KEY=sk_...                   │
│  TWILIO_ACCOUNT_SID=AC...                │
│  TWILIO_AUTH_TOKEN=eb...                 │
│  WPPCONNECT_TOKEN=...                    │
│  GROQ_API_KEY=gsk_...                    │
└──────────────────────────────────────────┘
```

**Security measures:**
- `.env` file in `.gitignore` — never committed
- GitHub push protection enabled — blocks accidental secret pushes
- Databricks Secrets for all production credentials
- Model Serving uses `{{secrets/...}}` syntax — secrets never exposed in code

---

## 15. Project Structure — Complete Codebase Map

```
Agri-Sarthi/
│
├── backend/                          # WEB + VOICE GATEWAY
│   ├── gateway.py                    # FastAPI app — all HTTP/WS/SSE endpoints
│   │                                 #   /chat, /chat/sync, /api/translate
│   │                                 #   /api/tts, /ws/voice-stream
│   │                                 #   /voice/incoming-call, /health
│   │
│   ├── client.py                     # DatabricksAgentClient class
│   │                                 #   invoke(), invoke_streaming()
│   │                                 #   log_conversation() via SQL API
│   │                                 #   health_check()
│   │                                 #   LakebaseSessionStore class
│   │
│   ├── requirements.txt              # fastapi, uvicorn, httpx, python-dotenv
│   │
│   └── voice/                        # TWILIO PHONE CALL MODULE
│       ├── __init__.py               # Package marker
│       ├── audio_utils.py            # mu-law ↔ WAV transcoding
│       │                             #   is_silence(), mulaw_chunks_to_wav()
│       │                             #   wav_to_mulaw(), constants
│       ├── sarvam_voice.py           # Async Sarvam AI (STT/TTS/translate)
│       │                             #   speech_to_text_translate()
│       │                             #   translate_text(), text_to_speech()
│       ├── twilio_handler.py         # WebSocket handler for Twilio streams
│       │                             #   handle_media_stream()
│       │                             #   _warmup_sql_warehouse()
│       │                             #   _invoke_agent(), _process_audio()
│       │                             #   Silence detection, greeting TTS
│       ├── models.py                 # Pydantic models (VoiceCallCreate, etc.)
│       └── views.py                  # Public API functions
│                                     #   handle_incoming_call() → TwiML
│                                     #   create_outbound_call()
│                                     #   get_call_history/transcript()
│
├── whatsapp/                         # WHATSAPP BOT (STANDALONE SERVER)
│   ├── main.py                       # FastAPI app (port 8001), /webhook
│   │                                 #   Message aggregation (2s buffer)
│   │                                 #   Voice transcription (Groq Whisper)
│   │                                 #   Language detect → translate → agent
│   │                                 #   → translate back → send reply
│   │
│   ├── databricks_client.py          # invoke_agent() — calls Model Serving
│   │
│   ├── sarvam.py                     # Sarvam AI sync client
│   │                                 #   detect_language(), translate_text()
│   │                                 #   text_to_speech(), speech_to_text()
│   │
│   ├── requirements.txt              # fastapi, requests, langdetect, groq
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── config.py                 # Groq client setup
│   │   └── logging.py               # Loguru logger configuration
│   │
│   └── wppconnect/
│       ├── __init__.py
│       └── api.py                    # send_message(), send_voice()
│                                     #   WPPConnect REST API wrapper
│
├── frontend/                         # REACT WEB APPLICATION
│   ├── package.json                  # react, react-markdown, uuid, heroicons
│   ├── public/
│   │   ├── index.html                # HTML template
│   │   ├── manifest.json             # PWA manifest
│   │   └── robots.txt
│   │
│   └── src/
│       ├── App.js                    # Root component with routing
│       ├── App.css                   # Global styles
│       ├── index.js                  # React entry point
│       ├── index.css                 # Base CSS
│       │
│       ├── components/
│       │   ├── Chat.js               # Main chat UI — SSE streaming
│       │   ├── Chat.css              # Chat bubble styles
│       │   ├── Header.js             # App header with branding
│       │   ├── Header.css
│       │   ├── Footer.js             # Language selector footer
│       │   ├── Footer.css
│       │   ├── HomePage.js           # Landing page
│       │   ├── HomePage.css
│       │   ├── MessageActions.js     # Translate 🌐 + TTS 🔊 buttons
│       │   └── MessageActions.css
│       │
│       └── services/
│           └── sarvamService.js      # Sarvam API client (via gateway proxy)
│                                     #   translateText(), textToSpeech()
│                                     #   23 SUPPORTED_LANGUAGES
│
├── notebooks/                        # DATABRICKS NOTEBOOKS
│   ├── 01_data_ingestion.py          # Upload data → Delta Lake + Vector Search
│   ├── 02_agent_tools.py             # Define 6 LangChain tools
│   ├── 03_agent_workflow.py          # Build LangGraph agent + MLflow register
│   ├── 04_deploy_serving.py          # Deploy via agents.deploy()
│   ├── 05_dashboard.py              # Create analytics views + dashboard
│   ├── 06_evaluation.py              # 14 test cases + MLflow evaluation
│   └── 07_mandi_price_job.py         # Daily mandi price refresh job
│
├── scripts/                          # UTILITY SCRIPTS (run locally)
│   ├── ingest_mandi_local.py         # Fetch 678+ mandi prices from data.gov.in
│   ├── setup_twilio.py               # Configure Twilio webhook URL
│   └── setup_wppconnect.py           # Generate WPPConnect API token
│
├── docs/                             # DOCUMENTATION
│   ├── ARCHITECTURE.md               # Architecture overview
│   ├── DEPLOYMENT_GUIDE.md           # Step-by-step deployment
│   └── DESIGN_DOCUMENT.md            # ← THIS FILE (Master Design Doc)
│
├── .env.example                      # Template for environment variables
├── .gitignore                        # Ignores .env, __pycache__, node_modules
├── LICENSE                           # MIT License
├── README.md                         # Project overview + quick start
└── databricks.yml                    # Databricks CLI configuration
```

**Line count summary:**

| Component | Files | Approximate Lines |
|-----------|-------|-------------------|
| Backend Gateway | 2 | ~510 |
| Voice Module | 5 | ~650 |
| WhatsApp Bot | 6 | ~400 |
| React Frontend | 10 | ~1,200 |
| Databricks Notebooks | 7 | ~2,200 |
| Scripts | 3 | ~350 |
| Docs | 3 | ~800 |
| **Total** | **36** | **~6,100** |

---

## 16. API Reference

### Backend Gateway (port 8000)

#### `POST /chat` — Streaming Chat
```json
// Request
{
  "message": "What is wheat price in Lucknow?",
  "thread_id": "uuid-v4",
  "language": "en-IN",
  "channel": "web"
}

// Response (SSE stream)
data: {"content": "Lucknow mandi "}
data: {"content": "mein gehun "}
data: {"content": "ka bhav "}
data: {"content": "₹2,100-₹2,350 "}
data: {"content": "per quintal hai."}
data: [DONE]
```

#### `POST /chat/sync` — Synchronous Chat
```json
// Request
{
  "message": "Tell me about PM-KISAN scheme",
  "thread_id": "uuid-v4"
}

// Response
{
  "response": "PM-KISAN is a central government scheme that provides ₹6,000 per year...",
  "session_id": "uuid-v4",
  "response_time_ms": 3456.78
}
```

#### `POST /api/translate` — Translation Proxy
```json
// Request
{
  "input": "Hello farmer! How can I help?",
  "source_language_code": "en-IN",
  "target_language_code": "hi-IN",
  "model": "mayura:v1"
}

// Response
{
  "translated_text": "नमस्ते किसान! मैं कैसे मदद कर सकता हूँ?"
}
```

#### `POST /api/tts` — Text-to-Speech Proxy
```json
// Request
{
  "text": "गेहूं का भाव ₹2,250 प्रति क्विंटल है",
  "target_language_code": "hi-IN",
  "speaker": "anushka",
  "model": "bulbul:v2"
}

// Response
{
  "audios": ["base64-encoded-wav-audio..."]
}
```

#### `POST /voice/incoming-call` — Twilio Webhook
```xml
<!-- Response (TwiML) -->
<Response>
  <Connect>
    <Stream url="wss://your-ngrok-url.ngrok-free.app/ws/voice-stream"/>
  </Connect>
</Response>
```

#### `GET /health` — Health Check
```json
{
  "status": "healthy",
  "databricks_agent": "healthy",
  "voice_agent": "enabled",
  "session_store": "lakebase",
  "version": "2.0.0"
}
```

### WhatsApp Bot (port 8001)

#### `POST /webhook` — WPPConnect Message Handler
```json
// Request (from WPPConnect)
{
  "event": "onmessage",
  "session": "agrisarthi",
  "body": "गेहूं का भाव बताओ",
  "type": "chat",
  "isNewMsg": true,
  "sender": {"id": "919876543210@c.us"}
}

// Response
{"status": "aggregating"}
```

---

## 17. Deployment Guide — End to End

### Prerequisites

| # | Requirement | Details |
|---|-------------|---------|
| 1 | Python 3.11+ | Backend and WhatsApp bot |
| 2 | Node.js 18+ | React frontend |
| 3 | Databricks workspace | With Model Serving enabled |
| 4 | Sarvam AI API key | For multilingual support |
| 5 | Twilio account | For phone calls (optional) |
| 6 | ngrok | For exposing local server to Twilio |

### Step-by-Step Deployment

```
PHASE 1: DATABRICKS SETUP
├── 1. Create Databricks workspace
├── 2. Create secret scope: databricks secrets create-scope agrisarthi
├── 3. Add secrets (6 keys)
├── 4. Upload soildata.csv to Unity Catalog Volumes
├── 5. Run notebooks 01-07 in order
└── 6. Verify agent endpoint is READY in Serving UI

PHASE 2: LOCAL BACKEND
├── 1. Clone repo: git clone https://github.com/HimanshuMohanty-Git24/Agri-Sarthi
├── 2. Copy .env.example to .env, fill credentials
├── 3. pip install -r backend/requirements.txt
├── 4. uvicorn backend.gateway:app --host 0.0.0.0 --port 8000
└── 5. Test: curl http://localhost:8000/health

PHASE 3: FRONTEND
├── 1. cd frontend && npm install
├── 2. npm start
└── 3. Open http://localhost:3000

PHASE 4: VOICE (OPTIONAL)
├── 1. Install ngrok, start tunnel: ngrok http 8000
├── 2. Copy ngrok HTTPS URL
├── 3. Set Twilio webhook: POST https://ngrok-url/voice/incoming-call
└── 4. Call Twilio number to test

PHASE 5: WHATSAPP (OPTIONAL)
├── 1. Start WPPConnect server: cd wppconnect-server && npm run dev
├── 2. Scan WhatsApp QR code
├── 3. pip install -r whatsapp/requirements.txt
├── 4. uvicorn whatsapp.main:app --host 0.0.0.0 --port 8001
└── 5. Send WhatsApp message to test
```

---

## 18. Cost Analysis

### Databricks Costs (Hackathon Scope)

| Resource | Unit Cost | Usage | Daily Cost |
|----------|----------|-------|------------|
| Model Serving (serverless) | ~$0.07/DBU | ~50-100 requests/day | ~$2-5 |
| SQL Warehouse (serverless) | ~$0.22/DBU | Auto-suspend, on-demand | ~$1-3 |
| Vector Search | ~$0.072/hour | Standard endpoint | ~$1.7 |
| Delta Lake storage | ~$0.02/GB/month | <1GB | ~$0.01 |
| Foundation Model API | ~$0.001/1K tokens | ~100K tokens/day | ~$0.10 |
| Lakebase | ~$0.05/hour | Serverless | ~$1 |
| **Total** | | | **~$6-11/day** |

### External Service Costs

| Service | Pricing | Usage | Monthly Cost |
|---------|---------|-------|-------------|
| Sarvam AI | Free tier + pay-as-you-go | ~500 calls/day | ~$0-20 |
| Twilio | $0.0085/min + phone ($1/month) | ~20 calls/day | ~$5-10 |
| OpenWeatherMap | Free tier (1000 calls/day) | ~100 calls/day | $0 |
| ngrok | Free tier | Tunnel | $0 |
| **Total** | | | **~$5-30/month** |

---

## 19. Future Roadmap

### Phase 1: Immediate (Post-Hackathon)
- [ ] Deploy frontend to Vercel/Netlify
- [ ] Deploy backend to Railway/Render
- [ ] Set up Databricks Workflows for automated monitoring
- [ ] Add more soil data (all 700+ districts of India)

### Phase 2: Short-Term (1-3 months)
- [ ] Implement Databricks AutoML for crop yield prediction
- [ ] Add Feature Store for personalized farmer profiles
- [ ] Build recommendation engine using historical conversation data
- [ ] Add support for image-based crop disease detection

### Phase 3: Long-Term (3-6 months)
- [ ] Scale to 1M+ farmers
- [ ] Partner with state agriculture departments for verified data
- [ ] Add marketplace feature (connect farmers to buyers)
- [ ] Implement satellite imagery integration for crop monitoring
- [ ] Multi-state deployment with localized data per region

---

## Appendix A: External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.104+ | Web framework |
| uvicorn | 0.24+ | ASGI server |
| httpx | 0.25+ | Async HTTP client |
| langchain | 0.1+ | LLM framework |
| langgraph | 0.0.40+ | Agent workflow graphs |
| mlflow | 2.9+ | Model tracking & registry |
| databricks-agents | latest | Agent deployment |
| databricks-vectorsearch | latest | Vector Search client |
| react | 18+ | Frontend UI |
| react-markdown | 9+ | Markdown rendering |
| framer-motion | 10+ | Animations |

---

## Appendix B: Environment Variables Reference

| Variable | Required By | Description |
|----------|------------|-------------|
| `DATABRICKS_HOST` | Backend, WhatsApp | Databricks workspace URL |
| `DATABRICKS_TOKEN` | Backend, WhatsApp | Personal access token |
| `DATABRICKS_AGENT_ENDPOINT` | Backend | Model Serving endpoint name |
| `DATABRICKS_SQL_WAREHOUSE_ID` | Backend (voice) | SQL warehouse for warmup |
| `SARVAM_API_KEY` | Backend | Sarvam AI (voice module) |
| `SARVAM_AI_API_KEY` | WhatsApp | Sarvam AI (WhatsApp bot) |
| `TWILIO_ACCOUNT_SID` | Backend (voice) | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Backend (voice) | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Backend (voice) | Twilio phone number |
| `GROQ_API_KEY` | WhatsApp | Groq Whisper for voice messages |
| `OPENWEATHERMAP_API_KEY` | Agent (Databricks) | Weather data |
| `WPPCONNECT_BASE_URL` | WhatsApp | WPPConnect server URL |
| `WPPCONNECT_SESSION_NAME` | WhatsApp | WPPConnect session |
| `WPPCONNECT_SECRET_KEY` | WhatsApp | WPPConnect auth secret |
| `WPPCONNECT_TOKEN` | WhatsApp | WPPConnect API token |
| `WAIT_TIME` | WhatsApp | Message aggregation delay (seconds) |

---

> **Document Version:** 2.0  
> **Last Updated:** February 2026  
> **Authors:** Team AgriSarthi  
> **Repository:** [github.com/HimanshuMohanty-Git24/Agri-Sarthi](https://github.com/HimanshuMohanty-Git24/Agri-Sarthi)
