# GitFlow-AI - GitHub Repository Analyzer

## Project Overview

GitFlow-AI is a web application that analyzes GitHub repositories using Google Gemini 2.0 Flash API. The interface resembles ChatGPT with a clean, conversational design, allowing users to gain insights about any public GitHub repository.

## Features

- **Repository Analysis**: Analyze public GitHub repositories for code quality, structure, and patterns
- **AI-Powered Insights**: Get intelligent analysis using Google Gemini 2.0 Flash API
- **Interactive Q&A**: Ask follow-up questions about the repository in a chat-like interface
- **Modern UI**: Clean, responsive design with dark/light theme support

## Tech Stack

- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **UI Components**: shadcn UI for consistent design
- **State Management**: Zustand for global state
- **API Integration**: GitHub API and Google Gemini API
- **Styling**: Tailwind CSS with responsive design

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Google Gemini API key

### Installation

1. Clone the repository
2. Install dependencies:

```bash
npm install
```

3. Create a `.env.local` file in the root directory with the following variables:

```
# Google Gemini API Key (required for AI analysis)
GEMINI_API_KEY=your_gemini_api_key

# Application URL (optional, for deployment)
NEXT_PUBLIC_APP_URL=your_app_url
```

4. Start the development server:

```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage

1. Enter a public GitHub repository URL in the input field
2. Click "Analyze" to start the analysis process
3. Wait for the analysis to complete
4. View the AI-generated summary and insights
5. Ask follow-up questions in the chat interface

## API Endpoints

- `/api/validate-repo` - Validates GitHub repository URLs
- `/api/analyze-repo` - Analyzes repositories using GitHub API and Gemini AI
- `/api/chat` - Handles follow-up questions in the context of the analyzed repository

## Deployment

This application can be easily deployed to Vercel:

```bash
npm run build
```

Then deploy using the Vercel CLI or GitHub integration.

## License

MIT
