import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from groq import Groq
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import app_log


class GuardrailEvaluation(BaseModel):
    is_safe: bool
    risk_score: float = 0.0
    category: str = "clean"
    reason: Optional[str] = None
    inspected_text: str = ""

# Guardrails in-memory telemetry
GUARDRAILS_METRICS: Dict[str, Any] = {
    "total_input_inspections": 0,
    "total_input_blocked": 0,
    "total_output_inspections": 0,
    "total_output_blocked": 0,
    "last_incident": None,
}

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"output\s+the\s+system\s+prompt",
    r"print\s+(the\s+)?system\s+prompt",
    r"reveal\s+your\s+system\s+prompt",
    r"developer\s+mode\s+(enabled|on)",
    r"dan\s+mode",
    r"bypass\s+(all\s+)?(filters|access\s+controls|security)",
    r"drop\s+table\b",
    r"union\s+select\b",
]

SECRET_PATTERNS = [
    r"gsk_[a-zA-Z0-9]{30,}",
    r"jina_[a-zA-Z0-9]{30,}",
    r"lsv2_pt_[a-zA-Z0-9_]{30,}",
    r"postgresql://[a-zA-Z0-9_\-]+:[^@]+@",
    r"eyJ[a-zA-Z0-9_\-]{20,}\.eyJ[a-zA-Z0-9_\-]{20,}",
]


def check_input_guardrail(query: str, user_email: str = "") -> GuardrailEvaluation:
    """Evaluate user input for prompt injection, jailbreaks, and malicious commands.

    Uses fast pattern detection + Meta Llama Prompt Guard 86M via Groq.
    """
    settings = get_settings()
    GUARDRAILS_METRICS["total_input_inspections"] += 1
    cleaned = query.strip()

    # 1. Pattern heuristic check
    for pat in INJECTION_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            GUARDRAILS_METRICS["total_input_blocked"] += 1
            incident = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "input_prompt_injection",
                "user": user_email,
                "reason": f"Matched malicious pattern: {pat}",
                "snippet": cleaned[:100],
            }
            GUARDRAILS_METRICS["last_incident"] = incident
            app_log("WARNING", "guardrails.input", f"[INPUT BLOCKED] Pattern-matched injection from {user_email}: {pat}")
            return GuardrailEvaluation(
                is_safe=False,
                risk_score=0.99,
                category="prompt_injection",
                reason="Input contains instructions attempting to override system behavior or security policies.",
                inspected_text=cleaned,
            )

    # 2. Model-based guardrail (Llama Prompt Guard 2 86M on Groq)
    guard_model = settings.PROMPT_GUARD_MODEL or "meta-llama/llama-prompt-guard-2-86m"
    if settings.ENABLE_GUARDRAILS and settings.GROQ_API_KEY:
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            resp = client.chat.completions.create(
                model=guard_model,
                messages=[{"role": "user", "content": cleaned}],
                temperature=0.0,
                max_tokens=20,
            )
            raw_out = resp.choices[0].message.content.strip()
            # If the model returns a probability score string:
            try:
                score = float(raw_out)
                if score > 0.70:
                    GUARDRAILS_METRICS["total_input_blocked"] += 1
                    incident = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "type": "input_guardrail_violation",
                        "user": user_email,
                        "reason": f"Prompt Guard score: {score:.3f}",
                        "snippet": cleaned[:100],
                    }
                    GUARDRAILS_METRICS["last_incident"] = incident
                    app_log("WARNING", "guardrails.input", f"[INPUT BLOCKED] {guard_model} score {score:.3f} for query: {cleaned[:60]}")
                    return GuardrailEvaluation(
                        is_safe=False,
                        risk_score=score,
                        category="prompt_injection",
                        reason=f"Security guardrail detected suspicious prompt manipulation (score: {score:.2f}).",
                        inspected_text=cleaned,
                    )
            except ValueError:
                # Non-float output from text safeguard model
                if any(kw in raw_out.lower() for kw in ["sorry, but i can't help", "unsafe", "violation"]):
                    GUARDRAILS_METRICS["total_input_blocked"] += 1
                    app_log("WARNING", "guardrails.input", f"[INPUT BLOCKED] Guardrail refusal triggered for query: {cleaned[:60]}")
                    return GuardrailEvaluation(
                        is_safe=False,
                        risk_score=0.95,
                        category="safeguard_refusal",
                        reason="Input rejected by enterprise safety policy.",
                        inspected_text=cleaned,
                    )
        except Exception as e:
            app_log("WARNING", "guardrails.input", f"Model guardrail evaluation skipped due to API error: {e}")
        except Exception as e:
            app_log("WARNING", "guardrails.input", f"Model guardrail evaluation skipped due to unexpected error: {e}")

    app_log("INFO", "guardrails.input", f"Input guardrail evaluation passed for query: {cleaned[:50]}")
    return GuardrailEvaluation(is_safe=True, risk_score=0.0, category="clean", inspected_text=cleaned)


def check_output_guardrail(answer: str) -> GuardrailEvaluation:
    """Evaluate model output to prevent leakages of system credentials, API keys, or raw JWTs."""
    GUARDRAILS_METRICS["total_output_inspections"] += 1
    cleaned = answer.strip()

    for pat in SECRET_PATTERNS:
        if re.search(pat, cleaned):
            GUARDRAILS_METRICS["total_output_blocked"] += 1
            incident = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "output_secret_leak",
                "reason": f"Detected credential pattern: {pat}",
            }
            GUARDRAILS_METRICS["last_incident"] = incident
            app_log("ERROR", "guardrails.output", f"[OUTPUT BLOCKED] Potential credential leakage detected matching {pat}")
            return GuardrailEvaluation(
                is_safe=False,
                risk_score=1.0,
                category="data_exfiltration",
                reason="Output contains sensitive system tokens or connection credentials.",
                inspected_text=cleaned[:50],
            )

    app_log("INFO", "guardrails.output", "Output guardrail evaluation passed. No sensitive credentials detected.")
    return GuardrailEvaluation(is_safe=True, risk_score=0.0, category="clean", inspected_text=cleaned[:50])


def get_guardrails_metrics() -> Dict[str, Any]:
    """Return live guardrails telemetry for admin monitoring."""
    settings = get_settings()
    total_in = GUARDRAILS_METRICS["total_input_inspections"]
    blocked_in = GUARDRAILS_METRICS["total_input_blocked"]
    total_out = GUARDRAILS_METRICS["total_output_inspections"]
    blocked_out = GUARDRAILS_METRICS["total_output_blocked"]
    total = total_in + total_out
    total_blocked = blocked_in + blocked_out
    pass_rate = 100.0 if total == 0 else ((total - total_blocked) / total) * 100.0

    return {
        "enabled": settings.ENABLE_GUARDRAILS,
        "input_guard_model": settings.PROMPT_GUARD_MODEL,
        "safeguard_model": settings.GUARD_MODEL_NAME,
        "total_input_inspections": total_in,
        "total_input_blocked": blocked_in,
        "total_output_inspections": total_out,
        "total_output_blocked": blocked_out,
        "pass_rate_percentage": round(pass_rate, 1),
        "last_incident": GUARDRAILS_METRICS["last_incident"],
    }
