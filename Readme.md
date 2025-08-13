# AgriSarthi: Your AI-Powered Farming Companion

**AgriSarthi** is a revolutionary platform designed to empower farmers with instant, accessible, and accurate agricultural information through a multi-channel approach. Leveraging the power of AI, AgriSarthi provides a comprehensive suite of services through a user-friendly web interface and a simple phone call.

This project aims to bridge the information gap in the agricultural sector, providing farmers with real-time data and expert advice on soil health, crop management, market prices, and government schemes.

-----
## 📺 Demo Video
**Complete Deep Dive Video:**
<br>
[![Deep Dive Video](https://img.youtube.com/vi/GqoiXhngEsc/hqdefault.jpg)](https://www.youtube.com/watch?v=GqoiXhngEsc)
<br>
**Just the Live Working Demo Video:**
[![Agri Sarthi Demo](https://img.youtube.com/vi/o0tapqYnpW4/maxresdefault.jpg)](https://youtu.be/o0tapqYnpW4?si=VWNCJLqgt3p-rFH7)

> Click the thumbnail above to watch the full demo on YouTube.
-----

## Architecture

The AgriSarthi platform is built on a modern, scalable, and modular architecture that ensures high performance and maintainability.
**LINK(Interactive Diagram) :** [LINK](https://app.eraser.io/workspace/bDVQE1A6Wi5T7KTrQhaa)
<img width="12454" height="5901" alt="diagram-export-8-13-2025-5_51_24-PM" src="https://github.com/user-attachments/assets/9ea45bb3-901d-42dd-bcc2-a93168422340" />




-----

## How It Works

AgriSarthi utilizes a sophisticated multi-agent AI system to provide specialized advice to farmers. The system is accessible through two primary channels: a web application and a voice call system.</br>
</br>
<img width="630" height="372" alt="AgriSarti agentic workflow" src="https://github.com/user-attachments/assets/d248cb70-85e7-4a8b-9032-670baf4713ef" />
</br>
### Web System

The web application provides a simple and intuitive chat interface where farmers can ask questions in their natural language.

1.  **User Interaction**: The farmer types a query into the chat interface built with **React.js**.
2.  **API Request**: The frontend sends the user's message to the **FastAPI** backend.
3.  **AI Processing**:
      * The query is received by the **Supervisor Agent**, which is the entry point of our AI core built with **LangGraph**.
      * The Supervisor Agent analyzes the query and routes it to the appropriate specialist agent:
          * **Soil & Crop Advisor**: Handles queries related to soil health, crop recommendations, farming techniques, and weather alerts. This agent uses a **RAG (Retrieval-Augmented Generation)** system with a **FAISS vector store** to provide information based on a comprehensive soil dataset (`soildata.csv`).
          * **Market Analyst**: Provides real-time market prices, mandi rates, and price trends by fetching data from external APIs.
          * **Financial Advisor**: Offers information on government schemes, subsidies, loans, and financial planning for farmers.
      * The specialist agents use the powerful and fast **Groq LLaMA3 LLM** to generate accurate and context-aware responses.
4.  **Response to User**: The generated response is streamed back to the user in the chat interface.

### Call System

For farmers who may not have access to a smartphone or the internet, AgriSarthi offers a voice call system powered by **Twilio**.

1.  **Incoming Call**: A farmer calls a designated Twilio phone number.
2.  **Twilio Webhook**: Twilio receives the call and sends a request to the FastAPI backend's `/voice/incoming-call` webhook, which is exposed to the internet using **ngrok**.
3.  **WebSocket Connection**: The backend responds with TwiML instructions to establish a real-time, bidirectional media stream over a WebSocket connection.
4.  **Real-time Processing**:
      * The farmer's speech is streamed to the backend.
      * The audio is transcribed to text in real-time.
      * The transcribed text is then processed by the same AI agent system as the web application.
      * The AI's text response is converted back to speech.
5.  **Voice Response**: The synthesized speech is streamed back to the farmer over the phone call, providing an interactive voice-based assistant.

-----

## Three-Prong Approach

AgriSarthi is designed with a three-prong approach to ensure maximum accessibility for all farmers:

1.  **Web Access**: A modern, responsive web application for users with smartphones and internet access.
2.  **Phone Access**: A simple phone call system for farmers with basic feature phones, making the service universally accessible.
3.  **WhatsApp Access**: The architecture is designed to integrate with WhatsApp, which is a widely used communication platform in India. **Please note that the WhatsApp integration is handled in a separate codebase named `Agri-Sarthi-WP`.**

-----

## Cost-Benefit Analysis & Advantages

AgriSarthi offers significant advantages over traditional systems of information dissemination in agriculture.

| Feature             | Traditional System                                       | AgriSarthi                                                               |
| ------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Accessibility** | Limited to specific hours, locations, and personnel.     | 24/7 availability from anywhere with a phone or internet connection.      |
| **Cost** | High costs associated with travel, and expert consultation. | Minimal to no cost for the farmer, leveraging low-cost internet and calls. |
| **Information Quality** | Information can be outdated or generalized.              | Real-time, personalized, and data-driven advice.                         |
| **Scalability** | Difficult to scale and reach a large number of farmers.   | Highly scalable, capable of serving millions of farmers simultaneously.  |

**Approximate Cost-Benefit:**

  * **Cost**: The operational cost of AgriSarthi is primarily driven by API usage (Twilio, Groq, Google Cloud/GenAI) and server hosting. By using efficient models and services, the cost per query can be kept extremely low.
  * **Benefit**: Farmers can experience increased crop yields, better market prices, and access to beneficial government schemes, leading to a significant increase in their income. This also leads to better resource management and more sustainable farming practices.

-----

## Getting Started

Follow these instructions to set up and run the AgriSarthi project locally.

### Prerequisites

  * **Node.js and npm**: For running the frontend.
  * **Python 3.12+**: For running the backend.
  * **Twilio Account**: With a phone number to set up the voice call system.
  * **ngrok**: To expose your local backend to the internet for Twilio webhooks.
  * **API Keys**:
      * `GROQ_API_KEY`
      * `TAVILY_API_KEY`
      * `GOOGLE_API_KEY`
      * `SARVAM_API_KEY` (if applicable)
      * `TWILIO_ACCOUNT_SID`
      * `TWILIO_AUTH_TOKEN`
      * `TWILIO_PHONE_NUMBER`

### Backend Setup

1.  **Clone the repository**:

    ```bash
    git clone <repository_url>
    cd agri_sarthi_project/backend
    ```

2.  **Create a virtual environment and activate it**:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file** in the `backend` directory and add your API keys:

    ```env
    GROQ_API_KEY="your_groq_api_key"
    TAVILY_API_KEY="your_tavily_api_key"
    GOOGLE_API_KEY="your_google_api_key"
    SARVAM_API_KEY="your_sarvam_api_key"
    TWILIO_ACCOUNT_SID="your_twilio_account_sid"
    TWILIO_AUTH_TOKEN="your_twilio_auth_token"
    TWILIO_PHONE_NUMBER="your_twilio_phone_number"
    NGROK_URL="your_ngrok_url"
    ```

5.  **Run the backend server**:

    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

### Frontend Setup

1.  **Navigate to the frontend directory**:

    ```bash
    cd ../frontend
    ```

2.  **Install dependencies**:

    ```bash
    npm install
    ```

3.  **Start the frontend development server**:

    ```bash
    npm start
    ```

    The web application will be available at `http://localhost:3000`.

### Twilio and Ngrok Setup

1.  **Start ngrok** to expose your local backend server:

    ```bash
    ngrok http 8000
    ```

2.  **Copy the ngrok URL** (the one that starts with `https://`) and update the `NGROK_URL` in your `.env` file.

3.  **Configure Twilio**:

      * Go to your Twilio console and navigate to your phone number's configuration.
      * Under "Voice & Fax", set the "A CALL COMES IN" webhook to your ngrok URL followed by `/voice/incoming-call`. For example: `https://<your-ngrok-url>.ngrok.io/voice/incoming-call`.
      * Set the HTTP method to `POST`.

4.  **Save your Twilio configuration**.

You can now call your Twilio phone number to interact with the voice agent.

-----

## Technologies Used

  * **Frontend**: React.js, CSS
  * **Backend**: FastAPI, Python
  * **AI**: LangChain, LangGraph, Groq LLaMA3
  * **Voice**: Twilio
  * **Database**: FAISS (for RAG)

  * **Deployment**: ngrok (for local development)






