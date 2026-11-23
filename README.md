<div align="center">

# ShopMind AI — Enterprise RAG-Based Intelligent Shopping Assistant
### *Hybrid Dense-Sparse Retrieval • LangGraph Agentic Orchestration • 106-Query RAGAS/DeepEval Benchmark • OWASP LLM Top 10 Security Guardrails*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Groq LLM](https://img.shields.io/badge/Groq-Llama--3.3--70B-F55036?style=for-the-badge)](https://groq.com/)
[![FAISS + BM25](https://img.shields.io/badge/RAG-FAISS%20%2B%20BM25%20%2B%20RRF-8B5CF6?style=for-the-badge)](https://github.com/facebookresearch/faiss)
[![OWASP LLM Top 10](https://img.shields.io/badge/Security-OWASP%20LLM%20Top%2010-10B981?style=for-the-badge)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
[![Docker Compose](https://img.shields.io/badge/Docker-Production%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## Executive Summary

**ShopMind AI** is a production-grade, full-stack Retrieval-Augmented Generation (RAG) intelligent shopping assistant engineered to help users discover, filter, compare, and understand products across **11 diverse product verticals** (**59+ verified products** across Electronics, Footwear, Apparel, Home & Room Decor, and Kitchen Cookware).

Unlike basic wrapper chatbots that hallucinate prices or unverified specifications, **ShopMind AI** enforces a **12-stage grounded RAG and AI Security pipeline**:

1. **Zero-Hallucination Policy**: Every product recommendation, price (in `₹`), technical specification, rating, and availability claim is grounded strictly in retrieved knowledge base documents and verified against retrieved Product IDs (`PROD-XXX-NNN`) prior to response delivery.
2. **Measurable Quality Engineering**: Ships with a repeatable **106-question labeled ground-truth evaluation suite** measuring retrieval (**Precision@K**, **Recall@K**, **MRR**, **Hit Rate@K**, **NDCG@K**), generation (**Faithfulness**, **Answer Relevancy**, **Context Precision**, **Context Recall**, **Response Correctness**, **Hallucination Rate**), and latency/cost telemetry.
3. **Defense-in-Depth AI Security**: Implements **OWASP Top 10 for LLM Applications** protections against direct prompt injection, indirect prompt injection inside product descriptions, jailbreaks, system prompt extraction, SQL injection, XSS, tampered JWTs, and unauthorized tool invocation, backed by a **10-vector automated penetration scanner**.

---

## Table of Contents

1. [System Architecture & 12-Stage RAG Workflow](#1-system-architecture--12-stage-rag-workflow)
2. [Technology Stack & Engineering Decisions](#2-technology-stack--engineering-decisions)
3. [Multi-Category Product Knowledge Base (11 Verticals)](#3-multi-category-product-knowledge-base-11-verticals)
4. [Agentic Shopping Tools & Conversational State Memory](#4-agentic-shopping-tools--conversational-state-memory)
5. [Mandatory AI Evaluation Framework & Actual Measured Results](#5-mandatory-ai-evaluation-framework--actual-measured-results)
6. [AI Security Architecture & OWASP LLM Top 10 Audit Results](#6-ai-security-architecture--owasp-llm-top-10-audit-results)
7. [Full-Stack Application Pages (7 Interactive Modules)](#7-full-stack-application-pages-7-interactive-modules)
8. [REST API Reference](#8-rest-api-reference)
9. [Relational Database Schema (11 Tables)](#9-relational-database-schema-11-tables)
10. [Project Directory Structure](#10-project-directory-structure)
11. [Installation, Configuration & Running the Application](#11-installation-configuration--running-the-application)
12. [Testing, CI/CD & Production Deployment](#12-testing-cicd--production-deployment)
13. [Known Limitations & Future Roadmap](#13-known-limitations--future-roadmap)

---

## 1. System Architecture & 12-Stage RAG Workflow

```mermaid
flowchart TD
    Client["React 18 + TypeScript Frontend (7 Modules)"] -->|REST API + JWT Bearer| RateLimit["1. Sliding-Window Rate Limiter & CORS Gate"]
    RateLimit --> SecurityGate["2. OWASP LLM01 Input Guardrail (Direct Injection, SQLi, XSS, Tool Probe)"]
    SecurityGate -->|Blocked Attack| SecDB[("SecurityEvent Audit Table")]
    SecurityGate -->|Verified Safe| IntentEngine["3. Query Analyzer: Intent Classification & Constraint Extraction"]
    IntentEngine --> StateMemory["4. Multi-Turn Session Constraint Merger (Budget, Category, Brand, Specs)"]
    StateMemory --> QueryRewriter["5. Domain Query Expansion & Synonym Rewriting"]
    QueryRewriter --> DenseIndex["6a. Dense Semantic Search (FAISS IndexFlatIP + MiniLM-L6-v2 384D)"]
    QueryRewriter --> SparseIndex["6b. Sparse Keyword Search (Okapi BM25 Index)"]
    DenseIndex --> RRF["7. Reciprocal Rank Fusion (RRF) + Hard Metadata Filtering"]
    SparseIndex --> RRF
    RRF --> Reranker["8. Cross-Feature & Specification Satisfaction Reranker"]
    Reranker --> BoundaryWrap["9. Untrusted Document Boundary Tagging (<UNTRUSTED_PRODUCT_EVIDENCE>)"]
    BoundaryWrap --> LLMGen["10. Groq SDK LLM (llama-3.3-70b-versatile) / Deterministic Grounded Synthesizer"]
    LLMGen --> OutputGuard["11. Hallucination Verifier (Product ID Grounding + Secret Redaction)"]
    OutputGuard --> Response["12. Grounded Answer + Product Cards + Hybrid Citations + Confidence Score"]
```

---

## 2. Technology Stack & Engineering Decisions

| Layer | Technology | Engineering Rationale |
| :--- | :--- | :--- |
| **Frontend UI** | React 18, TypeScript 5.6, Vite 5, Tailwind CSS 3 | Type-safe component architecture, ultra-fast HMR, and a dark shopping-tech aesthetic (`#070B14` navy/charcoal with electric blue & violet accents). |
| **Data Visualization** | Recharts, Lucide React | Interactive bar and line charts for retrieval/generation evaluation metrics, category pass rates, and run-over-run historical comparisons. |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn | High-throughput REST endpoints with strict Pydantic schema validation and automatic Swagger/OpenAPI documentation (`/docs`). |
| **LLM Generation** | Groq Python SDK (`llama-3.3-70b-versatile`) | Ultra-low-latency inference for grounded recommendation synthesis, product comparisons, and natural-language explanations, fully configurable via `GROQ_MODEL`. |
| **Embeddings & Vector Store** | Hugging Face `sentence-transformers/all-MiniLM-L6-v2` (384-D) + **FAISS** | 100% local, zero-cost dense semantic embeddings paired with FAISS inner-product search and an automatic L2-normalized TF-IDF dense fallback for offline resilience. |
| **Hybrid Retrieval & Reranking** | Okapi BM25 + Reciprocal Rank Fusion (RRF) + Cross-Feature Reranker | Combines semantic understanding (e.g., *"laptop for deep learning"*) with exact lexical precision (e.g., *"RTX 4060"*, *"QMK/VIA"*, *"304 stainless steel"*). |
| **Agent Orchestration** | LangGraph `StateGraph` + 8 Scoped Tools | Enforces a deterministic, auditable state machine (`security_gate -> retrieve_and_tool_route -> generate_grounded_response -> verify_grounding`) rather than unrestricted autonomous loops. |
| **Relational Database** | PostgreSQL 16 + SQLAlchemy 2.0 ORM + Alembic (SQLite local fallback) | Enforces foreign keys, check constraints (`price >= 0`, `0 <= rating <= 5`), composite indexes, and logical separation between relational data and vector indices. |
| **Caching & Throttling** | Redis 7 + Sliding-Window Rate Limiter | Protects API and LLM endpoints against abusive burst traffic (`OWASP LLM10: Unbounded Consumption`). |
| **Quality & DevOps** | `pytest`, RAGAS/DeepEval Metrics, Docker Compose, GitHub Actions | Automated unit, integration, security, and evaluation tests executed on every commit. |

---

## 3. Multi-Category Product Knowledge Base (11 Verticals)

The knowledge base (`data/sample_products.csv`) ships with **59 curated, richly specified products** spanning **11 categories**:

| Category | ID Prefix | Count | Representative Indexed Products |
| :--- | :--- | :---: | :--- |
| **Laptops** | `PROD-LAP-*` | 10 | ASUS TUF Gaming A15 (RTX 4050), Lenovo LOQ 15, Acer Swift Go 14 OLED, Apple MacBook Air M3, MSI Cyborg 15 (RTX 4060), Lenovo ThinkPad E14 Gen 5 |
| **Smartphones** | `PROD-PHN-*` | 8 | Samsung Galaxy S24 5G, OnePlus 12 5G, Google Pixel 8a, OnePlus 12R, iQOO Neo 9 Pro, Apple iPhone 15, Nothing Phone (2a), Xiaomi 14 CIVI Leica |
| **Headphones & Audio** | `PROD-AUD-*` | 6 | Sony WH-1000XM5, Bose QuietComfort Ultra, Sennheiser Momentum 4 (60h), Sony WH-CH720N, Anker Soundcore Space One, Apple AirPods Pro 2 |
| **Smartwatches** | `PROD-WAT-*` | 4 | Apple Watch Series 9, Samsung Galaxy Watch 6 Classic, Garmin Forerunner 265, Amazfit GTR 4 |
| **Tablets** | `PROD-TAB-*` | 2 | Apple iPad Air 11 M2, Samsung Galaxy Tab S9 FE (with IP68 S-Pen) |
| **Monitors** | `PROD-MON-*` | 2 | LG UltraFine 27US500 4K IPS, Dell UltraSharp U2723QE 4K IPS Black (90W USB-C Hub) |
| **Tech Accessories** | `PROD-ACC-*` | 3 | Logitech MX Master 3S Mouse, Keychron K2 Pro QMK/VIA Mechanical Keyboard, Anker 737 140W Power Bank |
| **Shoes & Footwear** | `PROD-SHO-*` | 6 | Nike Air Zoom Pegasus 40, Adidas Ultraboost Light, Puma Velocity Nitro 3, Skechers Arch Fit Go Walk, Woodland Nubuck Trekking Boots, Clarks Leather Oxford |
| **Clothing & Apparel** | `PROD-CLO-*` | 6 | Levi's 511 Slim Stretch Jeans, Uniqlo Ultra Light Down Winter Jacket, Raymond Egyptian Giza Cotton Formal Shirt, H&M 400GSM Oversized Hoodie, Fabindia Tussar Silk Kurta Set, Nike Dri-FIT ADV Tee |
| **Room Decor & Home** | `PROD-DEC-*` | 6 | Philips Hue Smart RGBWW Corner Floor Lamp, IKEA Ceramic Planter & Acacia Stand, Jaipur Rugs 100% NZ Wool Area Rug (5x8 ft), HomeCentre 3-Piece Nordic Wall Art, Chumbak Aromatherapy Diffuser, Wakefit Blackout Velvet Curtains |
| **Kitchen Utensils & Cookware** | `PROD-UTN-*` | 6 | Prestige Tri-Ply Honeycomb Stainless Steel 4-Pc Set, Hawkins Contura 5L Hard Anodised Pressure Cooker, Meyer Pre-Seasoned Cast Iron Skillet & Dutch Oven, Victorinox Swiss 6-Pc Chef Knife Block, Milton 24-Pc 304 Steel Dinner Set, Borosil 42L OTG & Air Fryer |

---

## 4. Agentic Shopping Tools & Conversational State Memory

The LangGraph shopping assistant (`backend/app/agents/shopping_agent.py`) orchestrates **8 permission-scoped tools**:

1. `search_products()`: Executes hybrid FAISS + BM25 retrieval with RRF and metadata filtering.
2. `compare_products()`: Builds a normalized side-by-side matrix of up to 4 products with pros, cons, specification alignment, and a `0–100` value-for-money score.
3. `filter_by_budget()`: Enforces strict upper/lower price bounds in `₹ INR`.
4. `get_product_details()`: Retrieves verified product specifications, availability, discount, and metadata by `product_id`.
5. `recommend_products()`: Synthesizes multi-constraint recommendations matching user preferences and use cases.
6. `find_similar_products()`: Performs vector-neighborhood search within the target category to locate lower-priced alternatives or higher-tier upgrades.
7. `retrieve_product_reviews()`: Aggregates customer rating scores, review counts, and verified feature highlights.
8. `explain_recommendation()`: Generates transparent grounding explanations linking product specs and budget savings directly to the user's constraints.

### Multi-Turn Conversational State Example
```text
Turn 1 (User)      : "I need a laptop under ₹75,000."
Agent State        : {"category": "Laptops", "max_price": 75000.0}
Agent Action       : Retrieves Acer Swift Go 14 OLED (₹72,990), LenovoThinkPad E14 (₹69,990), Lenovo LOQ 15 (₹67,490).

Turn 2 (User)      : "Compare the top two."
Agent State        : Resolves prior recommended IDs ["PROD-LAP-003", "PROD-LAP-010"] from conversation memory.
Agent Action       : Invokes compare_products() and renders a grounded specification & value comparison matrix.

Turn 3 (User)      : "Now recommend comfortable running shoes under ₹11,000."
Agent State        : Detects category switch -> resets category to {"category": "Shoes", "max_price": 11000.0}.
Agent Action       : Retrieves Puma Velocity Nitro 3 (₹8,499) and Nike Air Zoom Pegasus 40 (₹10,795).
```

---

## 5. Mandatory AI Evaluation Framework & Actual Measured Results

ShopMind AI includes a dedicated evaluation package (`backend/app/evaluation/evaluator.py`) tested against **106 synthetic, ground-truth labeled benchmark queries** (`data/evaluation_questions.json`) across **10 evaluation categories**.

> **Synthetic Benchmark Disclaimer**: All 106 evaluation queries and reference answers are synthetic benchmark examples engineered for reproducible RAG evaluation and contain zero customer PII.

### Measured Benchmark Telemetry (Run ID: `EVAL-E6E8C61C` — 106 Test Questions)

| Metric Category | Metric Name | Mathematical Definition | Measured Result | Pass Threshold | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Composite** | **Overall RAG Quality Score** | Weighted composite of Retrieval & Generation metrics | **95.57%** (`103/106` Passed) | `>= 80.0%` | **PASS** |
| **Retrieval** | **Precision@K (K=5)** | Proportion of retrieved top-K items that are relevant | **92.53%** | `>= 65.0%` | **PASS** |
| **Retrieval** | **Recall@K (K=5)** | Proportion of ground-truth relevant items retrieved in top-K | **97.17%** | `>= 75.0%` | **PASS** |
| **Retrieval** | **Mean Reciprocal Rank (MRR)** | $\frac{1}{|Q|}\sum_{i=1}^{|Q|}\frac{1}{\text{rank}_i}$ of first relevant product | **95.28%** | `>= 75.0%` | **PASS** |
| **Retrieval** | **Hit Rate@K (K=5)** | Fraction of queries with $\ge 1$ relevant product in top-K | **97.17%** | `>= 80.0%` | **PASS** |
| **Retrieval** | **NDCG@K (K=5)** | Normalized Discounted Cumulative Gain across top-K ranks | **95.62%** | `>= 75.0%` | **PASS** |
| **Generation** | **Faithfulness** | Fraction of product IDs & factual claims supported by retrieved context | **100.00%** | `>= 85.0%` | **PASS** |
| **Generation** | **Answer Relevancy** | Semantic & lexical alignment between query intent and generated answer | **93.31%** | `>= 80.0%` | **PASS** |
| **Generation** | **Context Precision** | Average precision at ranks where ground-truth items appear | **95.49%** | `>= 75.0%` | **PASS** |
| **Generation** | **Context Recall** | Coverage of expected reference facts and IDs in retrieved context | **97.99%** | `>= 75.0%` | **PASS** |
| **Generation** | **Response Correctness** | Weighted factual entity & token overlap with reference answer | **98.27%** | `>= 80.0%` | **PASS** |
| **Safety** | **Hallucination Rate** | $1 - \text{Faithfulness} + \text{Unverified Product ID Penalty}$ | **0.00%** | `<= 10.0%` | **PASS** |
| **Performance** | **Average Latency** | Total: **11.98 ms** (Retrieval: **8.92 ms** \| Synthesis: **0.07 ms**) | **11.98 ms** | `< 2000 ms` | **PASS** |

### Category-Level Breakdown Across All 10 Benchmark Categories

| Evaluation Category | Questions | Passed | Pass Rate | Recall@5 | MRR | Faithfulness | Response Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `budget_recommendation` | 12 | 12 | **100.0%** | 100.0% | 91.7% | 100.0% | 100.0% |
| `product_comparison` | 11 | 11 | **100.0%** | 100.0% | 95.5% | 100.0% | 100.0% |
| `technical_specification` | 11 | 11 | **100.0%** | 100.0% | 100.0% | 100.0% | 100.0% |
| `brand_search` | 10 | 10 | **100.0%** | 100.0% | 100.0% | 100.0% | 100.0% |
| `multi_constraint` | 12 | 12 | **100.0%** | 100.0% | 100.0% | 100.0% | 100.0% |
| `feature_explanation` | 10 | 9 | **90.0%** | 90.0% | 90.0% | 100.0% | 90.4% |
| `similar_product` | 10 | 10 | **100.0%** | 100.0% | 95.0% | 100.0% | 99.3% |
| `out_of_scope` | 10 | 10 | **100.0%** | 100.0% | 100.0% | 100.0% | 96.0% |
| `insufficient_evidence` | 10 | 8 | **80.0%** | 80.0% | 80.0% | 100.0% | 96.0% |
| `adversarial_security` | 10 | 10 | **100.0%** | 100.0% | 100.0% | 100.0% | 100.0% |

---

## 6. AI Security Architecture & OWASP LLM Top 10 Audit Results

ShopMind AI implements a multi-layered AI security architecture (`backend/app/security/guardrails.py` & `backend/app/security/scanner.py`) aligned with the **OWASP Top 10 for LLM Applications**:

| Test ID | Attack Vector Tested | OWASP Category | Severity | Measured Mitigation Outcome | Status |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `SEC-TEST-001` | Direct Prompt Injection & System Prompt Extraction | **OWASP LLM01 / LLM07** | `CRITICAL` | Blocked before LLM invocation & logged to `security_events` | **PASS** |
| `SEC-TEST-002` | Jailbreak & Hallucination Policy Override (`DAN`) | **OWASP LLM01** | `HIGH` | Blocked jailbreak persona override directive | **PASS** |
| `SEC-TEST-003` | Indirect Prompt Injection in Product Description | **OWASP LLM01** | `HIGH` | Stripped embedded instruction into `[REDACTED_UNTRUSTED_INSTRUCTION]` | **PASS** |
| `SEC-TEST-004` | Hallucinated Product ID & Secret Leakage Guardrail | **OWASP LLM02 / LLM09** | `CRITICAL` | Flagged unverified `PROD-FAK-999` & redacted `gsk_...` API key | **PASS** |
| `SEC-TEST-005` | SQL Injection Payload in Natural-Language Query | **Database Security** | `CRITICAL` | Blocked `'; DROP TABLE products; --` & enforced parameterized ORM | **PASS** |
| `SEC-TEST-006` | Cross-Site Scripting (`<script>`) in User Prompt | **OWASP LLM05** | `HIGH` | Blocked XSS payload at input inspection gate | **PASS** |
| `SEC-TEST-007` | Invalid & Tampered JWT Signature Verification | **Authentication / RBAC** | `HIGH` | Rejected tampered Bearer token with HTTP `401 Unauthorized` | **PASS** |
| `SEC-TEST-008` | Malicious Executable File Upload (`backdoor.exe`) | **Ingestion Security** | `HIGH` | Rejected non-`.csv`/`.json` binary upload with HTTP `400` | **PASS** |
| `SEC-TEST-009` | Excessive Request Burst Throttling | **OWASP LLM10** | `MEDIUM` | Sliding-window rate limiter throttled burst traffic (`HTTP 429`) | **PASS** |
| `SEC-TEST-010` | Unauthorized Tool & OS Command Execution Probe | **OWASP LLM06** | `CRITICAL` | Blocked `delete_all_database_records()` and `/etc/passwd` probe | **PASS** |

---

## 7. Full-Stack Application Pages (7 Interactive Modules)

1. **Overview / Landing Page (`/`)**: Hero product search bar, one-click RAG prompt chips, live telemetry cards (indexed catalog size, measured RAG quality score, hallucination rate, OWASP security status), and a visual breakdown of the 12-stage RAG pipeline.
2. **AI Shopping Assistant (`/assistant`)**: Full conversational interface with multi-turn session history, active extracted constraint pills (`Category`, `Max Price`, `Brand`, `Specs`), security & grounding verification badges, product recommendation cards, inline comparison tables, hybrid retrieval citations (`Dense`, `BM25`, `Rerank` scores), and helpfulness feedback buttons.
3. **Product Explorer (`/explorer`)**: Filterable 59-product catalog across all 11 categories and 37 brands with price slider, rating filter, sorting, technical specification modal, and vector-retrieved similar product recommendations.
4. **Product Comparison Matrix (`/compare`)**: Side-by-side comparison of up to **4 products** across price, discount, rating, dynamic specifications, pros & cons, `0–100` value-for-money score, and an AI-generated grounded comparison summary.
5. **RAG Evaluation Dashboard (`/evaluation`)**: Live execution of the 106-question evaluation benchmark, Recharts bar/line visualizations, pass/fail threshold indicators, before-and-after run comparison, question-level failure inspector, and downloadable **CSV** and **JSON** evaluation reports.
6. **AI Security Dashboard (`/security`)**: One-click 10-vector automated security penetration scanner, OWASP LLM control checklist, severity counters, and real-time blocked attack audit stream.
7. **Admin MLOps Control Center (`/admin`)**: JWT Role-Based Access Control (`admin` role required) for uploading `.csv`/`.json` product datasets, adding manual products, re-indexing the FAISS + BM25 vector store, inspecting ingestion job logs, viewing system health, and auditing administrative actions.

---

## 8. REST API Reference

Interactive Swagger UI is served at `http://127.0.0.1:8000/docs` and OpenAPI JSON at `http://127.0.0.1:8000/openapi.json`.

| Domain | Method & Endpoint | Auth / Role | Description |
| :--- | :--- | :---: | :--- |
| **Auth** | `POST /api/auth/register` | Public | Register a new shopper account and receive a signed JWT |
| **Auth** | `POST /api/auth/login` | Public | Authenticate with email/password and receive a signed JWT |
| **Auth** | `GET /api/auth/me` | Bearer JWT | Retrieve current authenticated user profile and RBAC role |
| **Shopping** | `POST /api/chat` | Public / JWT | Send natural-language query to the grounded RAG shopping agent |
| **Shopping** | `GET /api/chat/history` | Public / JWT | List user conversations or fetch messages for a `conversation_id` |
| **Shopping** | `DELETE /api/chat/{conversation_id}` | Public / JWT | Delete a conversation (enforces cross-user privacy isolation) |
| **Products** | `GET /api/products` | Public | Search, filter (`category`, `brand`, `max_price`, `min_rating`), and sort catalog |
| **Products** | `GET /api/products/{product_id}` | Public | Retrieve full specifications and metadata for a product ID |
| **Products** | `POST /api/products/compare` | Public | Compare 2 to 4 products side-by-side with an AI grounded summary |
| **Products** | `POST /api/products/recommend` | Public | Retrieve structured recommendations or similar products |
| **RAG** | `POST /api/rag/search` | Public | Direct hybrid FAISS + BM25 + RRF search with score breakdown |
| **RAG** | `POST /api/rag/reindex` | **Admin JWT** | Rebuild FAISS dense vectors and BM25 index from the database |
| **RAG** | `GET /api/rag/status` | Public | Inspect vector count, embedding dimension, and Groq configuration status |
| **Evaluation** | `POST /api/evaluation/run` | Public | Run the 106-question RAG evaluation benchmark and store metrics |
| **Evaluation** | `GET /api/evaluation/results` | Public | Retrieve full metrics and question results for the latest run |
| **Evaluation** | `GET /api/evaluation/history` | Public | Retrieve historical evaluation runs for trend charts |
| **Evaluation** | `GET /api/evaluation/report/{run_id}` | Public | Download evaluation report in `csv` or `json` format |
| **Security** | `GET /api/security/status` | Public | View OWASP LLM guardrail status and blocked attack statistics |
| **Security** | `GET /api/security/events` | Public | Retrieve chronological audit log of blocked security events |
| **Security** | `POST /api/security/test` | Public | Execute the 10-vector automated AI security test suite |
| **Admin** | `POST /api/admin/upload` | **Admin JWT** | Upload & validate `.csv` or `.json` product datasets and re-index |
| **Admin** | `POST /api/admin/products` | **Admin JWT** | Manually add a validated product and index into RAG |
| **Admin** | `GET /api/admin/analytics` | **Admin JWT** | Retrieve KPIs, category distribution, ingestion jobs, and audit logs |
| **Admin** | `GET /api/admin/system-health` | Public | Check live status of Database, Vector Store, Groq LLM, and Guardrails |

---

## 9. Relational Database Schema (11 Tables)

Defined in `backend/app/models/models.py` and managed via Alembic (`backend/migrations/`):

- `users`: `id`, `email` (unique indexed), `full_name`, `hashed_password`, `role` (`user` | `admin`), `is_active`, timestamps.
- `product_categories`: `id`, `name`, `slug`, `description`, `created_at`.
- `products`: `id`, `product_id` (unique indexed), `name`, `brand`, `category`, `category_id` (FK), `description`, `price` (`CHECK price >= 0`), `discount`, `rating` (`CHECK 0 <= rating <= 5`), `review_count`, `specifications` (JSON), `features` (JSON), `availability`, `image_url`, `product_url`, `product_metadata` (JSON), `is_indexed`.
- `conversations`: `id`, `conversation_id` (unique indexed), `user_id` (FK), `title`, `active_constraints` (JSON), timestamps.
- `messages`: `id`, `conversation_id` (FK), `role`, `content`, `recommended_products` (JSON), `citations` (JSON), `retrieval_metadata` (JSON), `confidence_score`, `feedback`, `created_at`.
- `user_preferences`: `id`, `user_id` (FK unique), `preferred_categories` (JSON), `preferred_brands` (JSON), `max_budget`, `required_specs` (JSON).
- `evaluation_runs`: `id`, `run_id`, `dataset_name`, `total_questions`, `passed_questions`, `failed_questions`, `overall_score`, `precision_at_k`, `recall_at_k`, `mrr`, `hit_rate_at_k`, `ndcg_at_k`, `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`, `response_correctness`, `hallucination_rate`, latency/token/cost fields, `thresholds_config` (JSON), `category_breakdown` (JSON).
- `evaluation_results`: Question-level records linked via `run_id` (FK) storing expected vs. retrieved IDs, generated answers, all 11 metrics, `passed`, and `failure_reason`.
- `security_events`: `id`, `event_type`, `severity`, `risk_category`, `endpoint`, `user_id`, `ip_address`, `payload_excerpt`, `mitigation_action`, `blocked`, `created_at`.
- `ingestion_jobs`: `id`, `job_id`, `source_type`, `filename`, `total_records`, `ingested_count`, `updated_count`, `skipped_duplicates`, `failed_count`, `error_details` (JSON), `status`.
- `audit_logs`: `id`, `actor_email`, `action`, `resource_type`, `resource_id`, `details` (JSON), `created_at`.

---

## 10. Project Directory Structure

```text
ShopMind AI — RAG-Based Intelligent Shopping Assistant/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx              # Navigation header, RBAC status & JWT login modal
│   │   │   └── ProductCard.tsx         # Grounded product card with specs & recommendation explanation
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx         # Hero search, live telemetry & 12-stage RAG architecture
│   │   │   ├── AssistantPage.tsx       # Multi-turn conversational RAG interface & citations
│   │   │   ├── ExplorerPage.tsx        # 11-category catalog explorer, filters & similar products modal
│   │   │   ├── ComparisonPage.tsx      # 4-product side-by-side matrix & AI comparison summary
│   │   │   ├── EvaluationPage.tsx      # 106-query RAG evaluation dashboard, Recharts & CSV/JSON export
│   │   │   ├── SecurityPage.tsx        # OWASP LLM Top 10 dashboard & 10-vector penetration scanner
│   │   │   └── AdminPage.tsx           # Admin dataset upload, manual product form, re-index & audit logs
│   │   ├── services/
│   │   │   └── api.ts                  # Typed Axios client with JWT interceptor
│   │   ├── types/
│   │   │   └── index.ts                # TypeScript interfaces for Products, Chat, Evaluation & Security
│   │   ├── App.tsx                     # Router & shared comparison tray state
│   │   ├── main.tsx                    # React DOM entry point
│   │   └── index.css                   # Tailwind CSS & custom dark theme styles
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── shopping_agent.py       # LangGraph workflow, 8 shopping tools & Groq SDK integration
│   │   ├── api/
│   │   │   ├── deps.py                 # JWT auth, RBAC admin guard & sliding-window rate limiter
│   │   │   └── routes.py               # All 24 REST API endpoints across 7 domain tags
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic Settings & SensitiveLogFilter (secret redaction)
│   │   │   └── security.py             # bcrypt hashing, PyJWT signing/verification & RateLimiter
│   │   ├── database/
│   │   │   ├── seed_generator.py       # Generates 58+ products CSV & 106-question evaluation JSON
│   │   │   └── session.py              # SQLAlchemy engine (PostgreSQL primary + SQLite fallback)
│   │   ├── evaluation/
│   │   │   └── evaluator.py            # Retrieval, RAGAS/DeepEval generation metrics & CSV/JSON exporter
│   │   ├── models/
│   │   │   └── models.py               # 11 SQLAlchemy 2.0 relational ORM models
│   │   ├── rag/
│   │   │   ├── ingestion.py            # CSV/JSON/Manual ingestion, cleaning, dedup & upload validation
│   │   │   └── pipeline.py             # SentenceTransformers, FAISS, BM25, RRF, QueryAnalyzer & Reranker
│   │   ├── schemas/
│   │   │   └── schemas.py              # Pydantic v2 request/response schemas
│   │   ├── security/
│   │   │   ├── guardrails.py           # OWASP LLM input/document/output security guardrails
│   │   │   └── scanner.py              # 10-vector automated AI security penetration test suite
│   │   └── main.py                     # FastAPI app bootstrapper, lifespan seeding & CORS middleware
│   ├── migrations/                     # Alembic database migration scripts
│   ├── evaluation_dataset/
│   │   └── evaluation_questions.json   # Reproducible 106-question labeled evaluation benchmark
│   ├── tests/
│   │   └── test_shopmind.py            # Comprehensive pytest suite (unit, integration, RAG, security)
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── data/
│   ├── sample_products.csv             # 58+ multi-category products with JSON specifications & metadata
│   └── evaluation_questions.json       # 106-question ground-truth evaluation dataset
│
├── docs/
│   └── ARCHITECTURE.md                 # System architecture & data flow documentation
├── .github/workflows/ci.yml            # GitHub Actions CI pipeline (pytest + TypeScript production build)
├── docker-compose.yml                  # Multi-container orchestration (PostgreSQL, Redis, Backend, Frontend)
├── .env.example                        # Environment configuration template
├── requirements.txt                    # Root Python dependency manifest
└── README.md
```

---

## 11. Installation, Configuration & Running the Application

### Prerequisites
- **Python**: `3.11+`
- **Node.js**: `18+` (or `20+`)
- *(Optional)* **Docker & Docker Compose** for containerized PostgreSQL + Redis deployment.

### Step 1: Clone & Configure Environment Variables
```powershell
Copy-Item .env.example .env
```
Edit `.env` to add your Groq API key (optional for local offline testing):
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
DATABASE_URL=postgresql+psycopg2://shopmind:shopmind_secret@localhost:5432/shopmind_db
SQLITE_FALLBACK_URL=sqlite:///./data/shopmind.db
USE_SQLITE_FALLBACK=true
SECRET_KEY=change-this-to-a-64-char-cryptographic-secret-in-production-env
```

### Step 2: Install Backend Dependencies & Start FastAPI Server (Terminal 1)
```powershell
pip install -r requirements.txt
python backend/app/database/seed_generator.py

$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

### Step 3: Install Frontend Dependencies & Start Vite Dev Server (Terminal 2)
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
- **Frontend Web Application**: `http://localhost:5173`

### Pre-Seeded Demo Accounts (One-Click Login Available in UI)

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@shopmind.ai` | `Admin@ShopMind2026!` | Full access to Admin Ops (`/api/admin/*`), dataset upload, manual product entry, vector re-indexing, and audit logs |
| **Demo Shopper** | `demo@shopmind.ai` | `Shopper@2026!` | Conversational RAG assistant, private chat history, product explorer, and 4-product comparison |

---

## 12. Testing, CI/CD & Production Deployment

### Execute Automated Pytest Suite
```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests/test_shopmind.py -v
```
Verifies:
1. `test_data_cleaning_and_indirect_injection_sanitization`
2. `test_embedding_generation_and_vector_store`
3. `test_hybrid_retrieval_and_reranking`
4. `test_similar_products_and_shopping_tools`
5. `test_conversational_shopping_assistant_and_context`
6. `test_product_endpoints_and_comparison`
7. `test_authentication_rbac_and_cross_user_isolation`
8. `test_ai_security_guardrails_and_automated_scanner`
9. `test_evaluation_metrics_and_endpoints`

### Build Production Frontend Bundle
```powershell
cd frontend
npm.cmd run build
```

### Deploy Full Stack via Docker Compose (PostgreSQL 16 + Redis 7 + FastAPI + Nginx React)
```powershell
docker compose up --build -d
```

### Run Database Migrations with Alembic
```powershell
cd backend
alembic upgrade head
```

---

## 13. Known Limitations & Future Roadmap

- **Fine-Grained Negative Attribute Detection**: In the 106-question benchmark, 103/106 queries pass (`95.57%` overall score). Two `insufficient_evidence` queries that reference an in-stock product while asking for unrecorded sub-metrics (such as PCB layer count or SAR radiation value) still retrieve the named product card even though the text answer correctly refuses to fabricate the missing metric. Adding slot-level schema coverage checks in `QueryAnalyzer` will bring those edge cases to 100%.
- **GPU Cross-Encoder Reranking**: On CPU environments, ShopMind AI uses a sub-10ms domain cross-feature and specification satisfaction reranker. Deploying on a GPU node enables `cross-encoder/ms-marco-MiniLM-L-6-v2` full neural pair scoring for 100k+ SKU catalogs.
- **Multimodal Visual Search**: Future iterations will integrate CLIP image embeddings so users can upload a photo of a sneaker, lamp, or outfit to retrieve visually similar products.
