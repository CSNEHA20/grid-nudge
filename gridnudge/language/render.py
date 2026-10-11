"""Message rendering engine with Bedrock integration, verifier gating, and template fallback.

Per AGENTS.md Section 1.4:
The LLM never decides. It only formats verified facts into natural language.
Every LLM output is verified by verify_nudge_text before delivery.
If Bedrock errors, times out, or hallucinates numbers, the system safely falls back
to deterministic templates with source="template".
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from gridnudge.contracts import Language
from gridnudge.language.verify import verify_nudge_text

logger = logging.getLogger(__name__)

from gridnudge.language.templates import render_template, TEMPLATES

# Fallback deterministic templates (permanent fallback per AGENTS.md Kill Rules Section 12)
DEFAULT_TEMPLATES = TEMPLATES["en"]


def _render_deterministic_template(facts: Dict[str, Any], frame: str, lang: str = "en") -> str:
    """Render deterministic fallback template using structured facts."""
    return render_template(facts=facts, frame=frame, lang=lang)


def render_bedrock_message(
    facts: Dict[str, Any],
    frame: str,
    lang: str = "en",
    tone: str = "friendly",
    model_id: Optional[str] = None,
) -> Optional[str]:
    """Call Amazon Bedrock converse API to phrase approved facts."""
    try:
        import boto3

        m_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        brt = boto3.client("bedrock-runtime")

        prompt = (
            f"Write one concise friendly sentence in {lang}, tone: {tone}. "
            f"Frame: {frame}. "
            f"Use ONLY these exact facts, and do NOT invent any numbers, percentages, or guarantees: "
            f"{json.dumps(facts)}"
        )

        response = brt.converse(
            modelId=m_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 100, "temperature": 0.2},
        )
        output_text = response["output"]["message"]["content"][0]["text"].strip()
        return output_text

    except Exception as exc:
        logger.debug("Bedrock rendering skipped or failed (falling back to template): %s", exc)
        return None


def render_nudge_message(
    facts: Dict[str, Any],
    frame: str,
    lang: str = "en",
    tone: str = "friendly",
    use_llm: bool = False,
    model_id: Optional[str] = None,
) -> Language:
    """Render and verify message for delivered persuasion nudge.

    Args:
        facts: Approved structured facts payload.
        frame: Persuasion frame ('cost', 'green', 'battery', etc.).
        lang: Target language code ('en', 'hi').
        tone: Tone of voice ('friendly', 'direct').
        use_llm: Whether to attempt Bedrock LLM generation.
        model_id: Optional Bedrock model ID.

    Returns:
        Typed Language contract object.
    """
    if frame == "none" or not facts:
        return Language(message=None, facts_used={}, verified=True, source="none")

    # 1. Attempt Bedrock generation if requested
    if use_llm:
        llm_text = render_bedrock_message(facts, frame, lang=lang, tone=tone, model_id=model_id)
        if llm_text:
            is_valid, reasons = verify_nudge_text(llm_text, facts)
            if is_valid:
                return Language(
                    message=llm_text,
                    facts_used=facts,
                    verified=True,
                    source="llm",
                )
            else:
                logger.warning("LLM generated text failed verification: %s. Using template fallback.", reasons)

    # 2. Template fallback (check Sneha's module if available, otherwise built-in)
    try:
        from gridnudge.language.templates import render_template
        template_text = render_template(facts, frame, lang=lang)
    except (ImportError, AttributeError):
        template_text = _render_deterministic_template(facts, frame)

    is_valid, _ = verify_nudge_text(template_text, facts)

    return Language(
        message=template_text,
        facts_used=facts,
        verified=is_valid,
        source="template",
    )
