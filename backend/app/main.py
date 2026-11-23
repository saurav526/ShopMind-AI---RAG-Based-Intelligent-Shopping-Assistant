"""Main FastAPI application entry point with lifespan initialization, seeding, indexing, and baseline evaluation."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import api_router
from app.core.config import DATA_DIR, logger, settings
from app.core.security import hash_password
from app.database.seed_generator import generate_datasets
from app.database.session import Base, SessionLocal, engine
from app.evaluation.evaluator import RAGEvaluator
from app.models.models import AuditLog, EvaluationRun, Product, User
from app.rag.ingestion import ingest_from_csv_path
from app.rag.pipeline import rag_engine
from app.security.scanner import SecurityScanner


def initialize_system(db: Session) -> None:
    """Seeds default admin/demo users, product catalog, FAISS+BM25 vector store, baseline evaluation, and security scan."""
    Base.metadata.create_all(bind=engine)

    # 1. Ensure datasets exist on disk
    csv_path = DATA_DIR / "sample_products.csv"
    eval_path = DATA_DIR / "evaluation_questions.json"
    if not csv_path.exists() or not eval_path.exists():
        generate_datasets()

    # 2. Seed default admin and demo shopper accounts if not present
    admin = db.query(User).filter(User.email == "admin@shopmind.ai").first()
    if not admin:
        admin = User(
            email="admin@shopmind.ai",
            full_name="ShopMind Lead Architect (Admin)",
            hashed_password=hash_password("Admin@ShopMind2026!"),
            role="admin",
            is_active=True,
        )
        db.add(admin)

    shopper = db.query(User).filter(User.email == "demo@shopmind.ai").first()
    if not shopper:
        shopper = User(
            email="demo@shopmind.ai",
            full_name="Aarav Sharma (Demo Shopper)",
            hashed_password=hash_password("Shopper@2026!"),
            role="user",
            is_active=True,
        )
        db.add(shopper)
    db.commit()

    # 3. Seed or sync products from sample_products.csv whenever new products exist in CSV
    product_count = db.query(Product).count()
    with open(csv_path, mode="r", encoding="utf-8") as f_csv:
        csv_row_count = max(0, sum(1 for _ in f_csv) - 1)
    if product_count < csv_row_count:
        job_info = ingest_from_csv_path(db, csv_path)
        db.add(
            AuditLog(
                actor_email="system@shopmind.ai",
                action="BOOTSTRAP_SEED_CATALOG",
                resource_type="INGESTION_JOB",
                resource_id=job_info["job_id"],
                details=job_info,
            )
        )
        db.commit()
        logger.info(f"Seeded/synced {job_info['ingested_count']} new products from {csv_path.name}")

    # 4. Build FAISS + BM25 Hybrid Vector Index
    rag_engine.build_index_from_db(db)

    # 5. Run baseline RAG Evaluation & Security Test Suite if database has no evaluation runs yet
    if db.query(EvaluationRun).count() == 0:
        logger.info("Running initial baseline RAG evaluation on ground-truth dataset...")
        RAGEvaluator.run_evaluation(db=db)
        SecurityScanner.run_security_test_suite(db=db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        initialize_system(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade RAG-Based Intelligent Shopping Assistant with Hybrid FAISS+BM25 Retrieval, "
        "Cross-Feature Reranking, LangGraph Agentic Tools, Groq LLM Integration, 106-Question RAG Evaluation Benchmark, "
        "and OWASP Top 10 for LLM Applications Security Layer."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["Root"])
def root_health():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "OPERATIONAL",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }
