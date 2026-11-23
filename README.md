# ShopMind AI — Intelligent RAG-Based Shopping Assistant with Evaluation and AI Security

**ShopMind AI** is a production-grade, full-stack Retrieval-Augmented Generation (RAG) shopping platform featuring hybrid semantic + keyword retrieval, cross-feature reranking, LangGraph agentic shopping tools, Groq LLM integration, a 106-question ground-truth RAG evaluation suite, and an OWASP Top 10 for LLM Applications security layer.

---

## 1. Key Capabilities

- **12-Stage Grounded Hybrid RAG Pipeline**:
  - Multi-source product ingestion from **CSV**, **JSON**, and **Manual Admin Entry** with schema normalization, duplicate detection, and indirect prompt injection sanitization.
  - Local Hugging Face `sentence-transformers/all-MiniLM-L6-v2` (384-D) embeddings indexed in **FAISS** combined with **Okapi BM25** keyword search via **Reciprocal Rank Fusion (RRF)**.
  - Hard metadata filtering (budget, category, brand, rating) and domain specification satisfaction reranking.
  - Zero-hallucination output verification ensuring every cited Product ID (`PROD-XXX-NNN`) and price (`₹`) matches retrieved catalog evidence.
- **LangGraph Agentic Shopping Assistant & 8 Domain Tools**:
  - `search_products()`, `compare_products()`, `filter_by_budget()`, `get_product_details()`, `recommend_products()`, `find_similar_products()`, `retrieve_product_reviews()`, and `explain_recommendation()`.
  - Multi-turn conversational memory that preserves active constraints (e.g. *"I need a laptop under ₹75,000"* -> *"It should have 16GB RAM"* -> *"Compare the top two"*).
- **Mandatory 106-Question RAG Evaluation Framework**:
  - Measures **Precision@K**, **Recall@K**, **Mean Reciprocal Rank (MRR)**, **Hit Rate@K**, **NDCG@K**, **Faithfulness**, **Answer Relevancy**, **Context Precision**, **Context Recall**, **Response Correctness**, and **Hallucination Rate** across 10 benchmark categories.
  - All evaluation runs and question-level results are persisted in the database and downloadable as **CSV** and **JSON** reports.
- **OWASP Top 10 for LLM Applications Security Layer**:
  - Defends against Direct Prompt Injection, Indirect Prompt Injection in product descriptions, System Prompt/API Key extraction, Hallucinated Product IDs, SQL Injection, XSS, Tampered JWTs, Cross-User Conversation Access, Malicious File Uploads, and Request Bursts.
  - Includes a 10-vector automated security penetration scanner (`/api/security/test`).

---

## 2. Environment Variables

Copy `.env.example` to `.env` in the project root and configure:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
DATABASE_URL=postgresql+psycopg2://shopmind:shopmind_secret@localhost:5432/shopmind_db
SQLITE_FALLBACK_URL=sqlite:///./data/shopmind.db
USE_SQLITE_FALLBACK=true
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-this-to-a-64-char-cryptographic-secret-in-production-env
```

> **Note on Groq API Key & Local Embedding Model**:
> -Embeddings run 100% locally using `sentence-transformers/all-MiniLM-L6-v2` (with automatic `scikit-learn` L2 dense TF-IDF fallback if offline), requiring no external embedding API key.
> -When `GROQ_API_KEY` is configured, ShopMind AI invokes the live Groq SDK (`llama-3.3-70b-versatile`). When `GROQ_API_KEY` is omitted, the backend transparently uses its built-in **ShopMind Grounded RAG Deterministic Synthesizer** and displays a clear configuration notice in `/api/admin/system-health` and the UI without fabricating ungrounded responses.

---

## 3. Quick Start & Running the Application

### Option A: Local Development Setup

1. **Install Backend Dependencies & Generate Ground-Truth Datasets**:
   ```bash
   pip install -r backend/requirements.txt
   python backend/app/database/seed_generator.py
   ```

2. **Start the FastAPI Backend Server (Port 8000)**:
   ```bash
   # PowerShell (Windows)
   $env:PYTHONPATH="backend"
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   - Swagger / OpenAPI Documentation: `http://127.0.0.1:8000/docs`

3. **Install & Start the React TypeScript Frontend (Port 5173)**:
   ```bash
   cd frontend
   npm.cmd install
   npm.cmd run dev
   ```
   - Frontend UI: `http://localhost:5173`

### Option B: Docker Compose Production Deployment (PostgreSQL + Redis + Backend + Frontend)

```bash
docker compose up --build -d
```

### Pre-Seeded RBAC Demo Accounts

| Role | Email | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@shopmind.ai` | `Admin@ShopMind2026!` | Full access including dataset upload, manual product creation, vector re-indexing, and audit logs |
| **Demo Shopper** | `demo@shopmind.ai` | `Shopper@2026!` | Conversational RAG assistant, personal chat history, product explorer, and comparisons |

---

## 4. Running Automated Tests & Evaluation

```bash
# Run the complete pytest suite (Ingestion, Embeddings, Hybrid RAG, Agent Tools, RBAC, Security, Evaluation)
$env:PYTHONPATH="backend"
python -m pytest backend/tests/test_shopmind.py -v
```
