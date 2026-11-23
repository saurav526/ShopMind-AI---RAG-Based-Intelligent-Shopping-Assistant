"""Relational database ORM models for ShopMind AI."""

#  it explain the model used in the ShopMind AI application, which are defined using SQLAlchemy ORM. The module includes models for users, products, product categories, conversations, messages, user preferences, evaluation runs and results, security events, ingestion jobs, and audit logs. Each model defines the database schema, relationships between entities, and relevant constraints to ensure data integrity and support the application's functionality.

#  Its main aim is to provide a structured representation of the application's data, enabling efficient storage, retrieval, and manipulation of information related to user interactions, product recommendations, evaluation metrics, and security monitoring.
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (JSON,Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)  # "user" or "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    products: Mapped[List["Product"]] = relationship("Product", back_populates="category_rel")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="check_positive_price"),
        CheckConstraint("rating >= 0 AND rating <= 5", name="check_rating_bounds"),
        Index("idx_products_category_brand_price", "category", "brand", "price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    specifications: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    features: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    availability: Mapped[str] = mapped_column(String(64), default="In Stock", nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    product_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    product_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    category_rel: Mapped[Optional["ProductCategory"]] = relationship("ProductCategory", back_populates="products")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Shopping Session", nullable=False)
    active_constraints: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_products: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    citations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    retrieval_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    preferred_categories: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_brands: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    max_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    required_specs: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="preferences")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(120), default="ShopMind Ground-Truth v1", nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    precision_at_k: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recall_at_k: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mrr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hit_rate_at_k: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ndcg_at_k: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    faithfulness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    answer_relevancy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    context_precision: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    context_recall: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    response_correctness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hallucination_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_retrieval_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_generation_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retrieval_success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    thresholds_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    category_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    results: Mapped[List["EvaluationResult"]] = relationship(
        "EvaluationResult", back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_product_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    retrieved_product_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    generated_answer: Mapped[str] = mapped_column(Text, nullable=False)
    precision_at_k: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recall_at_k: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mrr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ndcg_at_k: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hit_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    faithfulness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    answer_relevancy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    context_precision: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    context_recall: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    response_correctness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hallucination_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="results")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    risk_category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)  # OWASP LLM01, LLM02, etc.
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="127.0.0.1", nullable=False)
    payload_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    mitigation_action: Mapped[str] = mapped_column(String(255), nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)  # CSV, JSON, MANUAL, API
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ingested_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_duplicates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
