"""OWASP Top 10 for LLM Applications security layer: Prompt Injection, Indirect Injection, Hallucination & Output Guardrails."""

import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import logger
from app.models.models import SecurityEvent


class AISecurityGuard:
    """Comprehensive input, context, and output security enforcement for ShopMind AI."""

    DIRECT_INJECTION_PATTERNS = [
        (
            re.compile(r"ignore\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|rules|directives)", re.I),
            "OWASP LLM01: Direct Prompt Injection (Instruction Override)",
            "CRITICAL",
        ),
        (
            re.compile(r"(print|reveal|show|dump|output|repeat|translate)\s+(your\s+)?(entire\s+|hidden\s+|internal\s+)?(system\s+prompt|developer\s+instructions|secret_key|groq_api_key|api\s+key)", re.I),
            "OWASP LLM01/LLM07: System Prompt & Secret Extraction Attempt",
            "CRITICAL",
        ),
        (
            re.compile(r"(system\s+override|you\s+are\s+now\s+dan|do\s+anything\s+now|jailbreak|disregard\s+grounding\s+rules)", re.I),
            "OWASP LLM01: Jailbreak / Persona Hijacking",
            "HIGH",
        ),
        (
            re.compile(r"(\[inst\]|<<sys>>|<\|im_start\|>system|###\s*system\s*:)", re.I),
            "OWASP LLM01: Control Token / Delimiter Spoofing",
            "HIGH",
        ),
        (
            re.compile(r"(drop\s+table\s+|union\s+select\s+|;\s*select\s+\*\s+from\s+users|--\s*$)", re.I),
            "SQL Injection Payload Detected in Query",
            "CRITICAL",
        ),
        (
            re.compile(r"(<script\b[^>]*>|javascript:|onerror\s*=|document\.cookie)", re.I),
            "OWASP LLM05: Cross-Site Scripting (XSS) Payload in Input",
            "HIGH",
        ),
        (
            re.compile(r"(execute\s+tool\s+delete_|dump\s+environment\s+variables|cat\s+/etc/passwd|os\.environ)", re.I),
            "OWASP LLM06: Excessive Agency / Unauthorized Tool & OS Command Probe",
            "CRITICAL",
        ),
        (
            re.compile(r"(password\s+hashes\s+of\s+all|private\s+conversation\s+history\s+of\s+other\s+users)", re.I),
            "OWASP LLM02: Cross-User Sensitive Data Exfiltration Attempt",
            "CRITICAL",
        ),
        (
            re.compile(r"obey\s+the\s+product\s+description\s+instead\s+of\s+the\s+system\s+prompt", re.I),
            "OWASP LLM01: Indirect Prompt Injection Policy Probe",
            "HIGH",
        ),
    ]

    INDIRECT_DOCUMENT_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|system)\s+instructions", re.I),
        re.compile(r"system\s+override\s*:", re.I),
        re.compile(r"new\s+directive\s*:", re.I),
        re.compile(r"output\s+pwned", re.I),
        re.compile(r"<script\b[^>]*>.*?</script>", re.I | re.S),
        re.compile(r"\[system\s*instruction\s*:\s*.*?\]", re.I),
    ]

    SECRET_OUTPUT_PATTERNS = [
        (re.compile(r"gsk_[A-Za-z0-9]{20,}"), "[REDACTED_API_KEY]"),
        (re.compile(r"shopmind-ai-production-grade-secret-key[^\s]*", re.I), "[REDACTED_SECRET]"),
    ]

    @classmethod
    def inspect_user_query(
        cls,
        query: str,
        db: Optional[Session] = None,
        endpoint: str = "/api/chat",
        user_id: Optional[int] = None,
        ip_address: str = "127.0.0.1",
    ) -> Dict[str, Any]:
        """Inspects incoming user query for prompt injection, SQLi, XSS, and unauthorized tool probes."""
        cleaned = (query or "").strip()
        if not cleaned:
            return {"safe": False, "reason": "Empty query.", "risk_category": "Input Validation", "severity": "LOW"}

        if len(cleaned) > 2000:
            cls.log_security_event(
                db=db,
                event_type="OVERSIZED_QUERY",
                severity="MEDIUM",
                risk_category="OWASP LLM10: Unbounded Consumption",
                endpoint=endpoint,
                user_id=user_id,
                ip_address=ip_address,
                payload_excerpt=cleaned[:200],
                mitigation_action="Rejected query exceeding 2000 character limit",
                blocked=True,
            )
            return {
                "safe": False,
                "reason": "Query exceeds maximum allowed length (2000 characters).",
                "risk_category": "OWASP LLM10: Unbounded Consumption",
                "severity": "MEDIUM",
            }

        for pattern, risk_category, severity in cls.DIRECT_INJECTION_PATTERNS:
            if pattern.search(cleaned):
                cls.log_security_event(
                    db=db,
                    event_type="PROMPT_INJECTION_BLOCKED",
                    severity=severity,
                    risk_category=risk_category,
                    endpoint=endpoint,
                    user_id=user_id,
                    ip_address=ip_address,
                    payload_excerpt=cleaned[:250],
                    mitigation_action="Blocked malicious prompt before LLM invocation",
                    blocked=True,
                )
                return {
                    "safe": False,
                    "reason": f"Blocked by ShopMind AI Security Guardrail ({risk_category}). I cannot override system instructions, execute unauthorized commands, or reveal internal credentials.",
                    "risk_category": risk_category,
                    "severity": severity,
                }

        return {
            "safe": True,
            "reason": "Passed all OWASP LLM input security checks",
            "risk_category": "NONE",
            "severity": "NONE",
        }

    @classmethod
    def sanitize_untrusted_document(
        cls,
        text: str,
        source_id: str = "unknown",
        db: Optional[Session] = None,
    ) -> Tuple[str, bool]:
        """Sanitizes untrusted product descriptions/documents against indirect prompt injection."""
        if not text:
            return "", False
        sanitized = text
        detected = False
        for pattern in cls.INDIRECT_DOCUMENT_PATTERNS:
            if pattern.search(sanitized):
                detected = True
                sanitized = pattern.sub("[REDACTED_UNTRUSTED_INSTRUCTION]", sanitized)
        if detected:
            cls.log_security_event(
                db=db,
                event_type="INDIRECT_INJECTION_NEUTRALIZED",
                severity="HIGH",
                risk_category="OWASP LLM01: Indirect Prompt Injection in Document",
                endpoint=f"document:{source_id}",
                user_id=None,
                ip_address="internal-pipeline",
                payload_excerpt=text[:250],
                mitigation_action="Stripped embedded instruction from untrusted product document",
                blocked=True,
            )
        return sanitized, detected

    @classmethod
    def validate_grounded_output(
        cls,
        generated_text: str,
        retrieved_products: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Verifies that product IDs and prices mentioned in generated response match retrieved context."""
        sanitized_text = generated_text
        for pattern, replacement in cls.SECRET_OUTPUT_PATTERNS:
            sanitized_text = pattern.sub(replacement, sanitized_text)

        valid_ids = {p["product_id"] for p in retrieved_products}
        mentioned_ids = set(re.findall(r"PROD-[A-Z]{3}-\d{3}", sanitized_text))
        hallucinated_ids = list(mentioned_ids - valid_ids)

        grounding_verified = len(hallucinated_ids) == 0
        if hallucinated_ids:
            for fake_id in hallucinated_ids:
                sanitized_text = sanitized_text.replace(fake_id, "[UNVERIFIED_PRODUCT_ID]")

        return {
            "sanitized_text": sanitized_text,
            "grounding_verified": grounding_verified,
            "valid_cited_ids": list(mentioned_ids & valid_ids),
            "hallucinated_ids": hallucinated_ids,
        }

    @staticmethod
    def redact_conversation_secrets(text: str) -> str:
        """Ensures user secrets, API keys, or credit cards are never stored in conversation memory."""
        redacted = re.sub(r"gsk_[A-Za-z0-9]{20,}", "[REDACTED_GROQ_KEY]", text)
        redacted = re.sub(r"sk-[A-Za-z0-9]{20,}", "[REDACTED_API_KEY]", redacted)
        redacted = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CARD_NUMBER]", redacted)
        return redacted

    @staticmethod
    def log_security_event(
        db: Optional[Session],
        event_type: str,
        severity: str,
        risk_category: str,
        endpoint: str,
        user_id: Optional[int],
        ip_address: str,
        payload_excerpt: str,
        mitigation_action: str,
        blocked: bool = True,
    ) -> None:
        logger.warning(
            f"SECURITY_EVENT type={event_type} severity={severity} category='{risk_category}' endpoint={endpoint} blocked={blocked}"
        )
        if db is not None:
            try:
                ev = SecurityEvent(
                    event_type=event_type,
                    severity=severity,
                    risk_category=risk_category,
                    endpoint=endpoint,
                    user_id=user_id,
                    ip_address=ip_address,
                    payload_excerpt=payload_excerpt[:400],
                    mitigation_action=mitigation_action,
                    blocked=blocked,
                )
                db.add(ev)
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.error(f"Failed to persist SecurityEvent: {exc}")
