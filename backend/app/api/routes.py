"""Complete FastAPI REST API routers for ShopMind AI."""
# This module defines the complete set of FastAPI API routes for the ShopMind AI application, including endpoints for user authentication, shopping assistant interactions, product management, retrieval-augmented generation (RAG) operations, evaluation framework, AI security monitoring, and administrative functions. Each route is implemented with appropriate request validation, database interactions, and security checks to ensure safe and efficient operation of the application.
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.shopping_agent import ShoppingTools, shopping_agent
from app.api.deps import enforce_rate_limit, get_admin_user, get_current_user, get_optional_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.evaluation.evaluator import RAGEvaluator
from app.models.models import (
    AuditLog,
    Conversation,
    EvaluationResult,
    EvaluationRun,
    IngestionJob,
    Message,
    Product,
    ProductCategory,
    SecurityEvent,
    User,
    UserPreference,
)
from app.rag.ingestion import ingest_product_records, validate_and_parse_upload
from app.rag.pipeline import rag_engine
from app.schemas.schemas import (
    AuthTokenResponse,
    ChatRequest,
    ChatResponse,
    EvaluationRunRequest,
    ProductCompareRequest,
    ProductCreateRequest,
    ProductRecommendRequest,
    ProductResponse,
    RAGSearchRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.security.guardrails import AISecurityGuard
from app.security.scanner import SecurityScanner
from app.services.data_science import DataScienceEngine

api_router = APIRouter(prefix="/api", dependencies=[Depends(enforce_rate_limit)])


# =====================================================================
# 1. AUTHENTICATION ENDPOINTS (/api/auth/*)
# =====================================================================
@api_router.post("/auth/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")

    user = User(
        email=payload.email.lower().strip(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return AuthTokenResponse(access_token=token, user=UserResponse.model_validate(user))


@api_router.post("/auth/login", response_model=AuthTokenResponse, tags=["Authentication"])
def login_user(payload: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        AISecurityGuard.log_security_event(
            db=db,
            event_type="FAILED_LOGIN_ATTEMPT",
            severity="MEDIUM",
            risk_category="Authentication & Brute-Force Defense",
            endpoint="/api/auth/login",
            user_id=user.id if user else None,
            ip_address=request.client.host if request.client else "127.0.0.1",
            payload_excerpt=f"Failed login for {payload.email}",
            mitigation_action="Rejected invalid credentials with HTTP 401",
            blocked=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return AuthTokenResponse(access_token=token, user=UserResponse.model_validate(user))


@api_router.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


# =====================================================================
# 2. SHOPPING ASSISTANT & CONVERSATION ENDPOINTS (/api/chat*)
# =====================================================================
@api_router.post("/chat", response_model=ChatResponse, tags=["Shopping Assistant"])
def chat_with_assistant(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_id = current_user.id if current_user else None

    conv: Optional[Conversation] = None
    if payload.conversation_id:
        conv = db.query(Conversation).filter(Conversation.conversation_id == payload.conversation_id).first()
        # Cross-user data isolation check
        if conv and conv.user_id is not None and conv.user_id != user_id:
            AISecurityGuard.log_security_event(
                db=db,
                event_type="CROSS_USER_CONVERSATION_ACCESS_BLOCKED",
                severity="HIGH",
                risk_category="OWASP LLM02: Cross-User Privacy Isolation",
                endpoint="/api/chat",
                user_id=user_id,
                ip_address=client_ip,
                payload_excerpt=f"User {user_id} tried to access conversation {payload.conversation_id}",
                mitigation_action="Blocked cross-user conversation access with HTTP 403",
                blocked=True,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to another user's conversation.")

    if not conv:
        conv_uid = payload.conversation_id or f"CONV-{uuid.uuid4().hex[:10].upper()}"
        conv = Conversation(
            conversation_id=conv_uid,
            user_id=user_id,
            title=payload.message[:65].strip(),
            active_constraints=payload.preferences or {},
        )
        db.add(conv)
        db.flush()

    # Load last recommended product IDs from conversation history for contextual follow-ups
    last_recommended_ids: List[str] = []
    if conv.messages:
        for m in reversed(conv.messages):
            if m.role == "assistant" and m.recommended_products:
                last_recommended_ids = [p.get("product_id") for p in m.recommended_products if p.get("product_id")]
                if last_recommended_ids:
                    break

    # Redact any accidental user secrets before saving to memory
    safe_user_message = AISecurityGuard.redact_conversation_secrets(payload.message)
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=safe_user_message,
    )
    db.add(user_msg)

    # Merge user stored preferences if available
    prior_constraints = dict(conv.active_constraints or {})
    if payload.preferences:
        prior_constraints.update(payload.preferences)

    agent_result = shopping_agent.run(
        db=db,
        query=payload.message,
        prior_constraints=prior_constraints,
        last_recommended_ids=last_recommended_ids,
        user_id=user_id,
        ip_address=client_ip,
        endpoint="/api/chat",
    )

    # Update conversation state constraints
    if agent_result["security_status"]["safe"]:
        conv.active_constraints = agent_result["extracted_constraints"]
        if current_user and agent_result["extracted_constraints"]:
            pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
            if not pref:
                pref = UserPreference(user_id=current_user.id)
                db.add(pref)
            c = agent_result["extracted_constraints"]
            if "category" in c:
                cats = list(pref.preferred_categories or [])
                if c["category"] not in cats:
                    cats.append(c["category"])
                pref.preferred_categories = cats
            if "brand" in c:
                brs = list(pref.preferred_brands or [])
                if c["brand"] not in brs:
                    brs.append(c["brand"])
                pref.preferred_brands = brs
            if "max_price" in c:
                pref.max_budget = float(c["max_price"])

    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=agent_result["answer"],
        recommended_products=agent_result["recommended_products"],
        citations=agent_result["citations"],
        retrieval_metadata={
            "intent": agent_result["intent"],
            "constraints": agent_result["extracted_constraints"],
            "rewritten_query": agent_result["rewritten_query"],
            "comparison_table": agent_result["comparison_table"],
            "latency_ms": agent_result["latency_ms"],
            "llm_provider": agent_result["llm_provider"],
        },
        confidence_score=agent_result["confidence_score"],
    )
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        conversation_id=conv.conversation_id,
        answer=agent_result["answer"],
        intent=agent_result["intent"],
        extracted_constraints=agent_result["extracted_constraints"],
        rewritten_query=agent_result["rewritten_query"],
        recommended_products=agent_result["recommended_products"],
        comparison_table=agent_result["comparison_table"],
        citations=agent_result["citations"],
        confidence_score=agent_result["confidence_score"],
        grounding_verified=agent_result["grounding_verified"],
        security_status=agent_result["security_status"],
        latency_ms=agent_result["latency_ms"],
        llm_provider=agent_result["llm_provider"],
    )


@api_router.get("/chat/history", tags=["Shopping Assistant"])
def get_chat_history(
    conversation_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.conversation_id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
        if conv.user_id is not None and conv.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user's conversation.")
        return {
            "conversation_id": conv.conversation_id,
            "title": conv.title,
            "active_constraints": conv.active_constraints,
            "created_at": conv.created_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "recommended_products": m.recommended_products,
                    "citations": m.citations,
                    "retrieval_metadata": m.retrieval_metadata,
                    "confidence_score": m.confidence_score,
                    "created_at": m.created_at,
                }
                for m in conv.messages
            ],
        }

    query = db.query(Conversation)
    if user_id is not None:
        query = query.filter(Conversation.user_id == user_id)
    else:
        query = query.filter(Conversation.user_id.is_(None))
    convs = query.order_by(Conversation.updated_at.desc()).limit(25).all()
    return {
        "conversations": [
            {
                "conversation_id": c.conversation_id,
                "title": c.title,
                "active_constraints": c.active_constraints,
                "message_count": len(c.messages),
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in convs
        ]
    }


@api_router.delete("/chat/{conversation_id}", tags=["Shopping Assistant"])
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    conv = db.query(Conversation).filter(Conversation.conversation_id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    user_id = current_user.id if current_user else None
    if conv.user_id is not None and conv.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's conversation.")
    db.delete(conv)
    db.commit()
    return {"deleted": True, "conversation_id": conversation_id}


# =====================================================================
# 3. PRODUCTS ENDPOINTS (/api/products*)
# =====================================================================
@api_router.get("/products", tags=["Products"])
def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_rating: Optional[float] = Query(default=None, ge=0, le=5),
    sort_by: str = Query(default="rating_desc"),
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if category and category.lower() != "all":
        q = q.filter(func.lower(Product.category) == category.lower())
    if brand and brand.lower() != "all":
        q = q.filter(func.lower(Product.brand) == brand.lower())
    if min_price is not None:
        q = q.filter(Product.price >= min_price)
    if max_price is not None:
        q = q.filter(Product.price <= max_price)
    if min_rating is not None:
        q = q.filter(Product.rating >= min_rating)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        q = q.filter(
            (Product.name.ilike(pattern))
            | (Product.brand.ilike(pattern))
            | (Product.category.ilike(pattern))
            | (Product.description.ilike(pattern))
            | (Product.product_id.ilike(pattern))
        )

    if sort_by == "price_asc":
        q = q.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        q = q.order_by(Product.price.desc())
    elif sort_by == "reviews_desc":
        q = q.order_by(Product.review_count.desc())
    else:
        q = q.order_by(Product.rating.desc(), Product.review_count.desc())

    items = q.all()
    all_categories = [r[0] for r in db.query(Product.category).distinct().order_by(Product.category).all()]
    all_brands = [r[0] for r in db.query(Product.brand).distinct().order_by(Product.brand).all()]

    return {
        "total": len(items),
        "categories": all_categories,
        "brands": all_brands,
        "products": [ProductResponse.model_validate(p) for p in items],
    }


@api_router.get("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
def get_product_by_id(product_id: str, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(func.lower(Product.product_id) == product_id.lower()).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found.")
    return ProductResponse.model_validate(prod)


@api_router.post("/products/compare", tags=["Products"])
def compare_products_endpoint(payload: ProductCompareRequest, db: Session = Depends(get_db)):
    cmp_data = ShoppingTools.compare_products(
        db=db,
        product_ids=payload.product_ids,
        focus_criteria=payload.focus_criteria,
    )
    if len(cmp_data["products"]) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least two valid product IDs are required to generate a comparison.",
        )

    names_str = ", ".join(f"{p['name']} ({p['product_id']})" for p in cmp_data["products"])
    agent_summary = shopping_agent.run(
        db=db,
        query=f"Compare {names_str} based on price, specifications, performance, and value for money.",
        endpoint="/api/products/compare",
    )

    return {
        "products": cmp_data["products"],
        "comparison_table": cmp_data["comparison_table"],
        "spec_keys": cmp_data.get("spec_keys", []),
        "ai_summary": agent_summary["answer"],
        "llm_provider": agent_summary["llm_provider"],
        "grounding_verified": agent_summary["grounding_verified"],
    }


@api_router.post("/products/recommend", tags=["Products"])
def recommend_products_endpoint(payload: ProductRecommendRequest, db: Session = Depends(get_db)):
    res = ShoppingTools.recommend_products(
        db=db,
        query=payload.query,
        category=payload.category,
        brand=payload.brand,
        max_budget=payload.max_budget,
        min_rating=payload.min_rating,
        required_specs=payload.required_specs,
        similar_to_product_id=payload.similar_to_product_id,
        top_k=payload.top_k,
    )
    cards = []
    for p in res["results"]:
        cards.append(
            {
                **p,
                "why_recommended": ShoppingTools.explain_recommendation(
                    p, res.get("constraints", {}), payload.query or ""
                ),
            }
        )
    return {
        "intent": res.get("intent", "product_discovery"),
        "constraints": res.get("constraints", {}),
        "count": len(cards),
        "recommendations": cards,
    }


# =====================================================================
# 4. RAG PIPELINE ENDPOINTS (/api/rag/*)
# =====================================================================
@api_router.post("/rag/search", tags=["RAG Pipeline"])
def rag_search_endpoint(payload: RAGSearchRequest, db: Session = Depends(get_db)):
    sec = AISecurityGuard.inspect_user_query(payload.query, db=db, endpoint="/api/rag/search")
    if not sec["safe"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sec["reason"])

    res = rag_engine.hybrid_retrieve(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        category=payload.category,
        brand=payload.brand,
        max_price=payload.max_price,
        min_rating=payload.min_rating,
        use_reranker=payload.use_reranker,
    )
    return res


@api_router.post("/rag/reindex", tags=["RAG Pipeline"])
def rag_reindex_endpoint(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    stats = rag_engine.build_index_from_db(db)
    db.add(
        AuditLog(
            actor_email=admin_user.email,
            action="REINDEX_VECTOR_STORE",
            resource_type="RAG_INDEX",
            resource_id="products.faiss",
            details=stats,
        )
    )
    db.commit()
    return stats


@api_router.get("/rag/status", tags=["RAG Pipeline"])
def rag_status_endpoint(db: Session = Depends(get_db)):
    rag_engine.ensure_initialized(db)
    total_db_products = db.query(Product).count()
    return {
        "status": "ONLINE",
        "total_products_in_db": total_db_products,
        "indexed_chunks": len(rag_engine.document_chunks),
        "embedding_model": rag_engine.embedder.backend_name,
        "vector_dimension": rag_engine.embedder.dimension,
        "vector_store": "FAISS IndexFlatIP + Okapi BM25 Hybrid + Reciprocal Rank Fusion",
        "reranker": "Domain Cross-Feature & Constraint Reranker",
        "groq_model": settings.GROQ_MODEL,
        "groq_api_configured": settings.groq_configured,
        "last_indexed_at": rag_engine.last_indexed_at,
    }


# =====================================================================
# 5. EVALUATION FRAMEWORK ENDPOINTS (/api/evaluation/*)
# =====================================================================
@api_router.post("/evaluation/run", tags=["RAG Evaluation"])
def run_evaluation_endpoint(
    payload: Optional[EvaluationRunRequest] = None,
    db: Session = Depends(get_db),
):
    req = payload or EvaluationRunRequest()
    run = RAGEvaluator.run_evaluation(
        db=db,
        sample_size=req.sample_size,
        top_k=req.top_k,
        custom_thresholds=req.thresholds,
    )
    return _serialize_evaluation_run(run, include_results=True)


@api_router.get("/evaluation/results", tags=["RAG Evaluation"])
def get_latest_evaluation_results(db: Session = Depends(get_db)):
    latest = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).first()
    if not latest:
        latest = RAGEvaluator.run_evaluation(db=db)
    return _serialize_evaluation_run(latest, include_results=True)


@api_router.get("/evaluation/history", tags=["RAG Evaluation"])
def get_evaluation_history(db: Session = Depends(get_db)):
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(20).all()
    if not runs:
        latest = RAGEvaluator.run_evaluation(db=db)
        runs = [latest]
    return {
        "total_runs": len(runs),
        "runs": [_serialize_evaluation_run(r, include_results=False) for r in runs],
    }


@api_router.get("/evaluation/report/{run_id}", tags=["RAG Evaluation"])
def download_evaluation_report(
    run_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    run = db.query(EvaluationRun).filter(EvaluationRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evaluation run '{run_id}' not found.")

    if format == "csv":
        csv_text = RAGEvaluator.export_run_csv(run)
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{run.run_id}_report.csv"'},
        )

    payload = _serialize_evaluation_run(run, include_results=True)
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{run.run_id}_report.json"'},
    )


def _serialize_evaluation_run(run: EvaluationRun, include_results: bool = True) -> Dict[str, Any]:
    thresholds = run.thresholds_config or {}
    metric_statuses = {
        "precision_at_k": run.precision_at_k >= thresholds.get("precision_at_k", settings.EVAL_MIN_PRECISION_AT_K),
        "recall_at_k": run.recall_at_k >= thresholds.get("recall_at_k", settings.EVAL_MIN_RECALL_AT_K),
        "mrr": run.mrr >= thresholds.get("mrr", settings.EVAL_MIN_MRR),
        "ndcg_at_k": run.ndcg_at_k >= thresholds.get("ndcg_at_k", settings.EVAL_MIN_NDCG),
        "faithfulness": run.faithfulness >= thresholds.get("faithfulness", settings.EVAL_MIN_FAITHFULNESS),
        "answer_relevancy": run.answer_relevancy >= thresholds.get("answer_relevancy", settings.EVAL_MIN_ANSWER_RELEVANCY),
        "hallucination_rate": run.hallucination_rate <= thresholds.get("max_hallucination_rate", settings.EVAL_MAX_HALLUCINATION_RATE),
    }

    data: Dict[str, Any] = {
        "run_id": run.run_id,
        "dataset_name": run.dataset_name,
        "is_synthetic_benchmark": True,
        "total_questions": run.total_questions,
        "passed_questions": run.passed_questions,
        "failed_questions": run.failed_questions,
        "pass_rate": round(run.passed_questions / max(1, run.total_questions), 4),
        "overall_score": run.overall_score,
        "precision_at_k": run.precision_at_k,
        "recall_at_k": run.recall_at_k,
        "mrr": run.mrr,
        "hit_rate_at_k": run.hit_rate_at_k,
        "ndcg_at_k": run.ndcg_at_k,
        "faithfulness": run.faithfulness,
        "answer_relevancy": run.answer_relevancy,
        "context_precision": run.context_precision,
        "context_recall": run.context_recall,
        "response_correctness": run.response_correctness,
        "hallucination_rate": run.hallucination_rate,
        "avg_latency_ms": run.avg_latency_ms,
        "avg_retrieval_latency_ms": run.avg_retrieval_latency_ms,
        "avg_generation_latency_ms": run.avg_generation_latency_ms,
        "total_tokens": run.total_tokens,
        "estimated_cost_usd": run.estimated_cost_usd,
        "retrieval_success_rate": run.retrieval_success_rate,
        "thresholds": thresholds,
        "metric_pass_status": metric_statuses,
        "category_breakdown": run.category_breakdown,
        "status": run.status,
        "created_at": run.created_at,
    }
    if include_results:
        data["question_results"] = [
            {
                "question_id": r.question_id,
                "category": r.category,
                "query": r.query,
                "expected_product_ids": r.expected_product_ids,
                "retrieved_product_ids": r.retrieved_product_ids,
                "expected_answer": r.expected_answer,
                "generated_answer": r.generated_answer,
                "precision_at_k": r.precision_at_k,
                "recall_at_k": r.recall_at_k,
                "mrr": r.mrr,
                "ndcg_at_k": r.ndcg_at_k,
                "hit_rate": r.hit_rate,
                "faithfulness": r.faithfulness,
                "answer_relevancy": r.answer_relevancy,
                "context_precision": r.context_precision,
                "context_recall": r.context_recall,
                "response_correctness": r.response_correctness,
                "hallucination_rate": r.hallucination_rate,
                "latency_ms": r.latency_ms,
                "passed": r.passed,
                "failure_reason": r.failure_reason,
            }
            for r in run.results
        ]
        data["failed_cases"] = [q for q in data["question_results"] if not q["passed"]]
    return data


# =====================================================================
# 6. AI SECURITY ENDPOINTS (/api/security/*)
# =====================================================================
@api_router.get("/security/status", tags=["AI Security"])
def get_security_status(db: Session = Depends(get_db)):
    total_events = db.query(SecurityEvent).count()
    blocked_events = db.query(SecurityEvent).filter(SecurityEvent.blocked == True).count()
    by_severity = dict(
        db.query(SecurityEvent.severity, func.count(SecurityEvent.id)).group_by(SecurityEvent.severity).all()
    )
    by_category = dict(
        db.query(SecurityEvent.risk_category, func.count(SecurityEvent.id)).group_by(SecurityEvent.risk_category).all()
    )

    return {
        "security_layer_active": True,
        "owasp_llm_protections": [
            "LLM01: Direct & Indirect Prompt Injection Guardrails",
            "LLM02: Sensitive Information & Cross-User Privacy Redaction",
            "LLM05: Improper Output Handling & XSS Sanitization",
            "LLM06: Scoped Tool Execution & Excessive Agency Prevention",
            "LLM07: System Prompt & Credential Extraction Defense",
            "LLM09: Hallucination Verification & Product ID Grounding",
            "LLM10: Sliding-Window Rate Limiting & Payload Size Caps",
        ],
        "total_security_events": total_events,
        "blocked_attacks": blocked_events,
        "severity_breakdown": by_severity,
        "risk_category_breakdown": by_category,
    }


@api_router.get("/security/events", tags=["AI Security"])
def get_security_events(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    events = db.query(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(limit).all()
    return {
        "total": len(events),
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "risk_category": e.risk_category,
                "endpoint": e.endpoint,
                "payload_excerpt": e.payload_excerpt,
                "mitigation_action": e.mitigation_action,
                "blocked": e.blocked,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }


@api_router.post("/security/test", tags=["AI Security"])
def run_automated_security_tests(db: Session = Depends(get_db)):
    return SecurityScanner.run_security_test_suite(db=db)


# =====================================================================
# 7. ADMIN ENDPOINTS (/api/admin/*)
# =====================================================================
@api_router.post("/admin/upload", tags=["Admin"])
async def admin_upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    content = await file.read()
    try:
        records, source_type = validate_and_parse_upload(file.filename or "upload.csv", content)
    except ValueError as exc:
        AISecurityGuard.log_security_event(
            db=db,
            event_type="MALICIOUS_OR_INVALID_FILE_UPLOAD",
            severity="HIGH",
            risk_category="File Upload Validation",
            endpoint="/api/admin/upload",
            user_id=admin_user.id,
            ip_address="admin-upload",
            payload_excerpt=f"Filename={file.filename}: {exc}",
            mitigation_action="Rejected file upload before ingestion",
            blocked=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    job_summary = ingest_product_records(
        db=db,
        records=records,
        source_type=source_type,
        filename=file.filename or "upload.csv",
    )
    index_stats = rag_engine.build_index_from_db(db)

    db.add(
        AuditLog(
            actor_email=admin_user.email,
            action="UPLOAD_PRODUCT_DATASET",
            resource_type="INGESTION_JOB",
            resource_id=job_summary["job_id"],
            details={"job": job_summary, "index": index_stats},
        )
    )
    db.commit()
    return {"ingestion_job": job_summary, "vector_index": index_stats}


@api_router.post("/admin/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["Admin"])
def admin_add_manual_product(
    payload: ProductCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    raw_dict = payload.model_dump()
    job = ingest_product_records(
        db=db,
        records=[raw_dict],
        source_type="MANUAL",
        filename="admin_manual_entry",
    )
    if job["failed_count"] > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=job["error_details"][0]["error"])

    rag_engine.build_index_from_db(db)
    prod = db.query(Product).order_by(Product.id.desc()).first()
    db.add(
        AuditLog(
            actor_email=admin_user.email,
            action="CREATE_PRODUCT_MANUAL",
            resource_type="PRODUCT",
            resource_id=prod.product_id,
            details={"name": prod.name, "price": prod.price},
        )
    )
    db.commit()
    return ProductResponse.model_validate(prod)


@api_router.get("/admin/analytics", tags=["Admin"])
def admin_get_analytics(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    total_products = db.query(Product).count()
    total_users = db.query(User).count()
    total_conversations = db.query(Conversation).count()
    total_messages = db.query(Message).count()
    total_eval_runs = db.query(EvaluationRun).count()
    total_security_events = db.query(SecurityEvent).count()

    category_counts = dict(
        db.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    )
    jobs = db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(15).all()
    audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(25).all()

    return {
        "kpis": {
            "total_products": total_products,
            "total_users": total_users,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_evaluation_runs": total_eval_runs,
            "total_security_events": total_security_events,
        },
        "category_distribution": [{"category": k, "count": v} for k, v in category_counts.items()],
        "ingestion_jobs": [
            {
                "job_id": j.job_id,
                "source_type": j.source_type,
                "filename": j.filename,
                "total_records": j.total_records,
                "ingested_count": j.ingested_count,
                "updated_count": j.updated_count,
                "skipped_duplicates": j.skipped_duplicates,
                "failed_count": j.failed_count,
                "error_details": j.error_details,
                "status": j.status,
                "created_at": j.created_at,
            }
            for j in jobs
        ],
        "audit_logs": [
            {
                "id": a.id,
                "actor_email": a.actor_email,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "details": a.details,
                "created_at": a.created_at,
            }
            for a in audits
        ],
    }


@api_router.get("/admin/system-health", tags=["Admin"])
def admin_system_health(db: Session = Depends(get_db)):
    rag_engine.ensure_initialized(db)
    db_ok = True
    try:
        db.query(Product).count()
    except Exception:
        db_ok = False

    return {
        "status": "HEALTHY" if db_ok else "DEGRADED",
        "components": {
            "database": {
                "status": "CONNECTED" if db_ok else "ERROR",
                "engine": str(db.bind.dialect.name) if db.bind else "sqlite",
            },
            "vector_store": {
                "status": "READY" if rag_engine.faiss_index is not None else "EMPTY",
                "indexed_vectors": len(rag_engine.products_cache),
                "dimension": rag_engine.embedder.dimension,
                "embedding_backend": rag_engine.embedder.backend_name,
            },
            "llm_provider": {
                "provider": "Groq API",
                "configured_model": settings.GROQ_MODEL,
                "api_key_configured": settings.groq_configured,
                "mode": f"Live Groq ({settings.GROQ_MODEL})"
                if settings.groq_configured
                else "Grounded RAG Deterministic Synthesis (Set GROQ_API_KEY in .env to enable live Groq API calls)",
            },
            "security_guardrails": {
                "status": "ACTIVE",
                "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
                "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            },
        },
    }


# =====================================================================
# 8. DATA SCIENCE & STATISTICAL ML ENDPOINTS (/api/datascience/*)
# =====================================================================
@api_router.get("/datascience/insights", tags=["Data Science & ML Lab"])
def get_data_science_insights(db: Session = Depends(get_db)):
    rag_engine.ensure_initialized(db)
    bayesian_and_anomalies = DataScienceEngine.compute_bayesian_ratings_and_anomalies(rag_engine.products_cache)
    pca_manifold = DataScienceEngine.compute_embedding_manifold_pca(db=db, n_clusters=7)
    ablation_study = DataScienceEngine.run_retrieval_ablation_study(db=db)
    bootstrap_ci = DataScienceEngine.compute_bootstrap_confidence_intervals(db=db, n_bootstraps=400)

    return {
        "bayesian_and_anomalies": bayesian_and_anomalies,
        "pca_manifold": pca_manifold,
        "ablation_study": ablation_study,
        "bootstrap_ci": bootstrap_ci,
    }
