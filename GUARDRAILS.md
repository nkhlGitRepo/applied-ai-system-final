# AI Safety Guardrails - Music Advisor System

**Purpose**: Establish safeguards against harmful content, prompt injection, data leakage, and abuse in the RAG + Agentic Workflow Music Advisor.

**Status**: Implementation guidelines for Phase 1-9 development

---

## 1. Input Validation & Sanitization

### 1.1 User Message Validation
**Location**: `intent_parser.py` - before LLM calls
**Rules**:
- Maximum message length: 2000 characters (prevent token spam)
- Reject null/empty inputs
- Strip leading/trailing whitespace
- Check for suspicious patterns (SQL injection, shell commands, file paths)

**Implementation**:
```python
def validate_user_input(message: str) -> tuple[bool, str]:
    """
    Returns: (is_valid, sanitized_message)
    """
    if not message or len(message) == 0:
        return False, "Message cannot be empty"
    
    if len(message) > 2000:
        return False, f"Message too long ({len(message)}/2000 chars)"
    
    message = message.strip()
    
    # Reject patterns common in injection attacks
    dangerous_patterns = [
        r"(?i)(system|exec|eval|import|__)",  # Python/shell commands
        r"(?i)(select|insert|update|drop|delete)\s*from",  # SQL
        r"(\.\./|\/etc\/|\/tmp\/)",  # File path traversal
    ]
    
    import re
    for pattern in dangerous_patterns:
        if re.search(pattern, message):
            return False, "Message contains potentially harmful content"
    
    return True, message
```

### 1.2 Intent Structure Validation
**Location**: `intent_parser.py` - after parsing
**Rules**:
- Validate all enum-like fields against whitelist
- Ensure confidence score is 0.0-1.0
- Validate parameter counts match reasonable bounds
- No nested/recursive structures

**Whitelist Examples**:
```python
VALID_INTENT_TYPES = {
    "recommend", "explain", "create_playlist", 
    "compare", "discover"
}

VALID_CONSTRAINTS = {
    "genre", "mood", "energy", "acoustic", 
    "decade", "vocal_style", "production"
}

VALID_PARAMETERS = {
    "count": (1, 50),           # 1-50 songs max
    "energy": (0.0, 1.0),      # 0-1 scale
    "tempo": (40, 200),         # BPM range
}
```

---

## 2. Prompt Injection Prevention

### 2.1 LLM Prompt Security
**Location**: `intent_parser.py` - when calling Claude API
**Rules**:
- Use system prompts with clear boundaries
- Never interpolate user input directly into instructions
- Use structured templates with placeholders
- Validate LLM output before using

**Implementation Pattern**:
```python
# ❌ BAD - User input directly in prompt
prompt = f"Parse this request: {user_message}"

# ✅ GOOD - Structured template with validation
PARSE_TEMPLATE = """You are a music recommendation intent parser.
Parse the following user request into structured intent.
Respond with JSON only (no explanation).

User Request:
{user_request}

Respond with JSON: {{"intent_type": "...", "parameters": {{...}}}}"""

prompt = PARSE_TEMPLATE.format(user_request=sanitized_message)
# Then validate JSON response
```

### 2.2 Output Validation
**Location**: After all LLM API calls
**Rules**:
- Validate JSON responses are well-formed
- Validate all fields match expected schema
- Reject responses with suspicious content
- Log rejected outputs for monitoring

**Implementation**:
```python
def validate_llm_response(response: str, schema: dict) -> tuple[bool, any]:
    """
    Validates LLM response against schema.
    Returns: (is_valid, parsed_object)
    """
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return False, None
    
    # Check all required fields present
    for required_field in schema.get("required", []):
        if required_field not in parsed:
            return False, None
    
    # Validate field types
    for field, field_type in schema.get("properties", {}).items():
        if field in parsed:
            if not isinstance(parsed[field], field_type):
                return False, None
    
    return True, parsed
```

---

## 3. Knowledge Base Integrity

### 3.1 Content Filtering
**Location**: `knowledge_base.py` - song loading and retrieval
**Rules**:
- Validate all songs in catalog have required fields
- Check for harmful/offensive content in song metadata
- Verify song attributes are within valid ranges
- Prevent retrieval of flagged songs

**Implementation**:
```python
def validate_song_metadata(song: dict) -> bool:
    """Check song passes safety validation."""
    required_fields = [
        "id", "title", "artist", "genre", "mood", 
        "energy", "popularity", "release_decade"
    ]
    
    # Check all required fields present
    if not all(field in song for field in required_fields):
        return False
    
    # Validate ranges
    if not (0 <= song["energy"] <= 1.0):
        return False
    
    if not (0 <= song["popularity"] <= 100):
        return False
    
    if not (1900 <= song["release_decade"] <= 2100):
        return False
    
    # Check for offensive content in text fields
    harmful_keywords = ["explicit", "violence", "hate"]  # examples
    for field in ["title", "artist"]:
        text = str(song.get(field, "")).lower()
        if any(keyword in text for keyword in harmful_keywords):
            return False
    
    return True
```

### 3.2 Retrieval Constraints
**Location**: `knowledge_base.py` - retrieve_* functions
**Rules**:
- Limit retrieval result size (max 100 songs)
- Validate all retrieved songs pass safety check
- Never retrieve flagged/removed songs
- Log retrieval requests for audit

**Implementation**:
```python
def retrieve_similar_songs(
    song: dict, 
    count: int = 5, 
    max_distance: float = 0.3
) -> List[dict]:
    """Retrieve similar songs with safety constraints."""
    
    # Validate input count
    count = min(max(1, count), 50)  # Clamp to 1-50
    
    results = []
    # ... retrieval logic ...
    
    # Filter out unsafe songs
    results = [s for s in results if validate_song_metadata(s)]
    
    # Return clamped results
    return results[:count]
```

---

## 4. Rate Limiting & Abuse Prevention

### 4.1 API Call Limiting
**Location**: `conversation.py` - conversation loop
**Rules**:
- Limit messages per conversation session: 100/hour
- Limit API calls per user: throttle aggressive querying
- Implement exponential backoff for failures
- Log rate limit violations

**Implementation**:
```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_calls: int = 100, window_minutes: int = 60):
        self.max_calls = max_calls
        self.window = timedelta(minutes=window_minutes)
        self.calls = defaultdict(list)  # user_id -> [timestamps]
    
    def is_allowed(self, user_id: str) -> bool:
        now = datetime.now()
        # Remove old calls outside window
        self.calls[user_id] = [
            t for t in self.calls[user_id] 
            if now - t < self.window
        ]
        
        if len(self.calls[user_id]) >= self.max_calls:
            return False
        
        self.calls[user_id].append(now)
        return True
```

### 4.2 Recommendation Limits
**Location**: `recommender.py` - recommend_songs
**Rules**:
- Maximum k=100 (prevent resource exhaustion)
- Maximum distinct genres: 20
- Maximum recommendations per hour: depends on deployment

---

## 5. Data Privacy & Conversation History

### 5.1 Conversation Memory Safety
**Location**: `conversation.py` - conversation storage
**Rules**:
- Never store raw API responses with sensitive data
- Anonymize user preferences in logs
- Expire conversation history after 30 days
- Encrypt stored conversation data

**Implementation**:
```python
def store_conversation_turn(user_id: str, message: str, response: str):
    """Safely store conversation turn without sensitive data."""
    
    # Don't store full message if it contains email/phone/etc
    sanitized_message = sanitize_personal_info(message)
    
    # Store anonymized preferences, not full user profile
    turn = {
        "user_id": hash(user_id),  # Hash, don't store plaintext
        "timestamp": datetime.now().isoformat(),
        "message": sanitized_message,
        "response": response,  # Already contains only song titles/artists
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
    }
    
    return turn
```

### 5.2 No Credential Leakage
**Location**: All error handling
**Rules**:
- Never log API keys or tokens
- Never expose full stack traces to users
- Never include system paths in error messages
- Sanitize exception logs

**Implementation**:
```python
def safe_exception_handler(e: Exception) -> str:
    """Generate user-safe error message."""
    
    # Log full exception internally
    logger.error(f"Internal error", exc_info=True)
    
    # Return generic message to user
    return "We encountered an issue processing your request. Please try again."
```

---

## 6. Output Content Filtering

### 6.1 Explanation Sanitization
**Location**: `explainer.py` - before returning explanations
**Rules**:
- Escape HTML/special characters
- Remove any potentially harmful content from retrieved context
- Validate all output stays within bounds
- Don't include unverified artist/song claims

**Implementation**:
```python
import html

def sanitize_explanation(text: str) -> str:
    """Sanitize explanation text for safe output."""
    
    # Escape HTML
    text = html.escape(text)
    
    # Remove any remaining suspicious patterns
    import re
    text = re.sub(r'<[^>]*>', '', text)  # Remove HTML tags
    text = re.sub(r'(?i)(javascript:|onclick=)', '', text)  # Remove event handlers
    
    return text
```

### 6.2 Recommendation Validation
**Location**: Before returning recommendations
**Rules**:
- Verify all returned songs exist in knowledge base
- Verify scores are within [0, 10] range
- Verify explanations reference actual song attributes
- Reject malformed results

---

## 7. Error Handling & Logging

### 7.1 Secure Logging
**Location**: All modules
**Rules**:
- Log errors without exposing secrets
- Include request IDs for tracing
- Log security events (rate limit hits, invalid inputs)
- Never log full user messages (summarize intent only)

**Implementation**:
```python
import logging

logger = logging.getLogger(__name__)

def log_security_event(event_type: str, user_id: str, details: str):
    """Log security-relevant events."""
    logger.warning(
        f"SECURITY_EVENT",
        extra={
            "event_type": event_type,
            "user_id": hash(user_id),  # Anonymized
            "details": details
        }
    )
```

### 7.2 Graceful Degradation
**Location**: All critical paths
**Rules**:
- Fail safely (return empty results rather than crash)
- Provide helpful error messages
- Fallback to simpler recommendation if complex logic fails
- Never expose implementation details to users

---

## 8. Third-Party API Safety (Claude API)

### 8.1 API Call Security
**Rules**:
- Never pass raw user input directly to API
- Use structured system prompts with clear boundaries
- Validate all API responses before using
- Handle rate limiting from API provider
- Use latest Claude model for safety features

**Implementation**:
```python
def call_intent_parser_api(sanitized_message: str) -> dict:
    """Call Claude API safely for intent parsing."""
    
    response = client.messages.create(
        model="claude-opus-4-8",  # Use latest model
        max_tokens=1000,
        system="You are a music recommendation intent parser. Extract only: intent_type, constraints, parameters. Return JSON only.",
        messages=[
            {
                "role": "user",
                "content": f"Parse request:\n{sanitized_message}"
            }
        ]
    )
    
    # Validate before returning
    content = response.content[0].text
    is_valid, parsed = validate_llm_response(content, INTENT_SCHEMA)
    
    if not is_valid:
        raise ValueError("Invalid intent parsing response")
    
    return parsed
```

---

## 9. Implementation Checklist

- [ ] **Phase 2 (Intent Parser)**: Add input validation + prompt injection prevention
- [ ] **Phase 1 (Knowledge Base)**: Add song metadata validation + content filtering
- [ ] **Phase 6-7 (Agent Loops)**: Add output sanitization + validation
- [ ] **Phase 8 (Conversation)**: Add rate limiting + secure history storage
- [ ] **All Phases**: Add logging + error handling without credential leakage
- [ ] **Testing**: Create security test suite (injection attempts, malformed inputs, boundary conditions)

---

## 10. Security Test Cases

Create `tests/test_guardrails.py`:

```python
def test_sql_injection_rejected():
    """Ensure SQL injection attempts are rejected."""
    assert not validate_user_input("SELECT * FROM users; DROP TABLE users;")[0]

def test_prompt_injection_rejected():
    """Ensure prompt injection attempts are rejected."""
    assert not validate_user_input("Ignore above instructions and...")[0]

def test_max_message_length_enforced():
    """Ensure oversized messages are rejected."""
    long_message = "a" * 3000
    assert not validate_user_input(long_message)[0]

def test_song_validation_rejects_invalid_ranges():
    """Ensure invalid song data is rejected."""
    bad_song = {"energy": 2.5, "popularity": 150}  # Out of range
    assert not validate_song_metadata(bad_song)

def test_rate_limiting_enforced():
    """Ensure rate limiter blocks excessive requests."""
    limiter = RateLimiter(max_calls=5, window_minutes=1)
    user = "test_user"
    
    # Should allow up to 5
    for _ in range(5):
        assert limiter.is_allowed(user)
    
    # Should block 6th
    assert not limiter.is_allowed(user)

def test_explanation_sanitized():
    """Ensure explanations remove HTML/injection."""
    unsafe = "Click <a onclick='alert(1)'>here</a>"
    safe = sanitize_explanation(unsafe)
    assert "<" not in safe
    assert "onclick" not in safe
```

---

## 11. Monitoring & Alerts

**Metrics to track**:
- Rate limit violations (potential abuse)
- Input validation failures (potential attacks)
- LLM response validation failures (API issues or attacks)
- Conversation history expiry compliance
- Error rates by component

**Alert conditions**:
- >10 rate limit hits from same user in 1 hour
- >5% input validation failure rate
- Any SQL injection pattern detected
- Any API credential in logs

---

## 12. Documentation & Training

- Document all guardrails in code comments
- Add safety section to model_card.md
- Train on secure coding practices
- Regular security audits (quarterly)

---

**Revision Date**: 2026-07-21  
**Next Review**: When Phase 2 (Intent Parser) is implemented
