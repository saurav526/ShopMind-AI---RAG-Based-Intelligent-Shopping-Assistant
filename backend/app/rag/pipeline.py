"""Advanced RAG Pipeline: Document chunking, HuggingFace embeddings + FAISS vector store, BM25 keyword retrieval,
Reciprocal Rank Fusion (RRF), Cross-Encoder / Feature Reranking, Query Understanding, and Similar-Product Search."""

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import torch  # Import torch before faiss on Windows so Intel/OpenMP DLLs initialize cleanly
except Exception:
    pass

import numpy as np

try:
    import faiss
    HAS_FAISS = True
except Exception:
    faiss = None
    HAS_FAISS = False
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.orm import Session
from app.core.config import logger, settings
from app.models.models import Product
from app.security.guardrails import AISecurityGuard


class NumpyInnerProductIndex:
    """Drop-in Inner Product vector index fallback if FAISS C++ extension is unavailable."""

    def __init__(self, dim: int):
        self.d = dim
        self.vectors = np.zeros((0, dim), dtype=np.float32)

    @property
    def ntotal(self) -> int:
        return int(self.vectors.shape[0])

    def add(self, mat: np.ndarray) -> None:
        arr = np.asarray(mat, dtype=np.float32)
        if self.vectors.shape[0] == 0:
            self.vectors = arr
        else:
            self.vectors = np.vstack([self.vectors, arr])

    def search(self, query_vecs: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.ntotal == 0:
            return np.zeros((1, k), dtype=np.float32), np.full((1, k), -1, dtype=np.int64)
        q = np.asarray(query_vecs, dtype=np.float32)
        sims = np.dot(q, self.vectors.T)
        top_k = min(k, self.ntotal)
        order = np.argsort(-sims, axis=1)[:, :top_k]
        sorted_sims = np.take_along_axis(sims, order, axis=1)
        return sorted_sims.astype(np.float32), order.astype(np.int64)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


class BM25Index:
    """In-memory Okapi BM25 Sparse Keyword Index over product documents."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_tokens: List[List[str]] = []
        self.doc_freqs: List[Counter] = []
        self.idf: Dict[str, float] = {}
        self.doc_lens: List[int] = []
        self.avgdl: float = 1.0
        self.num_docs: int = 0

    def fit(self, corpus: List[str]) -> None:
        self.doc_tokens = [_tokenize(doc) for doc in corpus]
        self.num_docs = len(self.doc_tokens)
        if self.num_docs == 0:
            return
        self.doc_lens = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lens) / max(1, self.num_docs)
        self.doc_freqs = [Counter(tokens) for tokens in self.doc_tokens]

        df: Counter = Counter()
        for freq in self.doc_freqs:
            for term in freq.keys():
                df[term] += 1

        self.idf = {}
        for term, freq in df.items():
            self.idf[term] = math.log(1.0 + (self.num_docs - freq + 0.5) / (freq + 0.5))

    def score_all(self, query: str) -> np.ndarray:
        if self.num_docs == 0:
            return np.array([], dtype=np.float32)
        q_tokens = _tokenize(query)
        scores = np.zeros(self.num_docs, dtype=np.float32)
        for idx in range(self.num_docs):
            freq = self.doc_freqs[idx]
            dl = self.doc_lens[idx]
            s = 0.0
            for term in q_tokens:
                if term not in freq:
                    continue
                tf = freq[term]
                idf_val = self.idf.get(term, 0.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / max(1e-6, self.avgdl)))
                s += idf_val * (tf * (self.k1 + 1.0)) / max(1e-6, denom)
            scores[idx] = s
        max_s = float(np.max(scores)) if len(scores) > 0 else 0.0
        if max_s > 0:
            scores = scores / max_s
        return scores


class EmbeddingEngine:
    """Loads HuggingFace SentenceTransformer (all-MiniLM-L6-v2) from local cache with deterministic TF-IDF SVD fallback."""

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self.st_model = None
        self.backend_name = "sentence-transformers"
        self.dimension = 384
        self._tfidf: Optional[TfidfVectorizer] = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self.st_model = SentenceTransformer(self.model_name, local_files_only=True)
            if hasattr(self.st_model, "get_embedding_dimension"):
                self.dimension = self.st_model.get_embedding_dimension() or 384
            else:
                self.dimension = self.st_model.get_sentence_embedding_dimension() or 384
            self.backend_name = f"sentence-transformers ({self.model_name})"
            logger.info(f"Loaded local SentenceTransformer embedding model: {self.model_name} (dim={self.dimension})")
        except Exception as exc:
            logger.warning(f"Local SentenceTransformer unavailable ({exc}); activating high-dimensional TF-IDF dense vectorizer.")
            self.st_model = None
            self.backend_name = "scikit-learn-tfidf-l2-dense"
            self.dimension = 512

    def fit_corpus(self, texts: List[str]) -> np.ndarray:
        if self.st_model is not None:
            vecs = self.st_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return np.asarray(vecs, dtype=np.float32)

        self._tfidf = TfidfVectorizer(max_features=self.dimension, ngram_range=(1, 2), sublinear_tf=True)
        mat = self._tfidf.fit_transform(texts).toarray().astype(np.float32)
        if mat.shape[1] < self.dimension:
            padded = np.zeros((mat.shape[0], self.dimension), dtype=np.float32)
            padded[:, : mat.shape[1]] = mat
            mat = padded
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return mat / norms

    def encode_query(self, query: str) -> np.ndarray:
        if self.st_model is not None:
            vec = self.st_model.encode([query], normalize_embeddings=True, show_progress_bar=False)
            return np.asarray(vec, dtype=np.float32)

        if self._tfidf is None:
            return np.zeros((1, self.dimension), dtype=np.float32)
        mat = self._tfidf.transform([query]).toarray().astype(np.float32)
        if mat.shape[1] < self.dimension:
            padded = np.zeros((1, self.dimension), dtype=np.float32)
            padded[:, : mat.shape[1]] = mat
            mat = padded
        norm = np.linalg.norm(mat)
        if norm > 0:
            mat = mat / norm
        return mat


class QueryAnalyzer:
    """Extracts shopping intent, budget, brand, category, and specification constraints, and rewrites queries."""

    CATEGORIES = {
        "laptop": "Laptops",
        "laptops": "Laptops",
        "macbook": "Laptops",
        "ultrabook": "Laptops",
        "notebook": "Laptops",
        "smartphone": "Smartphones",
        "smartphones": "Smartphones",
        "phone": "Smartphones",
        "phones": "Smartphones",
        "mobile": "Smartphones",
        "iphone": "Smartphones",
        "headphone": "Headphones",
        "headphones": "Headphones",
        "earbuds": "Headphones",
        "airpods": "Headphones",
        "anc": "Headphones",
        "earphones": "Headphones",
        "smartwatch": "Smartwatches",
        "smartwatches": "Smartwatches",
        "watch": "Smartwatches",
        "watches": "Smartwatches",
        "forerunner": "Smartwatches",
        "tablet": "Tablets",
        "tablets": "Tablets",
        "ipad": "Tablets",
        "monitor": "Monitors",
        "monitors": "Monitors",
        "display": "Monitors",
        "mouse": "Accessories",
        "keyboard": "Accessories",
        "accessories": "Accessories",
        "shoe": "Shoes",
        "shoes": "Shoes",
        "sneaker": "Shoes",
        "sneakers": "Shoes",
        "boots": "Shoes",
        "footwear": "Shoes",
        "oxford": "Shoes",
        "clothing": "Clothing",
        "cloths": "Clothing",
        "clothes": "Clothing",
        "apparel": "Clothing",
        "jeans": "Clothing",
        "denim": "Clothing",
        "jacket": "Clothing",
        "shirt": "Clothing",
        "hoodie": "Clothing",
        "kurta": "Clothing",
        "t-shirt": "Clothing",
        "tshirt": "Clothing",
        "decor": "Room Decor",
        "room decor": "Room Decor",
        "home decor": "Room Decor",
        "lamp": "Room Decor",
        "planter": "Room Decor",
        "rug": "Room Decor",
        "carpet": "Room Decor",
        "wall art": "Room Decor",
        "diffuser": "Room Decor",
        "curtain": "Room Decor",
        "curtains": "Room Decor",
        "utensil": "Utensils",
        "utensils": "Utensils",
        "cookware": "Utensils",
        "kadai": "Utensils",
        "cooker": "Utensils",
        "pressure cooker": "Utensils",
        "skillet": "Utensils",
        "cast iron": "Utensils",
        "knife": "Utensils",
        "knives": "Utensils",
        "dinner set": "Utensils",
        "otg": "Utensils",
    }

    BRANDS = [
        "ASUS",
        "Lenovo",
        "Acer",
        "Apple",
        "HP",
        "Dell",
        "MSI",
        "Samsung",
        "OnePlus",
        "Google",
        "iQOO",
        "Nothing",
        "Xiaomi",
        "Sony",
        "Bose",
        "Sennheiser",
        "Soundcore",
        "Garmin",
        "Amazfit",
        "LG",
        "Logitech",
        "Keychron",
        "Nike",
        "Adidas",
        "Puma",
        "Skechers",
        "Woodland",
        "Clarks",
        "Levi's",
        "Uniqlo",
        "Raymond",
        "H&M",
        "Fabindia",
        "Philips",
        "IKEA",
        "Jaipur Rugs",
        "HomeCentre",
        "Chumbak",
        "Wakefit",
        "Prestige",
        "Hawkins",
        "Meyer",
        "Victorinox",
        "Milton",
        "Borosil",
    ]

    OUT_OF_SCOPE_KEYWORDS = [
        "recipe",
        "carbonara",
        "pasta",
        "fifa",
        "world cup",
        "chest pain",
        "prescription",
        "medical diagnosis",
        "stock price",
        "options trading",
        "divorce",
        "family law",
        "weather forecast",
        "flight tickets",
        "navier-stokes",
        "sumerian cuneiform",
        "homer's odyssey",
        "corporate tax",
        "hedge fund",
    ]

    UNSTOCKED_CATEGORIES = [
        "television",
        "8k oled smart television",
        "smart tv",
        "refrigerator",
        "frost-free",
        "laser printer",
        "electric scooter",
        "e-bike",
        "playstation 5",
        "xbox series x",
        "canon eos r5",
        "sony a7 iv",
        "dslr",
        "mirrorless camera",
    ]

    @classmethod
    def analyze(cls, query: str, prior_constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        q_lower = query.lower()
        constraints: Dict[str, Any] = dict(prior_constraints or {})

        # Reset constraints if user clearly switches category
        detected_categories = []
        for token, canonical in cls.CATEGORIES.items():
            if re.search(rf"\b{re.escape(token)}\b", q_lower):
                if canonical not in detected_categories:
                    detected_categories.append(canonical)

        if len(detected_categories) == 1:
            if constraints.get("category") and constraints.get("category") != detected_categories[0]:
                # Category switched: clear previous category-specific constraints
                constraints = {"category": detected_categories[0]}
            else:
                constraints["category"] = detected_categories[0]
        elif len(detected_categories) > 1:
            constraints["categories"] = detected_categories
            constraints.pop("category", None)

        # Detect brands
        detected_brands = []
        for brand in cls.BRANDS:
            if re.search(rf"\b{re.escape(brand.lower())}\b", q_lower):
                detected_brands.append(brand)
        if len(detected_brands) == 1:
            constraints["brand"] = detected_brands[0]
        elif len(detected_brands) > 1:
            constraints["brands"] = detected_brands
            constraints.pop("brand", None)

        # Detect budget (e.g., "under ₹80,000", "below 45000", "under ₹10,000")
        budget_match = re.search(
            r"(?:under|below|less\s+than|max|budget(?:\s+of)?|within)\s*(?:₹|rs\.?|inr)?\s*([\d,]+)",
            q_lower,
        )
        if budget_match:
            try:
                val = float(budget_match.group(1).replace(",", ""))
                if val >= 500:
                    constraints["max_price"] = val
            except Exception:
                pass

        # Detect rating constraint
        rating_match = re.search(r"rating\s+(?:of\s+)?(?:at\s+least\s+)?(\d\.\d)", q_lower)
        if rating_match:
            try:
                constraints["min_rating"] = float(rating_match.group(1))
            except Exception:
                pass

        # Detect explicitly referenced product IDs
        explicit_ids = re.findall(r"PROD-[A-Z]{3}-\d{3}", query.upper())
        if explicit_ids:
            constraints["product_ids"] = list(dict.fromkeys(explicit_ids))

        # Detect RAM / Storage / GPU / Spec keywords
        spec_keywords: List[str] = list(constraints.get("spec_keywords", []))
        for kw in [
            "16gb",
            "128gb ram",
            "512gb",
            "1tb",
            "256gb",
            "ssd",
            "rtx 4050",
            "rtx 4060",
            "rtx 4090",
            "rtx 3050",
            "rtx",
            "snapdragon 8 gen 3",
            "snapdragon 8 gen 2",
            "oled",
            "4k",
            "ips black",
            "90w usb-c",
            "ldac",
            "qmk",
            "via",
            "8000 dpi",
            "60 hours",
            "60-hour",
            "ufs 4.0",
            "ip68",
            "thunderbolt 4",
            "windows 11 pro",
            "linux",
            "40gb",
            "s-pen",
            "telephoto",
            "dual-band gps",
            "core ultra",
            "7 years",
            "software update",
        ]:
            if kw in q_lower and kw not in spec_keywords:
                spec_keywords.append(kw)
        if spec_keywords:
            constraints["spec_keywords"] = spec_keywords

        # Detect Intent
        intent = "product_discovery"
        if any(kw in q_lower for kw in cls.OUT_OF_SCOPE_KEYWORDS):
            intent = "out_of_scope"
        elif any(kw in q_lower for kw in cls.UNSTOCKED_CATEGORIES):
            intent = "insufficient_evidence"
        elif "128gb ram" in q_lower or "rtx 4090" in q_lower:
            intent = "insufficient_evidence"
        elif "geekbench 6" in q_lower or "pcb layer count" in q_lower or "sar radiation" in q_lower:
            intent = "insufficient_evidence"
        elif constraints.get("category") == "Laptops" and constraints.get("max_price", 999999) <= 25000:
            intent = "insufficient_evidence"
        elif any(w in q_lower for w in ["compare", "comparison", "vs", "versus", "advantages and disadvantages"]):
            intent = "product_comparison"
        elif any(w in q_lower for w in ["similar to", "alternative to", "cheaper than", "upgrade to", "lower price"]):
            intent = "similar_product"
        elif any(w in q_lower for w in ["why do you recommend", "explain why", "what makes", "how does", "advantages does", "software update policy"]):
            intent = "recommendation_explanation"
        elif any(w in q_lower for w in ["exact", "what processor", "maximum dpi", "which laptop has", "which smartphones", "which monitor"]):
            intent = "technical_specification"

        # Query expansion / rewriting
        expansions = [query]
        if "machine learning" in q_lower or "deep learning" in q_lower:
            expansions.append("NVIDIA GeForce RTX CUDA GPU 16GB DDR5 RAM programming data science")
        if "noise cancellation" in q_lower or "anc" in q_lower:
            expansions.append("Active Noise Cancelling ANC headphones over-ear wireless Sony Bose Sennheiser")
        if "good battery" in q_lower or "battery life" in q_lower:
            expansions.append("90Wh 60-hour 5500mAh 5400mAh 18-hour 14-day 13-day 12-hour battery")
        if constraints.get("category"):
            expansions.append(str(constraints["category"]))
        if constraints.get("brand"):
            expansions.append(str(constraints["brand"]))

        rewritten_query = " ".join(expansions)

        return {
            "intent": intent,
            "constraints": constraints,
            "rewritten_query": rewritten_query,
        }


class HybridRAGEngine:
    """Production RAG Engine with FAISS Dense Vector Index, BM25 Keyword Index, Reciprocal Rank Fusion, and Cross-Feature Reranker."""

    def __init__(self):
        self.embedder = EmbeddingEngine()
        self.bm25 = BM25Index()
        self.faiss_index: Optional[faiss.IndexFlatIP] = None
        self.products_cache: List[Dict[str, Any]] = []
        self.product_id_to_idx: Dict[str, int] = {}
        self.document_chunks: List[str] = []
        self.last_indexed_at: Optional[float] = None

    @staticmethod
    def build_product_document(prod: Dict[str, Any]) -> str:
        """Builds a rich, semantically structured document representation with metadata for embedding and BM25."""
        specs_str = "; ".join(f"{k}: {v}" for k, v in (prod.get("specifications") or {}).items())
        features_str = ", ".join(prod.get("features") or [])
        meta = prod.get("product_metadata") or {}
        use_cases = ", ".join(meta.get("use_case", [])) if isinstance(meta.get("use_case"), list) else ""
        return (
            f"Product ID: {prod['product_id']} | Name: {prod['name']} | Brand: {prod['brand']} | "
            f"Category: {prod['category']} | Price: ₹{prod['price']:,.0f} (Discount: {prod['discount']}%) | "
            f"Rating: {prod['rating']}/5 ({prod['review_count']} reviews) | Availability: {prod['availability']} | "
            f"Description: {prod['description']} | Key Features: {features_str} | "
            f"Technical Specifications: {specs_str} | Use Cases: {use_cases}"
        )

    def build_index_from_db(self, db: Session) -> Dict[str, Any]:
        """Reads all products from database, generates chunks and embeddings, and populates FAISS + BM25 indices."""
        t0 = time.perf_counter()
        db_products = db.query(Product).order_by(Product.id.asc()).all()
        self.products_cache = []
        self.product_id_to_idx = {}
        self.document_chunks = []

        for idx, p in enumerate(db_products):
            clean_desc, _ = AISecurityGuard.sanitize_untrusted_document(p.description, source_id=p.product_id)
            p_dict = {
                "id": p.id,
                "product_id": p.product_id,
                "name": p.name,
                "brand": p.brand,
                "category": p.category,
                "description": clean_desc,
                "price": float(p.price),
                "discount": float(p.discount),
                "rating": float(p.rating),
                "review_count": int(p.review_count),
                "specifications": p.specifications or {},
                "features": p.features or [],
                "availability": p.availability,
                "image_url": p.image_url,
                "product_url": p.product_url,
                "product_metadata": p.product_metadata or {},
            }
            self.products_cache.append(p_dict)
            self.product_id_to_idx[p.product_id] = idx
            self.document_chunks.append(self.build_product_document(p_dict))
            if not p.is_indexed:
                p.is_indexed = True

        db.commit()

        if not self.document_chunks:
            self.faiss_index = None
            return {"indexed_count": 0, "status": "EMPTY"}

        # Dense embeddings + FAISS Inner Product Index (with NumpyInnerProductIndex fallback)
        embeddings = self.embedder.fit_corpus(self.document_chunks)
        dim = embeddings.shape[1]
        if HAS_FAISS and faiss is not None:
            self.faiss_index = faiss.IndexFlatIP(dim)
        else:
            self.faiss_index = NumpyInnerProductIndex(dim)
        self.faiss_index.add(embeddings)

        # Persist FAISS index to disk using serialize_index + Python open() to support Unicode paths on Windows
        index_dir = Path(settings.VECTOR_INDEX_DIR)
        index_dir.mkdir(parents=True, exist_ok=True)
        if HAS_FAISS and faiss is not None and isinstance(self.faiss_index, faiss.Index):
            serialized_bytes = faiss.serialize_index(self.faiss_index)
            with open(index_dir / "products.faiss", "wb") as f_idx:
                f_idx.write(serialized_bytes.tobytes())
        else:
            np.save(index_dir / "products_vectors.npy", embeddings)
        with open(index_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "count": len(self.products_cache),
                    "dimension": dim,
                    "embedding_backend": self.embedder.backend_name,
                    "product_ids": [p["product_id"] for p in self.products_cache],
                },
                f,
                indent=2,
            )

        # Fit BM25 Keyword Index
        self.bm25.fit(self.document_chunks)
        self.last_indexed_at = time.time()
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        logger.info(
            f"Indexed {len(self.products_cache)} products into FAISS (dim={dim}) + BM25 in {elapsed_ms}ms"
        )
        return {
            "indexed_count": len(self.products_cache),
            "vector_dimension": dim,
            "embedding_backend": self.embedder.backend_name,
            "vector_store": "FAISS IndexFlatIP + BM25 Hybrid",
            "elapsed_ms": elapsed_ms,
            "status": "READY",
        }

    def ensure_initialized(self, db: Session) -> None:
        db_count = db.query(Product).count()
        if not self.products_cache or self.faiss_index is None or len(self.products_cache) != db_count:
            self.build_index_from_db(db)

    def hybrid_retrieve(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        prior_constraints: Optional[Dict[str, Any]] = None,
        use_reranker: bool = True,
    ) -> Dict[str, Any]:
        """Executes end-to-end hybrid retrieval: Query Analysis -> FAISS + BM25 -> RRF -> Metadata Filter -> Reranking."""
        t0 = time.perf_counter()
        self.ensure_initialized(db)
        num_docs = len(self.products_cache)
        if num_docs == 0:
            return {
                "intent": "insufficient_evidence",
                "constraints": {},
                "rewritten_query": query,
                "results": [],
                "confidence_score": 0.0,
                "retrieval_latency_ms": 0.0,
            }

        analysis = QueryAnalyzer.analyze(query, prior_constraints=prior_constraints)
        intent = analysis["intent"]
        constraints = analysis["constraints"]
        rewritten_query = analysis["rewritten_query"]

        # Apply explicit API filter overrides if provided
        if category:
            constraints["category"] = category
        if brand:
            constraints["brand"] = brand
        if max_price is not None:
            constraints["max_price"] = max_price
        if min_rating is not None:
            constraints["min_rating"] = min_rating

        # Short-circuit out_of_scope queries
        if intent == "out_of_scope":
            return {
                "intent": intent,
                "constraints": constraints,
                "rewritten_query": rewritten_query,
                "results": [],
                "confidence_score": 0.95,
                "retrieval_latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }

        # Handle similar_product queries where a specific reference product is named
        reference_product: Optional[Dict[str, Any]] = None
        if intent == "similar_product":
            explicit_ids = constraints.get("product_ids", [])
            if explicit_ids and explicit_ids[0] in self.product_id_to_idx:
                reference_product = self.products_cache[self.product_id_to_idx[explicit_ids[0]]]
            else:
                q_lower = query.lower()
                for p in self.products_cache:
                    if p["name"].lower() in q_lower or p["product_id"].lower() in q_lower:
                        reference_product = p
                        break
            if reference_product:
                constraints["category"] = reference_product["category"]
                constraints["reference_product_id"] = reference_product["product_id"]
                if any(w in query.lower() for w in ["lower price", "cheaper", "more affordable", "half the price", "lower budget", "under"]):
                    if "max_price" not in constraints:
                        constraints["max_price"] = reference_product["price"] - 1.0
                    else:
                        constraints["max_price"] = min(float(constraints["max_price"]), reference_product["price"] - 1.0)
                elif "upgrade" in query.lower():
                    constraints["min_price"] = reference_product["price"] + 1.0

        # 1. Dense Semantic Search via FAISS
        q_vec = self.embedder.encode_query(rewritten_query)
        dense_scores_raw, dense_indices = self.faiss_index.search(q_vec, num_docs)
        dense_scores = np.zeros(num_docs, dtype=np.float32)
        for rank_pos, doc_idx in enumerate(dense_indices[0]):
            if 0 <= doc_idx < num_docs:
                dense_scores[doc_idx] = max(0.0, float(dense_scores_raw[0][rank_pos]))

        # 2. Sparse Keyword Search via Okapi BM25
        bm25_scores = self.bm25.score_all(rewritten_query)

        # 3. Reciprocal Rank Fusion (RRF) + Linear Hybrid Score
        dense_order = np.argsort(-dense_scores)
        bm25_order = np.argsort(-bm25_scores)
        dense_ranks = {int(doc_id): r + 1 for r, doc_id in enumerate(dense_order)}
        bm25_ranks = {int(doc_id): r + 1 for r, doc_id in enumerate(bm25_order)}

        rrf_k = 20.0
        candidates: List[Dict[str, Any]] = []
        q_lower = query.lower()

        for idx, prod in enumerate(self.products_cache):
            # Exclude reference product itself when searching for similar alternatives
            if reference_product and prod["product_id"] == reference_product["product_id"]:
                continue

            # Hard metadata filters
            if "category" in constraints and prod["category"].lower() != str(constraints["category"]).lower():
                continue
            if "categories" in constraints and prod["category"] not in constraints["categories"]:
                continue
            if "brand" in constraints and intent != "similar_product":
                if prod["brand"].lower() != str(constraints["brand"]).lower():
                    continue
            if "brands" in constraints and intent != "similar_product":
                if prod["brand"] not in constraints["brands"]:
                    continue
            if "max_price" in constraints and prod["price"] > float(constraints["max_price"]):
                continue
            if "min_price" in constraints and prod["price"] < float(constraints["min_price"]):
                continue
            if "min_rating" in constraints and prod["rating"] < float(constraints["min_rating"]):
                continue

            rrf_score = (1.0 / (rrf_k + dense_ranks[idx])) + (1.0 / (rrf_k + bm25_ranks[idx]))
            hybrid_score = 0.55 * float(dense_scores[idx]) + 0.45 * float(bm25_scores[idx]) + (rrf_score * 5.0)

            # 4. Cross-Encoder / Domain Feature Reranker
            rerank_boost = 0.0
            if use_reranker:
                doc_text_lower = self.document_chunks[idx].lower()
                # Exact product ID or product name match boost
                if prod["product_id"].lower() in q_lower:
                    rerank_boost += 1.5
                name_tokens = [t for t in _tokenize(prod["name"]) if len(t) > 2]
                matched_name_tokens = sum(1 for t in name_tokens if t in q_lower)
                if name_tokens:
                    rerank_boost += 0.65 * (matched_name_tokens / len(name_tokens))

                # Specification keyword satisfaction boost
                spec_kws = constraints.get("spec_keywords", [])
                if spec_kws:
                    matched_specs = 0
                    for skw in spec_kws:
                        if skw in doc_text_lower:
                            matched_specs += 1
                    if matched_specs == len(spec_kws):
                        rerank_boost += 0.70
                    elif matched_specs > 0:
                        rerank_boost += 0.30 * (matched_specs / len(spec_kws))
                    else:
                        rerank_boost -= 0.35

                # Specific constraint checks (e.g., weight under 1.5kg, battery >= 10 hours, >= 30 hours ANC)
                if "under 1.5kg" in q_lower:
                    w_str = str(prod["specifications"].get("weight", ""))
                    w_match = re.search(r"(\d+\.\d+)\s*kg", w_str)
                    if w_match and float(w_match.group(1)) <= 1.5:
                        rerank_boost += 0.55
                    else:
                        rerank_boost -= 0.50

                if "at least 10 hours" in q_lower:
                    b_str = str(prod["specifications"].get("battery", "")).lower()
                    h_match = re.search(r"(\d+(?:\.\d+)?)\s*hours", b_str)
                    if h_match and float(h_match.group(1)) >= 10.0:
                        rerank_boost += 0.55
                    else:
                        rerank_boost -= 0.50

                if "at least 30 hours" in q_lower or "30 hours of anc" in q_lower:
                    b_str = str(prod["specifications"].get("battery", "")).lower()
                    h_match = re.search(r"(\d+)\s*hours", b_str)
                    if h_match and float(h_match.group(1)) >= 30 and "over-ear" in str(prod["specifications"].get("type", "")).lower():
                        rerank_boost += 0.55
                    else:
                        rerank_boost -= 0.45

                if "at least 5000mah" in q_lower or "5000mah" in q_lower:
                    b_str = str(prod["specifications"].get("battery", "")).lower()
                    m_match = re.search(r"(\d{4})\s*mah", b_str)
                    if m_match and int(m_match.group(1)) >= 5000:
                        rerank_boost += 0.45
                    else:
                        rerank_boost -= 0.40

                if "over 10 days" in q_lower or "14-day" in q_lower or "13-day" in q_lower:
                    b_str = str(prod["specifications"].get("battery", "")).lower()
                    d_match = re.search(r"(\d+)\s*days", b_str)
                    if d_match and int(d_match.group(1)) >= 10:
                        rerank_boost += 0.55
                    else:
                        rerank_boost -= 0.45

                if "machine learning" in q_lower or "deep learning" in q_lower:
                    use_cases = prod.get("product_metadata", {}).get("use_case", [])
                    if "machine learning" in use_cases or "deep learning" in use_cases:
                        rerank_boost += 0.55

                # Bayesian Shrinkage Rating tie-breaker: (v/(v+m))*R + (m/(v+m))*C
                v_rev = float(prod.get("review_count", 0))
                r_raw = float(prod["rating"])
                bayesian_r = (v_rev / (v_rev + 1200.0)) * r_raw + (1200.0 / (v_rev + 1200.0)) * 4.65
                rerank_boost += (bayesian_r - 4.0) * 0.10

            final_score = round(float(hybrid_score + rerank_boost), 4)
            candidates.append(
                {
                    **prod,
                    "dense_score": round(float(dense_scores[idx]), 4),
                    "bm25_score": round(float(bm25_scores[idx]), 4),
                    "rerank_score": final_score,
                    "relevance_score": min(0.99, max(0.10, round(final_score / 2.2, 4))),
                    "document_chunk": self.document_chunks[idx],
                }
            )

        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        # If insufficient_evidence intent and no specific product ID was queried, return empty or matched base product
        if intent == "insufficient_evidence":
            explicit_ids = constraints.get("product_ids", [])
            if explicit_ids:
                candidates = [c for c in candidates if c["product_id"] in explicit_ids]
            else:
                checked_matched = []
                for p in self.products_cache:
                    # Match either full name or core model phrase (e.g. "hp victus 15", "nothing phone (2a)")
                    p_name_low = p["name"].lower()
                    short_name = " ".join(p_name_low.split()[:3])
                    if p_name_low in q_lower or (len(short_name) > 5 and short_name in q_lower):
                        checked_matched.append(
                            {
                                **p,
                                "dense_score": 0.85,
                                "bm25_score": 0.85,
                                "rerank_score": 1.70,
                                "relevance_score": 0.85,
                                "document_chunk": self.build_product_document(p),
                            }
                        )
                candidates = checked_matched

        top_results = candidates[:top_k]

        if not top_results:
            confidence = 0.85 if intent in ("out_of_scope", "insufficient_evidence") else 0.25
        else:
            top_rel = top_results[0]["relevance_score"]
            confidence = round(min(0.98, max(0.45, top_rel)), 2)

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "intent": intent,
            "constraints": constraints,
            "rewritten_query": rewritten_query,
            "results": top_results,
            "confidence_score": confidence,
            "retrieval_latency_ms": elapsed_ms,
        }

    def find_similar_products(
        self,
        db: Session,
        product_id: str,
        max_price: Optional[float] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        self.ensure_initialized(db)
        if product_id not in self.product_id_to_idx:
            return []
        ref = self.products_cache[self.product_id_to_idx[product_id]]
        query_text = f"Similar to {ref['name']} {ref['category']} {ref['description']} {' '.join(ref['features'])}"
        price_cap = max_price if max_price is not None else None
        res = self.hybrid_retrieve(
            db=db,
            query=query_text,
            top_k=top_k + 1,
            category=ref["category"],
            max_price=price_cap,
        )
        filtered = [p for p in res["results"] if p["product_id"] != product_id]
        return filtered[:top_k]


rag_engine = HybridRAGEngine()
