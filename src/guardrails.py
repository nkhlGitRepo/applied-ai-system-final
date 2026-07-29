"""
Validation utilities (guardrails).

Provides input/output validation used across the advisor module. Phase 1 uses
the song-metadata validation and retrieval-count clamping to keep the knowledge
base safe (see ../../../GUARDRAILS.md sections 3.1 and 3.2).

Later phases add:
  - validate_user_input()    (Phase 2 - intent parser)
  - validate_llm_response()  (Phase 2 - intent parser)
"""

from typing import Dict


# Terms that flag a song as unsafe for recommendation. Left intentionally empty
# by default so the catalog is not falsely filtered; wire real terms in here if
# a deployment needs content moderation (see GUARDRAILS.md section 3.1).
BLOCKED_TERMS: set = set()

# Fields every song must have to be usable by the knowledge base.
REQUIRED_SONG_FIELDS = (
    "id", "title", "artist", "genre", "mood",
    "energy", "popularity", "release_decade",
)

# Numeric fields validated only when present, mapped to their valid (min, max).
NUMERIC_FIELD_RANGES = {
    "energy": (0.0, 1.0),
    "valence": (0.0, 1.0),
    "danceability": (0.0, 1.0),
    "acousticness": (0.0, 1.0),
    "popularity": (0.0, 100.0),
    # Lower bound reaches the Baroque era so classical works (e.g. Bach, 1700s)
    # are not wrongly filtered out of the catalog.
    "release_decade": (1600, 2100),
}


def clamp(value: float, low: float, high: float) -> float:
    """Clamp value into the inclusive range [low, high]."""
    return max(low, min(high, value))


def validate_retrieval_count(count: int, minimum: int = 1, maximum: int = 50) -> int:
    """Clamp a requested retrieval count into a safe range.

    Prevents resource exhaustion from oversized retrieval requests
    (GUARDRAILS.md section 3.2). Non-integer input falls back to `minimum`.

    Args:
        count: Requested number of results.
        minimum: Smallest allowed count (default 1).
        maximum: Largest allowed count (default 50).

    Returns:
        An int within [minimum, maximum].
    """
    try:
        count = int(count)
    except (TypeError, ValueError):
        return minimum
    return int(clamp(count, minimum, maximum))


def validate_song_metadata(song: Dict) -> bool:
    """Check that a song dict is well-formed and safe to serve.

    Validation steps (GUARDRAILS.md section 3.1):
      1. All required fields are present.
      2. Numeric fields fall within their valid ranges.
      3. Text fields contain no blocked terms.

    Args:
        song: Song dictionary (as produced by recommender.load_songs).

    Returns:
        True if the song passes all checks, else False.
    """
    if not isinstance(song, dict):
        return False

    # 1. Required fields present (and not None).
    for field in REQUIRED_SONG_FIELDS:
        if field not in song or song[field] is None:
            return False

    # 2. Numeric ranges.
    for field, (low, high) in NUMERIC_FIELD_RANGES.items():
        if field in song and song[field] is not None:
            value = song[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False
            if not (low <= value <= high):
                return False

    # 3. Blocked-term scan on user-facing text fields.
    if BLOCKED_TERMS:
        for field in ("title", "artist", "genre", "mood"):
            text = str(song.get(field, "")).lower()
            if any(term in text for term in BLOCKED_TERMS):
                return False

    return True


# ---------------------------------------------------------------------------
# Phase 2: Input validation & sanitization (Intent Resolver)
# ---------------------------------------------------------------------------
import re
import logging

# Injection attack patterns to reject (GUARDRAILS.md section 2)
_INJECTION_PATTERNS = [
    r"(?i)(system|exec|eval|import|__)",           # Python/shell commands
    r"(?i)(select|insert|update|drop|delete)\s+from",  # SQL
    r"(\.\./|\/etc\/|\/tmp\/)",                    # File path traversal
    r"(?i)(ignore|forget|override|bypass|disable)", # Prompt injection markers
]

def validate_user_input(message: str, max_length: int = 2000) -> tuple[bool, str]:
    """Validate user input for safety (GUARDRAILS.md section 1).

    Checks:
      1. Message is not None/empty
      2. Message is within length limit
      3. Message doesn't contain injection patterns

    Args:
        message: Raw user input
        max_length: Maximum allowed message length (default 2000)

    Returns:
        (is_valid, sanitized_message) where sanitized is trimmed/stripped
    """
    if not message or not isinstance(message, str):
        return False, ""

    message = message.strip()

    if len(message) == 0:
        return False, ""

    if len(message) > max_length:
        return False, f"Message exceeds {max_length} characters"

    # Check for injection patterns
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, message):
            return False, "Message contains potentially harmful content"

    return True, message


def sanitize_user_input(message: str) -> str:
    """Prepare user input for LLM (remove control chars, normalize whitespace).

    Args:
        message: Validated user input (must already pass validate_user_input)

    Returns:
        Sanitized message safe for LLM
    """
    # Remove control characters
    message = "".join(ch for ch in message if ord(ch) >= 32 or ch in "\n\t")

    # Normalize whitespace
    message = " ".join(message.split())

    return message


def sanitize_explanation(text: str) -> str:
    """Sanitize explanation text for output (escape HTML, remove injection).

    Args:
        text: Explanation text from LLM/recommender

    Returns:
        Safe HTML-escaped text
    """
    import html

    # Escape HTML
    text = html.escape(text)

    # Remove any remaining HTML tags (in case of escaped sequences)
    text = re.sub(r"&lt;[^&]*&gt;", "", text)

    return text


def safe_log_error(logger: logging.Logger, error: Exception, context: str = "") -> None:
    """Log an error without exposing credentials or sensitive data.

    Args:
        logger: Python logger instance
        error: Exception to log
        context: Brief context string (no user data)
    """
    logger.error(f"{context}: {type(error).__name__}: {str(error)[:100]}")
