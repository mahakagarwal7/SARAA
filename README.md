# SARAA (Strategic Autonomous Research & Action Agent)

SARAA is a premium, next-generation **Strategic Autonomous Research & Action Agent Swarm** designed to act as a hyper-competent executive assistant. By combining multi-agent coordination, deep web intelligence extraction, real-time Microsoft Graph calendar integration, and multi-modal document analysis, SARAA handles complex tasks autonomously.

The application features a dark-themed, glassmorphic ChatGPT-style user interface built on a live-rendered 3D WebGL background, delivering a premium visual experience.

---

## 🌟 Key Features

1. **Autonomous Agent Swarm (AutoGen):**
   * Multi-agent communication framework featuring specialised agents (Orchestrator, Research, Calendar Sync, and Document Writer) collaborating to build plans, write scripts, and synthesize briefings.
2. **Microsoft Graph API Integration:**
   * Full, secure authentication via Microsoft Authentication Library (MSAL).
   * Live calendar synchronization to retrieve upcoming meeting schedules and automatically prepare custom strategic briefings based on attendee lists.
3. **Deep Web Research & Scraping:**
   * Autonomous web crawling agents that scrape pages, resolve conflicting sources, and synthesize raw data into coherent, detailed documents.
   * Leverages Tavily/Bing Search APIs.
4. **Multimodal & Document Parsing:**
   * Accepts high-volume `.pdf`, `.doc`, and `.docx` uploads alongside images.
   * Auto-extracts text directly into the agent context, with built-in token-truncation protection (30,000 character limit) to prevent context window crash.
5. **High-Fidelity PDF Export:**
   * Strips away UI wrappers (inputs, 3D particles, chat history) using native print-media styles (`@media print`) to compile clean, professional PDF reports directly from the browser print dialog.
6. **State-of-the-Art Visuals & Interaction:**
   * **Writing Logo Animation:** The "SARAA" logo writes itself in letter-by-letter with a custom-easing kinetic entry (slide, rotate, scale) and a soft white neon glow.
   * **Frosted Glassmorphism:** Clean white frosted container backgrounds, high-contrast typography (Outfit), and translucent glass widgets.
   * **Radial Magnetic Cursor Glow:** The search command bar features an interactive Vercel-style radial spotlight that dynamically follows mouse movement.
   * **Built-in Voice Dictation:** Hands-free interaction via integrated browser `SpeechRecognition`.

---

## 📂 Repository Layout

```
SARAA/
├── README.md                              # Main documentation (this file)
└── executive-assistant-swarm/
    ├── backend/                           # FastAPI Autogen Swarm server
    │   ├── api/                           # API endpoints & route handlers
    │   │   └── main.py                    # Main server entrypoint
    │   ├── agents/                        # Autonomous agent implementations
    │   │   ├── base_agent.py              # Base Agent & document parsing logic
    │   │   └── orchestrator_agent.py      # Swarm orchestration configuration
    │   ├── tools/                         # Custom tools (Scraping, Calendar, Search)
    │   ├── tests/                         # Backend pytest suite
    │   ├── requirements.txt               # Python package dependencies
    │   └── .env                           # Backend environment secrets
    └── frontend/                          # React + TypeScript SPA client
        ├── src/                           # Client source code
        │   ├── App.tsx                    # Main app components & MSAL authentication
        │   ├── App.css                    # UI styles, animations, & print rules
        │   ├── authConfig.ts              # MSAL Auth & Scope configuration
        │   └── services/                  # Stream handling & API services
        ├── package.json                   # NPM dependencies
        └── vite.config.ts                 # Vite setup & proxy rules
```

---

## 🛠️ Technology Stack

* **Frontend:** [React 19](./executive-assistant-swarm/frontend/package.json), [TypeScript](./executive-assistant-swarm/frontend/tsconfig.json), [Vite](./executive-assistant-swarm/frontend/vite.config.ts), [Fluent UI React Components](./executive-assistant-swarm/frontend/src/App.tsx), [Vanta.net / Three.js](./executive-assistant-swarm/frontend/src/App.css) (WebGL Background).
* **Backend:** [FastAPI](./executive-assistant-swarm/backend/api/main.py), [AutoGen](./executive-assistant-swarm/backend/requirements.txt) (Agentchat), [PyPDF / Python-docx](./executive-assistant-swarm/backend/agents/base_agent.py) (Doc parsing), Azure OpenAI (LLM), Microsoft Graph SDK (Office 365).

---

## ⚙️ Configuration & Environment Setup

### 1. Azure App Registration (Entra ID)
To enable Microsoft Graph Sync (Calendar and Mail), register a new Single Page Application (SPA) in the **Azure Portal (App Registrations)**:
* **Redirect URI:** `http://localhost:5173/` (or your local client origin).
* **API Permissions (Microsoft Graph):**
  * `User.Read` (Sign in / User Profile)
  * `Calendars.Read` & `Calendars.ReadWrite` (Fetch/Edit meetings)
  * `Mail.Send` (Email briefings)

### 2. Backend Environment Variables
Create a `.env` file inside the [backend](./executive-assistant-swarm/backend) directory:
```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://<your-resource>.services.ai.azure.com/
AZURE_OPENAI_API_KEY=<your-azure-key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Microsoft Graph API Configuration
CLIENT_ID=<your-azure-app-client-id>
CLIENT_SECRET=<your-azure-app-client-secret>
TENANT_ID=<your-azure-app-tenant-id>
REDIRECT_URI=http://localhost:8000/auth/callback

# Web Search Tools
TAVILY_API_KEY=<your-tavily-api-key>
BING_SEARCH_API_KEY=<your-optional-bing-api-key>
BING_SEARCH_ENDPOINT=https://api.bing.microsoft.com/v7.0/search

# Telemetry & Monitoring (Optional)
APPLICATIONINSIGHTS_CONNECTION_STRING=<your-appinsights-connection-string>
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 3. Frontend MSAL Config
Configure the [authConfig.ts](./executive-assistant-swarm/frontend/src/authConfig.ts) file with your Azure credentials:
```typescript
export const msalConfig: Configuration = {
  auth: {
    clientId: "<your-client-id>",
    authority: "https://login.microsoftonline.com/<your-tenant-id>",
    redirectUri: window.location.origin,
  }
};
```

---

## 🚀 Installation & Running Locally

### Prerequisites
* [Node.js](https://nodejs.org/) (v18+)
* [Python](https://www.python.org/) (v3.10+)

### Step 1: Start the Backend Server
1. Navigate to the backend directory:
   ```bash
   cd executive-assistant-swarm/backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI development server:
   ```bash
   python api/main.py
   ```
   The backend will be available at `http://localhost:8000`.

### Step 2: Start the Frontend Client
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd executive-assistant-swarm/frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```
   The frontend application will boot at `http://localhost:5173`. Open this URL in your browser to begin deploying the swarm!