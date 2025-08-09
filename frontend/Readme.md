# 🌾 Agri Sarthi Frontend

> Your AI-powered agricultural assistant for smarter farming decisions

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [API Integration](#api-integration)
- [Components](#components)
- [Styling](#styling)
- [Browser Support](#browser-support)
- [Contributing](#contributing)
- [License](#license)

## 🌟 Overview

Agri Sarthi Frontend is a modern, responsive React application that serves as the user interface for an AI-powered agricultural assistant. The application helps farmers make informed decisions about crops, soil health, market prices, weather conditions, and government schemes through an intuitive chat interface and comprehensive dashboard.

## ✨ Features

### 🤖 AI-Powered Chat Assistant

- Real-time conversational AI for agricultural queries
- Streaming responses for better user experience
- Context-aware conversations with thread management
- Quick question suggestions for common farming queries

### 🌐 Multi-language Support

- 22+ Indian languages supported via Sarvam AI
- Real-time text translation
- Text-to-speech in multiple Indian languages
- Seamless language switching

### 📱 Responsive Design

- Mobile-first approach
- Optimized for tablets and desktop
- Touch-friendly interface
- Progressive Web App capabilities

### 🎨 Modern UI/UX

- Clean, intuitive design
- Smooth animations with Framer Motion
- Accessibility compliant
- Dark/Light theme support

### 🔧 Core Functionalities

- **Crop Advisory**: Personalized crop recommendations
- **Market Prices**: Real-time mandi rates and price trends
- **Weather Alerts**: Weather forecasts and disaster warnings
- **Soil Analysis**: Detailed soil health reports
- **Government Schemes**: Information about subsidies and programs
- **Analytics**: Data-driven farming insights

## 🛠 Tech Stack

### Frontend Framework

- **React 18** - Modern React with hooks and functional components
- **Create React App** - Development environment and build tools

### UI/UX Libraries

- **Framer Motion** - Smooth animations and transitions
- **Heroicons** - Beautiful SVG icons
- **Lucide React** - Additional icon set
- **React Markdown** - Markdown rendering for bot responses

### API Integration

- **Fetch API** - For backend communication
- **Sarvam AI API** - Translation and text-to-speech services
- **Server-Sent Events** - Real-time streaming responses

### Styling

- **CSS3** - Custom CSS with CSS variables
- **Flexbox & Grid** - Modern layout techniques
- **CSS Animations** - Smooth user interactions

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v16.0 or higher)
- **npm** (v8.0 or higher) or **yarn**
- **Git** for version control

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/HimanshuMohanty-Git24/Agri-Sarthi.git
   cd agri-sarthi/frontend
   ```

2. **Install dependencies**

   ```bash
   npm install
   # or
   yarn install
   ```

3. **Set up environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` file with your API keys and configuration.

4. **Start the development server**

   ```bash
   npm start
   # or
   yarn start
   ```

5. **Open your browser**

   Navigate to `http://localhost:3000`

### Quick Start Commands

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run tests
npm test

# Build for production
npm run build

# Serve production build locally
npm run serve
```

## 📁 Project Structure

```text
frontend/
├── public/
│   ├── favicon.ico
│   ├── index.html
│   ├── logo.png
│   ├── manifest.json
│   └── robots.txt
├── src/
│   ├── components/
│   │   ├── Chat.js              # Main chat interface
│   │   ├── Chat.css
│   │   ├── Header.js            # Navigation header
│   │   ├── Header.css
│   │   ├── Footer.js            # Site footer
│   │   ├── Footer.css
│   │   ├── HomePage.js          # Landing page
│   │   ├── HomePage.css
│   │   ├── MessageActions.js    # Message interaction buttons
│   │   └── MessageActions.css
│   ├── services/
│   │   └── sarvamService.js     # Sarvam AI integration
│   ├── App.js                   # Main application component
│   ├── App.css                  # Global styles
│   ├── index.js                 # Application entry point
│   └── index.css                # Base styles
├── .env                         # Environment variables
├── package.json                 # Dependencies and scripts
└── README.md                    # This file
```

## 🔐 Environment Variables

Create a `.env` file in the frontend directory:

```env
# Sarvam AI API Configuration
REACT_APP_SARVAM_API_KEY=your_sarvam_api_key_here

# Backend API Configuration
REACT_APP_BACKEND_URL=http://localhost:8000

# Optional: Enable development features
REACT_APP_DEBUG_MODE=false
```

### Environment Variables Explained

| Variable | Description | Required |
|----------|-------------|----------|
| `REACT_APP_SARVAM_API_KEY` | API key for Sarvam AI translation and TTS | Yes |
| `REACT_APP_BACKEND_URL` | Backend API base URL | Yes |
| `REACT_APP_DEBUG_MODE` | Enable debug logging | No |

## 📜 Available Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Runs the app in development mode |
| `npm test` | Launches the test runner |
| `npm run build` | Builds the app for production |
| `npm run eject` | Ejects from Create React App (irreversible) |

## 🔌 API Integration

### Backend Communication

- **Base URL**: `http://localhost:8000`
- **Chat Endpoint**: `POST /chat`
- **Health Check**: `GET /test`

### Sarvam AI Integration

- **Translation API**: Text translation across 22+ Indian languages
- **Text-to-Speech**: Audio generation in multiple languages
- **Language Detection**: Automatic source language detection

### Request/Response Format

**Chat Request:**

```json
{
  "message": "What crops are suitable for Punjab?",
  "thread_id": "uuid-v4-string"
}
```

**Streaming Response:**

```text
data: {"content": "Based on Punjab's climate..."}
data: {"content": " wheat and rice are..."}
data: {"content": " excellent choices."}
```

## 🧩 Components

### Core Components

#### `Chat.js`

- Main chat interface with real-time messaging
- Streaming response handling
- Quick question suggestions
- Connection status monitoring

#### `HomePage.js`

- Landing page with feature highlights
- Call-to-action sections
- Statistics display
- Responsive hero section

#### `MessageActions.js`

- Copy to clipboard functionality
- Multi-language translation
- Text-to-speech playback
- Message interaction controls

#### `Header.js`

- Site navigation
- Logo and branding
- Responsive menu

#### `Footer.js`

- Site information
- Contact details
- Quick links

### Services

#### `sarvamService.js`

- Sarvam AI API integration
- Translation functionality
- Text-to-speech generation
- Audio playback utilities

## 🎨 Styling

### Design System

**Color Palette:**

- Primary Green: `#2E7D32`
- Secondary Green: `#4CAF50`
- Light Green: `#E8F5E8`
- Accent Green: `#66BB6A`
- Dark Green: `#1B5E20`

**Typography:**

- Font Family: Inter (Google Fonts)
- Weights: 400, 500, 600, 700, 800

**Spacing:**

- Base unit: 0.5rem (8px)
- Common values: 1rem, 1.5rem, 2rem

### CSS Architecture

- CSS Custom Properties for theming
- BEM-like naming convention
- Component-scoped styles
- Responsive design with mobile-first approach

## 🌍 Browser Support

- **Chrome** 90+
- **Firefox** 88+
- **Safari** 14+
- **Edge** 90+
- **Mobile browsers** (iOS Safari, Chrome Mobile)

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**

   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Commit your changes**

   ```bash
   git commit -m 'Add amazing feature'
   ```

4. **Push to the branch**

   ```bash
   git push origin feature/amazing-feature
5. **Open a Pull Request**

### Development Guidelines

- Follow React best practices
- Use functional components with hooks
- Maintain consistent code formatting
- Write meaningful commit messages
- Add comments for complex logic
- Test on multiple browsers

### Code Style

- Use meaningful variable and function names
- Keep components focused and reusable
- Follow the existing file structure
- Use CSS custom properties for theming
- Implement responsive design patterns

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Sarvam AI** for multilingual support
- **React Community** for excellent documentation
- **Indian Farmers** for inspiring this project
- **Open Source Contributors** for their valuable contributions

---

**Made with ❤️ for Indian Farmers** 🇮🇳

## Empowering agriculture through technology