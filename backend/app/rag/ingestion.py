"""Product data ingestion pipeline supporting CSV, JSON, Manual Admin Entry, and Public Product APIs."""
# This module implements a robust product data ingestion pipeline for the ShopMind AI application. It supports multiple input formats, including CSV files, JSON files, manual admin entry, and public product APIs. The module provides functions to clean, validate, and normalize product records, ensuring data integrity and security against indirect prompt injection attacks. It also handles duplicate detection, category management, and database interactions using SQLAlchemy ORM models. The ingestion process is logged with detailed error reporting and job tracking for auditing and monitoring purposes.

import csv
import io
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import logger, settings
from app.models.models import IngestionJob, Product, ProductCategory
from app.security.guardrails import AISecurityGuard

ALLOWED_EXTENSIONS = {".csv", ".json"}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "general"


def clean_and_validate_product_record(raw: Dict[str, Any], index: int = 0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Cleans, normalizes, sanitizes untrusted descriptions, and validates a product record."""
    name = str(raw.get("name") or raw.get("product_name") or "").strip()
    if not name or len(name) < 2:
        return None, f"Row {index}: Missing or invalid product name."

    brand = str(raw.get("brand") or "Generic").strip()
    category = str(raw.get("category") or "Electronics").strip()
    description_raw = str(raw.get("description") or f"{brand} {name} in {category}").strip()

    product_id = str(raw.get("product_id") or "").strip()
    if not product_id:
        prefix = re.sub(r"[^A-Z]", "", category.upper())[:3] or "PRD"
        product_id = f"PROD-{prefix}-{uuid.uuid4().hex[:6].upper()}"

    # Sanitize untrusted description against indirect prompt injection
    clean_description, _ = AISecurityGuard.sanitize_untrusted_document(description_raw, source_id=product_id)

    # Validate price
    try:
        raw_price = str(raw.get("price", "")).replace("₹", "").replace(",", "").strip()
        price = float(raw_price)
        if price < 0 or price > 10_000_000:
            return None, f"Row {index} ({product_id}): Invalid price {price}."
    except Exception:
        return None, f"Row {index} ({product_id}): Non-numeric price '{raw.get('price')}'."

    # Discount, Rating, Review Count
    try:
        discount = max(0.0, min(95.0, float(raw.get("discount") or 0.0)))
    except Exception:
        discount = 0.0

    try:
        rating = float(raw.get("rating") or 4.0)
        rating = max(0.0, min(5.0, rating))
    except Exception:
        rating = 4.0

    try:
        review_count = max(0, int(float(raw.get("review_count") or 0)))
    except Exception:
        review_count = 0

    # Parse JSON or dict specifications
    specs_raw = raw.get("specifications") or {}
    if isinstance(specs_raw, str):
        try:
            specifications = json.loads(specs_raw) if specs_raw.strip() else {}
        except Exception:
            # Parse key:value pairs separated by semicolons
            specifications = {}
            for part in specs_raw.split(";"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    specifications[k.strip().lower()] = v.strip()
    elif isinstance(specs_raw, dict):
        specifications = specs_raw
    else:
        specifications = {}

    # Sanitize specification values
    normalized_specs: Dict[str, Any] = {}
    for k, v in specifications.items():
        clean_k = str(k).strip().lower()
        clean_v, _ = AISecurityGuard.sanitize_untrusted_document(str(v).strip(), source_id=product_id)
        normalized_specs[clean_k] = clean_v

    # Parse features list
    features_raw = raw.get("features") or []
    if isinstance(features_raw, str):
        try:
            features = json.loads(features_raw) if features_raw.strip().startswith("[") else [
                f.strip() for f in features_raw.split(",") if f.strip()
            ]
        except Exception:
            features = [f.strip() for f in features_raw.split(",") if f.strip()]
    elif isinstance(features_raw, list):
        features = [str(f).strip() for f in features_raw if str(f).strip()]
    else:
        features = []

    # Parse metadata
    meta_raw = raw.get("product_metadata") or raw.get("metadata") or {}
    if isinstance(meta_raw, str):
        try:
            product_metadata = json.loads(meta_raw) if meta_raw.strip() else {}
        except Exception:
            product_metadata = {}
    elif isinstance(meta_raw, dict):
        product_metadata = meta_raw
    else:
        product_metadata = {}

    availability = str(raw.get("availability") or "In Stock").strip()
    image_url = str(raw.get("image_url") or raw.get("product_image") or "").strip()
    product_url = str(raw.get("product_url") or f"https://shopmind.example.com/products/{product_id}").strip()

    return {
        "product_id": product_id,
        "name": name,
        "brand": brand,
        "category": category,
        "description": clean_description,
        "price": round(price, 2),
        "discount": round(discount, 2),
        "rating": round(rating, 2),
        "review_count": review_count,
        "specifications": normalized_specs,
        "features": features,
        "availability": availability,
        "image_url": image_url,
        "product_url": product_url,
        "product_metadata": product_metadata,
    }, None


def ingest_product_records(
    db: Session,
    records: List[Dict[str, Any]],
    source_type: str = "CSV",
    filename: str = "sample_products.csv",
    update_existing: bool = True,
) -> Dict[str, Any]:
    """Ingests a batch of product dictionaries into the relational database with duplicate detection."""
    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
    ingested_count = 0
    updated_count = 0
    skipped_duplicates = 0
    failed_count = 0
    error_details: List[Dict[str, Any]] = []

    seen_batch_keys = set()
    category_cache: Dict[str, ProductCategory] = {
        c.name.lower(): c for c in db.query(ProductCategory).all()
    }

    for idx, raw in enumerate(records, start=1):
        cleaned, err = clean_and_validate_product_record(raw, index=idx)
        if err or not cleaned:
            failed_count += 1
            error_details.append({"row": idx, "error": err or "Validation failed"})
            continue

        dedup_key = (cleaned["product_id"].lower(), cleaned["name"].lower())
        if dedup_key in seen_batch_keys:
            skipped_duplicates += 1
            continue
        seen_batch_keys.add(dedup_key)

        cat_key = cleaned["category"].lower()
        cat_obj = category_cache.get(cat_key)
        if not cat_obj:
            cat_obj = ProductCategory(
                name=cleaned["category"],
                slug=_slugify(cleaned["category"]),
                description=f"{cleaned['category']} catalog section",
            )
            db.add(cat_obj)
            db.flush()
            category_cache[cat_key] = cat_obj

        existing = (
            db.query(Product)
            .filter((Product.product_id == cleaned["product_id"]) | (Product.name == cleaned["name"]))
            .first()
        )
        if existing:
            if update_existing:
                for k, v in cleaned.items():
                    setattr(existing, k, v)
                existing.category_id = cat_obj.id
                existing.is_indexed = True
                updated_count += 1
            else:
                skipped_duplicates += 1
        else:
            new_prod = Product(
                **cleaned,
                category_id=cat_obj.id,
                is_indexed=True,
            )
            db.add(new_prod)
            ingested_count += 1

    job = IngestionJob(
        job_id=job_id,
        source_type=source_type,
        filename=filename,
        total_records=len(records),
        ingested_count=ingested_count,
        updated_count=updated_count,
        skipped_duplicates=skipped_duplicates,
        failed_count=failed_count,
        error_details=error_details,
        status="COMPLETED" if failed_count < len(records) else "FAILED",
    )
    db.add(job)
    db.commit()

    return {
        "job_id": job_id,
        "source_type": source_type,
        "filename": filename,
        "total_records": len(records),
        "ingested_count": ingested_count,
        "updated_count": updated_count,
        "skipped_duplicates": skipped_duplicates,
        "failed_count": failed_count,
        "error_details": error_details,
        "status": job.status,
    }


def ingest_from_csv_path(db: Session, csv_path: Path) -> Dict[str, Any]:
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)
    return ingest_product_records(db, records, source_type="CSV", filename=csv_path.name)


def validate_and_parse_upload(filename: str, content_bytes: bytes) -> Tuple[List[Dict[str, Any]], str]:
    """Validates file extension, file size, and structure for uploaded CSV or JSON datasets."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Only .csv and .json product files are allowed.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content_bytes) > max_bytes:
        raise ValueError(f"Uploaded file exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB.")

    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Uploaded file must be valid UTF-8 encoded text.")

    if ext == ".csv":
        reader = csv.DictReader(io.StringIO(text))
        records = list(reader)
        return records, "CSV"
    else:
        payload = json.loads(text)
        if isinstance(payload, dict) and "products" in payload:
            records = payload["products"]
        elif isinstance(payload, list):
            records = payload
        else:
            raise ValueError("JSON upload must be a list of product objects or {'products': [...]}.")
        return records, "JSON"
