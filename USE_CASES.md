# Smart Document Context Handler — Real-World Use Cases

> How the 4-tier pipeline maps to production AI workflows across email deliverability, customer support, compliance, and data analysis platforms.

---

## 1. Deliverability Log Analysis

### The Problem
Platforms that monitor hundreds or thousands of inboxes generate daily logs per client — reply rates, bounce rates, spam placement data, warm-up metrics. When a user asks their AI support bot *"Why did my domain get flagged last Tuesday?"*, the system needs to search through potentially hundreds of MBs of log files to find the answer. A naive approach dumps everything into the prompt and immediately blows the context window.

### How the System Handles It

```
inbox_logs_2025_01.csv (800KB)
        │
        ▼
DocumentLoader (CSV → pandas → readable text)
        │
        ▼
TokenEstimator: ~200,000 tokens → Tier 4 (RAG Retrieval)
        │
        ▼
ChunkingEngine: splits into ~512-token log segments
        │
        ▼
RAGPipeline: embeds all segments into FAISS index
        │
        ▼
Query: "Why did domain X get flagged on Tuesday?"
        │
        ▼
FAISS retrieves: only Tuesday segments for that domain (~5K tokens)
        │
        ▼
ContextAssembler: 5–10 relevant chunks sent to LLM
```

**Result:** The LLM receives exactly the relevant time window and domain — not 800KB of noise. Accurate, targeted answers instead of context overflow errors.

**Key advantage:** The FAISS index is built once per log file and cached in Redis. Every subsequent query on the same log file hits the cache — no re-embedding, sub-second retrieval.

---

## 2. Customer Support / Knowledge Base Querying

### The Problem
AI-powered support bots need access to FAQs, onboarding guides, setup documentation, API references, and troubleshooting articles. These docs collectively can reach 200KB–500KB+. Feeding the entire knowledge base into every single prompt is prohibitively expensive and often impossible.

### How the System Handles It

```
knowledge_base/ (500KB combined)
        │
        ▼
DocumentLoader (Markdown/PDF → raw text with section headers)
        │
        ▼
TokenEstimator: ~125,000 tokens → Tier 4 (RAG Retrieval)
        │
        ▼
ChunkingEngine: section-aware splitting (detects ## headers as boundaries)
        │
        ▼
RAGPipeline: FAISS index built once, cached in Redis
        │
        ▼
Customer query: "How do I connect my sequencer account?"
        │
        ▼
Vector search → top 3 chunks (integration setup section) retrieved
        │
        ▼
LLM answers from ~1,500 tokens instead of 125,000
```

**Result:** Precise, source-grounded answers. LLM costs drop dramatically. Response quality improves because the model isn't distracted by irrelevant documentation.

---

## 3. Multi-Client Report Generation

### The Problem
Platforms generate periodic reports for each client — inbox health scores, deliverability trends, recommendations. Each client's data export is a different size (some are 20KB CSVs, some are 180KB PDFs). When using an LLM to auto-generate summaries, the system must ensure the report data + system instructions + conversation history all fit within the context window without silently truncating important data.

### How the System Handles It

The Tier Classifier automatically routes each client's report to the right strategy:

| Client | Export Size | Tier | Strategy |
|--------|-------------|------|----------|
| Client A | 28KB PDF | T1 | Full document injected directly |
| Client B | 75KB CSV | T2 | Strip redundant headers/footers, compress whitespace |
| Client C | 160KB PDF | T3 | Chunk by section, rank by relevance, fill token budget |
| Client D | 400KB PDF | T4 | Embed into FAISS, retrieve only relevant sections |

The **Token Budget Allocator** guarantees safe allocation for every report:

```
System prompt (LLM instructions):  2,000 tokens  (fixed)
Report data (dynamic):          up to 184,000 tokens
Conversation history:              10,000 tokens  (fixed)
Response buffer:                    4,000 tokens  (fixed)
─────────────────────────────────────────────────────────
Total:                            200,000 tokens
```

**Result:** No report data is silently dropped. If a report overflows the budget, it is chunked and ranked — the most important sections are always included.

---

## 4. Email Content Analysis at Scale

### The Problem
Teams running large-scale cold email campaigns send thousands of copy variants across multiple domains. Analysing which email patterns correlate with spam placement requires feeding large CSV datasets — templates + performance metrics — into an LLM. A single campaign export can be 100KB–300KB.

### How the System Handles It

```
campaign_analysis.csv (120KB)
        │
        ▼
DocumentLoader: pandas reads CSV, converts to readable tabular text
        │
        ▼
TokenEstimator: ~30,000 tokens → Tier 3 (Strategic Chunking)
        │
        ▼
ChunkingEngine: groups rows into campaign-sized chunks (~512 tokens each)
        │
        ▼
BM25 ranking: query "which subject lines correlated with spam placement?"
        │
        ▼
Top chunks (highest-signal campaigns) selected, fill token budget greedily
        │
        ▼
Tier 2 boilerplate trimmer: strips repeated column headers between chunks
        │
        ▼
LLM analyses only the relevant campaign segments
```

**Result:** Pattern analysis across thousands of email variants without context overflow. BM25 keyword ranking surfaces the most signal-rich data segments for any given analytical question.

---

## 5. Onboarding Document Processing

### The Problem
New clients submit existing configurations, DNS records, sequencer settings, and domain lists — often as a mix of PDFs, CSVs, and DOCX files of completely unpredictable sizes. Processing these through an LLM for automated setup recommendations requires handling multiple file types in a single workflow.

### How the System Handles It

All formats are normalised to the same internal structure before any processing:

```
client_setup.pdf    → PyMuPDF      → text + [Page N] markers
dns_records.csv     → pandas       → tabular → readable string
sequencer.docx      → python-docx  → paragraphs + table rows extracted
domain_list.txt     → UTF-8 decode → raw text

         All produce: LoadedDocument(filename, file_size, raw_text, mime_type)
                │
                ▼
         Same pipeline from here — TokenEstimator → TierClassifier → ...
```

The rest of the pipeline is completely format-agnostic. Each file is independently classified and assembled — a 10KB DNS CSV hits Tier 1 while a 200KB onboarding PDF hits Tier 4, and each gets the right treatment automatically.

**Result:** A single API endpoint handles any file type, any size. No custom handling per format required from the calling application.

---

## 6. Compliance & Audit Trail Queries

### The Problem
Email deliverability involves regulatory compliance (CAN-SPAM, GDPR, CASL). Platforms store policy documents, data processing agreements, and audit event logs. When a compliance question arises — from a client, a legal team, or an automated audit — querying across large legal documents and log histories with a naive prompt approach is impractical.

### How the System Handles It

**Policy documents:**
```
gdpr_compliance_policy.pdf (250KB) → Tier 4
        │
        ▼
Embedded into FAISS (built once, cached in Redis)
        │
        ▼
Query: "What is our data retention obligation under Article 17?"
        │
        ▼
Retrieves: Article 17 chunk + adjacent context (~2K tokens)
        │
        ▼
LLM answers with exact policy language, not hallucinated summaries
```

**Audit logs:**
```
audit_events_2025_q1.csv (1MB+) → Tier 4
        │
        ▼
ChunkingEngine: splits by time window (e.g. weekly batches)
        │
        ▼
Query: "All unsubscribe events for client X in January 2025"
        │
        ▼
Vector search retrieves only January chunks for that client
        │
        ▼
LLM returns structured summary from ~3K tokens of relevant data
```

**Result:** Compliance queries are answered from source documents, not model memory. Audit trails can be searched semantically, not just by exact string match.

---

## Summary

All six scenarios flow through the same pipeline — the tier is selected automatically based on document size:

| Use Case | Typical Tier | Key Module |
|----------|-------------|------------|
| Deliverability log analysis | T4 | RAGPipeline + FAISS |
| Knowledge base querying | T4 | RAGPipeline + Redis cache |
| Per-client report generation | T1–T3 (varies) | TierClassifier + BudgetAllocator |
| Email copy analysis | T3 | ChunkingEngine + BM25 |
| Onboarding doc processing | T1–T4 (varies) | DocumentLoader (multi-format) |
| Compliance & audit queries | T4 | RAGPipeline + FAISS |

The calling application never manages token counts, chunking, or embedding logic — it uploads a file and asks a question. The system handles everything in between.
