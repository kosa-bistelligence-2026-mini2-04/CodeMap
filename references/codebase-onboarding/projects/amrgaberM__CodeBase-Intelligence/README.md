# CodeLens 🔍

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://your-app.streamlit.app)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AI-powered codebase intelligence. Ask questions about any GitHub repo in plain English.**

![CodeLens Demo](demo.gif)
---

## What is CodeLens?

Point CodeLens at any GitHub repository and instantly:
- 💬 **Ask questions** in natural language
- 🔍 **Search code** semantically (not just keywords)
- 📖 **Explain functions** with full context
- 🔗 **Understand dependencies** between files

---

## Quick Demo

```bash
# 1. Clone & install
git clone [repo link]
cd codelens && pip install -r requirements.txt

# 2. Add your Groq API key
echo "GROQ_API_KEY=your_key" > .env

# 3. Run
streamlit run streamlit_app.py
```

---

## Performance

| Metric | Value |
|--------|-------|
| Retrieval Latency | **38ms** |
| Answer Generation | **1.9s** |
| Retrieval Accuracy | **85%** |
| Chunks Supported | **2,000+** |

> Tested on [tiangolo/typer](https://github.com/tiangolo/typer) (605 files, 2,117 chunks)

---

## How It Works

```
GitHub Repo → AST Parser → Chunker → Embeddings → Vector DB
                                                      ↓
    User Question → Hybrid Search (Dense + BM25) → Reranker → LLM → Answer
```

**Key techniques:**
- **Hybrid retrieval**: 70% semantic + 30% keyword search
- **AST-based chunking**: Preserves function/class boundaries
- **Dependency expansion**: Adds related files automatically
- **Reciprocal Rank Fusion**: Combines multiple search strategies

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Groq (Llama 3.3 70B) |
| Embeddings | MiniLM-L6-v2 (384 dim) |
| Vector Store | ChromaDB |
| Sparse Search | BM25 |
| Backend | FastAPI |
| Frontend | Streamlit |

---

## Features

### 💬 Natural Language Q&A
Ask anything about the codebase:
- *"How does authentication work?"*
- *"What does the process_data function do?"*
- *"Where is error handling implemented?"*

### 🔍 Hybrid Search
Combines semantic understanding with keyword matching for best results.

### 📊 Code Intelligence
- **Explain Function**: Detailed breakdown of any function
- **Find Similar**: Discover similar code patterns
- **Usage Analysis**: Track where symbols are used
- **Auto-Documentation**: Generate docs for any file

---

## Installation

### Prerequisites
- Python 3.10+
- [Groq API Key](https://console.groq.com) (free)

### Setup
```bash
# Clone
git clone https://github.com/amr-khalil/codelens.git
cd codelens

# Install
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
echo "GROQ_API_KEY=your_key" > .env

# Run
streamlit run streamlit_app.py
```

---

## Usage

### Web UI
```bash
streamlit run streamlit_app.py
```

### CLI
```bash
python cli.py ingest https://github.com/tiangolo/typer
python cli.py query "How do I create a CLI command?"
python cli.py chat  # Interactive mode
```

### API
```bash
uvicorn src.api.main:app --reload

# Index
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/tiangolo/typer"}'

# Query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How does argument parsing work?"}'
```

---

## Architecture

```
codelens/
├── src/
│   ├── api/            # FastAPI REST API
│   ├── ingestion/      # GitHub loader, AST parser
│   ├── chunking/       # AST & semantic chunkers
│   ├── embeddings/     # Embedding model
│   ├── retrieval/      # Vector store, BM25, hybrid search
│   ├── generation/     # LLM integration, prompts
│   └── utils/          # Config, logging, dependency graph
├── streamlit_app.py    # Web UI
├── cli.py              # CLI interface
└── api.py              # Standalone API
```

---

## Roadmap

- [x] Hybrid retrieval (dense + sparse)
- [x] AST-based chunking
- [x] Dependency graph expansion
- [ ] Multi-language AST (tree-sitter)
- [ ] Streaming responses
- [ ] Redis caching
- [ ] Evaluation metrics (RAGAS)

---

## Contributing

```bash
# Setup
pip install pytest black isort

# Test
pytest tests/ -v

# Format
black src/ && isort src/
```

---

## License

MIT © 2025 Amr

---

## Acknowledgments

Built with [Groq](https://groq.com), [ChromaDB](https://trychroma.com), [HuggingFace](https://huggingface.co), [Streamlit](https://streamlit.io)
