"""Numeric and claim verifier for generated persuasion messages.

NON-NEGOTIABLE AGENT RULE (AGENTS.md Section 1.4 & Section 9):
The LLM never decides. Every numeric claim in generated text must be traceable
to the structured approved facts payload.

Any unsupported number, hallucinated saving, or forbidden claim (guarantees,
lifespan promises, real-world claims) causes immediate rejection and triggers
fallback to deterministic templates.
"""

from decimal import Decimal
import re
from typing import Any, Dict, List, Set, Tuple

NUM_PATTERN = re.compile(r"\d+(?:\.\d+)?")

FORBIDDEN_PATTERN = re.compile(
    r"guarantee|will last|safe for sure|100\s*%|risk[- ]free|"
    r"proven on real users|saves \d+%\s*in the real world|promise",
    re.IGNORECASE,
)


def extract_allowed_numbers(facts: Dict[str, Any]) -> Set[str]:
    """Extract all permitted numeric representations from structured facts dictionary."""
    allowed: Set[str] = set()

    for key, val in facts.items():
        if val is None:
            continue

        val_str = str(val).replace(",", "")
        extracted = NUM_PATTERN.findall(val_str)
        allowed.update(extracted)

        # Also support integer / float conversions and percentages
        if isinstance(val, (int, float, Decimal)):
            num_float = float(val)
            # Add integer representation
            allowed.add(str(int(round(num_float))))
            # If probability in (0, 1], allow corresponding whole percentage (e.g. 0.94 -> 94)
            if 0.0 < num_float <= 1.0:
                allowed.add(str(int(round(num_float * 100))))
                allowed.add(f"{num_float * 100:.1f}")
            # If currency or energy with decimal, allow rounded integer (e.g. 51.3 -> 51)
            allowed.add(f"{num_float:.1f}")
            allowed.add(f"{num_float:.2f}")

        # If time string "HH:MM", allow components
        if isinstance(val, str) and ":" in val:
            parts = val.split(":")
            if len(parts) >= 2:
                allowed.add(parts[0].lstrip("0") or "0")
                allowed.add(parts[1])
                # Format for 12-hour AM/PM (e.g. "22" -> "10")
                try:
                    h_int = int(parts[0])
                    if h_int > 12:
                        allowed.add(str(h_int - 12))
                    elif h_int == 0:
                        allowed.add("12")
                except ValueError:
                    pass

    return allowed


def verify_nudge_text(text: str, facts: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Verify that generated message contains no forbidden phrases or unsupported numbers.

    Args:
        text: Generated message text to verify.
        facts: Approved structured facts payload.

    Returns:
        Tuple of (verified: bool, violation_reasons: List[str]).
    """
    reasons: List[str] = []

    if not text or not text.strip():
        return False, ["Message text is empty"]

    # 1. Forbidden phrase check
    forbidden_match = FORBIDDEN_PATTERN.search(text)
    if forbidden_match:
        reasons.append(f"Forbidden claim detected: '{forbidden_match.group(0)}'")

    # 2. Numeric traceability check
    allowed_numbers = extract_allowed_numbers(facts)
    clean_text = text.replace(",", "")
    text_numbers = set(NUM_PATTERN.findall(clean_text))

    unsupported_numbers = text_numbers - allowed_numbers
    if unsupported_numbers:
        reasons.append(f"Unsupported numbers detected: {sorted(list(unsupported_numbers))}")

    is_verified = len(reasons) == 0
    return is_verified, reasons
