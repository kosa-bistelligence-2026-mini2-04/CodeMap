# CodeMap AI — Codebase Onboarding Agent

CodeMap AI is a web service designed to automate repository onboarding, analysis, and interactive documentation generation. It incorporates design philosophies and components benchmarked from leading open-source repositories.

## Benchmarked Architectural Pillars

1. **Next.js 15+ & TailwindCSS v4 Framework**: Adopted from `403errors/repomind` as the scalable front-end baseline.
2. **Three.js Interactive ASCII Hero Scene**: Adopted from `chroma-core/github-sync-demo` to build a sleek, minimalist interactive 3D landing environment.
3. **Structured Repository Analysis UI**: Adopted from `CronusL-1141/repo-insight` (migrated to standard English), featuring:
   - Local directory absolute path and public GitHub URL validation.
   - Live LLM model provider dropdown lists.
   - Interactive SVG-based hotspot risk locator (zero-dependency mapping).
   - Multi-agent state orchestration telemetry tracking.
   - Real-time agent status mapping with manual retry logic.

---

## Project Structure

```
codemap-ai/
├── frontend/          # Next.js 15 + TypeScript + TailwindCSS v4
│   ├── src/
│   │   ├── app/       # App router pages (Home, Dashboard)
│   │   ├── components/# Modular Tailwind v4 widgets
│   │   ├── hooks/     # Native WebSocket lifecycle manager
│   │   └── lib/       # Lightweight HTML sanitizer & API clients
│   └── next.config.ts # API Proxy routing rules
│
└── backend/           # FastAPI Python Mock Scaffolding
    ├── app/
    │   ├── main.py    # CORS middleware & WebSocket routes
    │   ├── api/       # Simulation engines & mock routers
    │   └── models/    # Pydantic contract validators
    └── pyproject.toml # Dependencies manager
```

---

## Local Development Execution

### Prerequisites
- Node.js >= 20
- Python >= 3.10

### 1. Run Backend Service
Go to the `backend/` directory, setup a virtual environment, install dependencies, and run:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Run Frontend Web App
Go to the `frontend/` directory, install packages, and start Next.js:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

## Quick Testing / Demonstration Guide

1. Open [http://localhost:3000](http://localhost:3000). You will see the beautiful interactive 3D ASCII shapes floating in the background. Feel free to drag them around!
2. Type any GitHub URL or select the suggestions underneath the input bar.
3. You will be redirected to the `/analyze` dashboard where the multi-agent execution pipeline (Static Analysis, Behavior Inference, etc.) will start running in real-time.
4. Once completed, a comprehensive report featuring a risk mapping heatmap, AI executive summaries, multi-agent conflicts resolved by LLM Judge, and guardrail telemetry metrics will be populated instantly.
