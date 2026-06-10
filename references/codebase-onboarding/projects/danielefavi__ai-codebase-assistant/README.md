AI Codebase Assistant: Chat with Your Code
==========================================

This project provides an API that lets you interact with your codebase through an **AI assistant**. By using a **RAG (Retrieval-Augmented Generation)** system, this tool allows you to ask questions about your code in plain English and receive intelligent, context-aware answers.

It's an **AI agent** designed to help you quickly understand complex code, navigate legacy systems, or find specific implementations without manually digging through files. The system is built with **Node.js**, **TypeScript**, and **LangChain.JS**, and it uses **local Ollama** models to ensure your code remains **private**.

# Overview

This API server gives an **AI agent** knowledge about your specific codebase. You can then query the agent to get insights and explanations about your code's functionality.

The process begins with the AI agent scanning your codebase. Here’s a simple breakdown of how it works:

1. **Scanning & Indexing**: The agent reads all the files in your project. It intelligently detects new and modified files, so subsequent scans are much faster. For each file, it creates a list of tasks, such as breaking the code into smaller, logical chunks.
2. **Summarization & Storage**: The AI summarizes each code chunk and stores these summaries, along with the original code, in a local vector database. This creates a searchable knowledge graph of your entire codebase.
3. **Querying**: Once the scanning is complete, you can ask the AI assistant technical questions via the API. The RAG system retrieves the most relevant code snippets and summaries from the vector store and uses them as context to provide you with an accurate and detailed answer.

# Quickstart

Follow these steps to set up and run the AI Codebase Assistant on your local machine.

## 1. Prerequisites

- **Ollama**: For running the local language models.
- **Docker**: For running supporting services like the vector store and MySQL database.
- **Node.js**: Version 22 or higher.

## 2. Clone the Repo

Clone the repository and CD into the project folder with the following commands:

```sh
git clone https://github.com/danielefavi/ai-codebase-assistant.git
cd ai-codebase-assistant
```

## 2. Environment Setup

First, configure your environment variables.

1. Copy the example environment file:

```sh
cp .env.example .env
```

2. Open the new `.env` file and customize the settings, such as the LLM and embedding models you intend to use.

> **IMPORTANT**: You must have already installed the models you specify in your .env file within your Ollama instance.

## 3. Launch the Application

1. **Start Ollama**: Make sure the Ollama application is running.

2. **Start Docker Services**: Navigate to the docker directory and launch the containers for the database and other services.

```sh
cd docker
docker compose up
```

3. Start the API Server: Return to the project's root directory, install dependencies, and start the server.

```sh
npm i
npm run dev
```

If successful, you will see the message: `Server is running on http://localhost:5000`

## 4. Scan Your Codebase

To enable the AI to understand your code, you need to scan it first.

1. **Add Your Code**: Place the codebase you want to analyze into the `source-code` directory.

2. **Run the Scanner**: Execute the following command to start the scanning and indexing process:

```sh
npm run load-docs
```

> **Note on Scan Time**: The initial scan can be time-consuming, depending on the size of your codebase and your machine's performance.
> **You can terminate and resume the process** at any time by running `npm run load-docs` again.


## 5. Talk to Your Code

Once the scanning process is complete, you can start asking the AI assistant questions about your code.

Make a `POST` request to the `/api/agent/rag` endpoint with your query. Here is an example using cURL (you can import it in POSTMAN):

```sh
curl --location 'http://localhost:5000/api/agent/rag' \
--header 'Content-Type: application/json' \
--data '{
    "query": "What does the application do?"
}'
```

You are now ready to interact with your AI Codebase Assistant!

# API Endpoints Guide

This API provides endpoints for interacting with the AI agent, managing the codebase scanning process, and checking system status.

## Agent & LLM Interaction

These endpoints are for communicating with the AI agent and the underlying Large Language Model (LLM).

### Ask the AI About Your Code (RAG)

Ask a question about the scanned codebase. This is the primary endpoint for interacting with your codebase-aware AI agent. The AI will use the indexed information (Retrieval-Augmented Generation) to provide a context-aware answer.  
You must scan your codebase before using this.

- **Endpoint**: `POST` `/api/agent/rag`
- **Example**:

```sh
curl --location 'http://localhost:5000/api/agent/rag' \
--header 'Content-Type: application/json' \
--data '{
    "query": "How is user authentication handled in this project?"
}'
```

### Ask a General Question (No RAG)

Make a direct query to the LLM without using the codebase information (the vector store is not involved). The response is returned after the LLM has finished generating the full answer.

- **Endpoint**: `POST` `/api/agent/ask`
- **Example**:

```sh
curl --location 'http://localhost:5000/api/agent/ask' \
--header 'Content-Type: application/json' \
--data '{
    "query": "Explain the concept of dependency injection."
}'
```

### Ask a General Question (Streaming)

Make a direct query to the LLM and receive the response as a real-time stream of tokens as they are generated. Useful for real-time applications

- **Endpoint**: POST /api/agent/ask-stream
- **Example**:

```sh
curl --location 'http://localhost:5000/api/agent/ask-stream' \
--header 'Content-Type: application/json' \
--data '{
    "query": "Write a short story about a sentient bug in a program."
}'
```

## Codebase & Data Operations

Use these endpoints to manage the scanning process and reset the system's data.

### Reset the System

Deletes all data from the vector store and the MySQL database. **You will lose all scanning progress and must run the scanner again from scratch**.

- **Endpoint**: `POST` `/api/operations/reset`
- **Example**:

```sh
curl --location --request POST 'http://localhost:5000/api/operations/reset'
```

### Run the Master Scanner

Initiates the "master" operation that scans the source-code directory. It identifies new or changed files and queues up tasks (chunking, summarizing) to be processed.  
This is the first step in the scanning process and is run automatically by the `npm run load-docs` script.

- **Endpoint**: POST /api/operations/run-master
- **Example**:

```sh
curl --location --request POST 'http://localhost:5000/api/operations/run-master'
```

### Run a Queued Operation

Executes a single, random operation from the task queue (e.g., chunking one file, summarizing one chunk).  
This endpoint processes one task from the queue created by the master scanner. The `npm run load-docs` script calls this repeatedly under the hood.

- **Endpoint**: `POST` `/api/operations/run-rand`
- **Example**:

```sh
curl --location --request POST 'http://localhost:5000/api/operations/run-rand'
```

## System & Tool Endpoints

These endpoints provide utilities for inspecting the system's state and configuration.

### List Available Ollama Models

Returns a list of all LLM and embedding models currently installed in your Ollama instance.

- **Endpoint**: `GET` `/api/tools/ollama/models`
- **Example**:

```sh
curl --location 'http://localhost:5000/api/tools/ollama/models'
```

### View Latest Vector Store Entries

Fetches the 50 most recent entries that have been added to the local vector store.

- **Endpoint**: `GET` `/api/tools/vector-store/get-latest-entries`
- **Example**:

```sh
curl --location 'http://localhost:5000/api/tools/vector-store/get-latest-entries'
```

## Test Endpoint

A simple endpoint for quick connectivity tests.

- **Endpoint**: `GET` `/api/test`
- **Example**:

```sh
curl --location 'http://localhost:5000/api/test'
```
