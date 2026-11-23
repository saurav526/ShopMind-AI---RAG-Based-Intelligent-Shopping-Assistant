"""Pydantic request and response schemas for ShopMind AI REST APIs."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth Schemas ---
class UserRegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Product Schemas ---
class ProductCreateRequest(BaseModel):
    product_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=255)
    brand: str = Field(..., min_length=1, max_length=120)
    category: str = Field(..., min_length=2, max_length=120)
    description: str = Field(..., min_length=10)
    price: float = Field(..., ge=0)
    discount: float = Field(default=0.0, ge=0, le=95)
    rating: float = Field(default=4.2, ge=0, le=5.0)
    review_count: int = Field(default=0, ge=0)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)
    availability: str = Field(default="In Stock")
    image_url: str = Field(default="")
    product_url: str = Field(default="")
    product_metadata: Dict[str, Any] = Field(default_factory=dict)


class ProductResponse(BaseModel):
    id: int
    product_id: str
    name: str
    brand: str
    category: str
    description: str
    price: float
    discount: float
    rating: float
    review_count: int
    specifications: Dict[str, Any]
    features: List[str]
    availability: str
    image_url: str
    product_url: str
    product_metadata: Dict[str, Any]
    is_indexed: bool

    model_config = ConfigDict(from_attributes=True)


class ProductCompareRequest(BaseModel):
    product_ids: List[str] = Field(..., min_length=2, max_length=4)
    focus_criteria: Optional[List[str]] = None


class ProductRecommendRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    max_budget: Optional[float] = None
    min_rating: Optional[float] = 0.0
    required_specs: Optional[Dict[str, Any]] = None
    similar_to_product_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


# --- RAG & Chat Schemas ---
class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = None
    brand: Optional[str] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    use_reranker: bool = True


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class RecommendedProductCard(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    description: str = ""
    price: float
    discount: float
    rating: float
    review_count: int
    specifications: Dict[str, Any]
    features: List[str]
    availability: str
    image_url: str
    product_url: str
    why_recommended: str
    relevance_score: float


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    intent: str
    extracted_constraints: Dict[str, Any]
    rewritten_query: str
    recommended_products: List[RecommendedProductCard]
    comparison_table: Optional[List[Dict[str, Any]]] = None
    citations: List[Dict[str, Any]]
    confidence_score: float
    grounding_verified: bool
    security_status: Dict[str, Any]
    latency_ms: float
    llm_provider: str


# --- Evaluation Schemas ---
class EvaluationRunRequest(BaseModel):
    sample_size: Optional[int] = Field(default=None, ge=5, le=200)
    top_k: int = Field(default=5, ge=1, le=10)
    thresholds: Optional[Dict[str, float]] = None
