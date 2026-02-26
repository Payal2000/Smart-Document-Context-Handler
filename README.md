# Smart Document Context Handler

> Intelligent 4-tier document processing system that automatically selects the optimal strategy to fit any document into an LLM's context window — no wasted tokens, no context overflow.



## The Problem

LLMs have a finite context window (~200K tokens). Naively stuffing an entire document wastes tokens on irrelevant content, causes context overflow on large files, and produces poor results when important content gets buried.

## The Solution

A tiered pipeline that analyses each document and picks the right strategy automatically:

| Tier | Token Range | Strategy | When Used |
|------|-------------|----------|-----------|
| **T1** — Direct Injection | ≤ 12,000 | Send the full document as-is | Small docs, always optimal |
| **T2** — Smart Trimming | 12K – 25K | Strip boilerplate, compress whitespace | Medium docs with redundant content |
| **T3** — Strategic Chunking | 25K – 50K | Sentence-aware splits + BM25 keyword ranking | Large docs, query-driven retrieval |
| **T4** — RAG Retrieval | > 50K | FAISS vector search (OpenAI or local embeddings) | Very large docs, semantic search |



## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Document Upload                       │
└──────────────────────────┬──────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Document   │  .txt .md .pdf .docx .csv .xlsx
                    │   Loader    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Token     │  tiktoken cl100k_base
                    │  Estimator  │  exact token count
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Tier     │  T1 / T2 / T3 / T4
                    │ Classifier  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐───────────────┐
           │               │               │               │
      ┌────▼────┐    ┌─────▼────┐   ┌─────▼────┐   ┌─────▼────┐
      │   T1    │    │    T2    │   │    T3    │   │    T4    │
      │  Full   │    │  Trim    │   │  Chunk   │   │   RAG    │
      │  Text   │    │ Boilerpl.│   │  + BM25  │   │  FAISS   │
      └────┬────┘    └─────┬────┘   └─────┬────┘   └─────┬────┘
           └───────────────┴───────────────┴───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Context Assembler       │
                    │  (greedy token budget fill)  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Assembled Prompt        │
                    │   ready to send to LLM       │
                    └─────────────────────────────┘
```

## Token Budget

The 200K context window is allocated as:

```
┌──────────────────────────────────────────────────────┐
│  Total Context Window: 200,000 tokens                │
├──────────────────────┬───────────────────────────────┤
│  System Prompt       │    2,000 tokens               │
│  Conversation Hist.  │   10,000 tokens               │
│  Response Buffer     │    4,000 tokens               │
│  Document Content    │  184,000 tokens (dynamic max) │
└──────────────────────┴───────────────────────────────┘
```

## Tech Stack

### Backend
| Component | Technology | Why |
|-----------|-----------|-----|
| API Framework | FastAPI | Async-native, auto OpenAPI docs, Pydantic v2 |
| Token Counting | tiktoken (cl100k_base) | OpenAI's exact tokenizer |
| PDF Parsing | PyMuPDF | 10× faster than PyPDF2, handles complex layouts |
| DOCX Parsing | python-docx | Native .docx support |
| Tabular Data | pandas | Handles malformed CSVs, multiple encodings |
| Sentence Splitting | NLTK punkt | Gold-standard sentence boundary detection |
| BM25 Ranking | rank-bm25 | Fast keyword relevance (T3) |
| Embeddings (primary) | OpenAI text-embedding-3-small | Best quality/cost ratio |
| Embeddings (fallback) | sentence-transformers all-MiniLM-L6-v2 | Free, offline, 384-dim |
| Vector Search | FAISS | Battle-tested, in-memory, no setup |
| Database | PostgreSQL + SQLAlchemy async | Document & chunk metadata |
| Cache | Redis | FAISS index caching, avoid re-embedding |
| Logging | Loguru | Structured, zero-config |

### Frontend
| Component | Technology |
|-----------|-----------|
| UI Framework | React 18 + TypeScript |
| Styling | Tailwind CSS |
| Charts | Recharts (token budget pie chart) |
| File Upload | react-dropzone |
| Animations | Framer Motion |
| Build Tool | Vite |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerisation | Docker + Docker Compose |
| Web Server | Nginx (frontend) |
| CI-ready | GitHub Actions compatible |



## Project Structure

```
Smart Document Context Handler/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── document_loader.py     # File parsing (.txt .md .pdf .docx .csv)
│   │   │   ├── token_estimator.py     # Exact token counting via tiktoken
│   │   │   ├── tier_classifier.py     # T1–T4 routing logic
│   │   │   ├── budget_allocator.py    # 200K window allocation
│   │   │   ├── chunking_engine.py     # Sentence-aware splitting + boilerplate trim
│   │   │   ├── rag_pipeline.py        # FAISS + embeddings + BM25
│   │   │   └── context_assembler.py   # Tier dispatch → assembled prompt
│   │   ├── api/routes/
│   │   │   ├── documents.py           # POST /upload  GET /{id}  GET /
│   │   │   └── query.py               # POST /query/
│   │   ├── db/
│   │   │   ├── database.py            # Async SQLAlchemy engine + session
│   │   │   └── models.py              # Document + DocumentChunk ORM models
│   │   ├── models/
│   │   │   └── document.py            # Pydantic request/response schemas
│   │   ├── config.py                  # Settings from env vars
│   │   └── main.py                    # FastAPI app entry point
│   ├── tests/                         # pytest test suite
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── FileUpload.tsx          # Drag-and-drop upload
│       │   ├── TierBadge.tsx           # T1/T2/T3/T4 coloured badge
│       │   ├── TokenBudgetChart.tsx    # Recharts donut chart
│       │   ├── ChunkViewer.tsx         # Retrieved chunks + context preview
│       │   └── QueryInterface.tsx      # Query input + results
│       ├── api/client.ts               # Axios API calls
│       └── types/index.ts              # TypeScript types
├── docker-compose.yml
├── .env.example
└── README.md
```



## Quick Start

### Option A — Docker Compose (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/Payal2000/Smart-Document-Context-Handler.git
cd Smart-Document-Context-Handler

# 2. Configure environment
cp .env.example .env
# Optional: add your OpenAI key for better embeddings
# OPENAI_API_KEY=sk-...

# 3. Start everything
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |



### Option B — Local Development

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Postgres + Redis (only, not the full stack)
docker-compose up postgres redis -d

# Configure
cp ../.env.example .env
# Edit .env with your database URL etc.

# Run API
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```



## API Reference

### Upload a Document
```http
POST /api/documents/upload
Content-Type: multipart/form-data

file: <binary>
```

**Response:**
```json
{
  "doc_id": "a3f2c1d0-...",
  "filename": "research_paper.pdf",
  "file_size": 142680,
  "token_count": 34200,
  "tier": {
    "tier": 3,
    "label": "Strategic Chunking",
    "color": "#f59e0b",
    "description": "Large document. Semantic chunking with BM25 relevance ranking."
  },
  "budget": {
    "total_window": 200000,
    "allocations": {
      "document_content": 34200,
      "system_prompt": 2000,
      "conversation_history": 10000,
      "response_buffer": 4000
    }
  }
}
```

### Query a Document
```http
POST /api/query/
Content-Type: application/json

{
  "doc_id": "a3f2c1d0-...",
  "query": "What are the main conclusions?",
  "top_k": 10
}
```

**Response:**
```json
{
  "doc_id": "a3f2c1d0-...",
  "tier": 3,
  "assembled_context": "...",
  "token_count": 18400,
  "chunks_used": [
    { "index": 4, "tokens": 498, "score": 0.8821 },
    { "index": 7, "tokens": 512, "score": 0.8134 }
  ],
  "strategy_notes": "Document split into 67 chunks. Top 10 selected via BM25 ranking."
}
```

### Other Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/documents/{id}` | Get document metadata |
| `GET` | `/api/documents/` | List recent documents |
| `GET` | `/api/health` | Health check |

---

## Running Tests

```bash
cd backend
pytest tests/ -v --tb=short

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```



## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | _(empty)_ | If set, uses OpenAI embeddings; otherwise sentence-transformers |
| `DATABASE_URL` | `postgresql+asyncpg://sdch:sdch_pass@localhost:5432/sdch` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for FAISS index caching |
| `UPLOAD_DIR` | `/tmp/sdch_uploads` | Where uploaded files are stored |
| `MAX_FILE_SIZE_MB` | `50` | Maximum upload size |
| `TIER1_MAX_TOKENS` | `12000` | T1 upper boundary |
| `TIER2_MAX_TOKENS` | `25000` | T2 upper boundary |
| `TIER3_MAX_TOKENS` | `50000` | T3 upper boundary |
| `CHUNK_TARGET_TOKENS` | `512` | Target tokens per chunk |
| `RAG_TOP_K` | `10` | Number of chunks to retrieve in T3/T4 |




