"""
Phase 2: Intent Resolver - Parse natural language + resolve preferences.

Parses user requests into structured intent, resolves conflicts, and maps to
scoring modes. Uses heuristic parsing (simple, modular, no external API).

Public API:
    resolver = IntentResolver()
    user_prefs, mode, confidence = resolver.resolve("Find 5 chill songs")
    # Returns: ({genre: "lofi", mood: "chill", energy: 0.4, ...}, "discovery", 0.92)
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from src.guardrails import validate_user_input, sanitize_user_input, safe_log_error

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class IntentStructure:
    """Parsed user intent extracted from natural language."""
    intent_type: str            # "recommend", "create_playlist", "discover", etc.
    primary_genre: Optional[str]  # "pop", "lofi", "rock", etc. (or None)
    primary_mood: Optional[str]   # "happy", "chill", "intense", etc. (or None)
    target_energy: Optional[float]  # 0.0-1.0 (or None for unspecified)
    likes_acoustic: Optional[bool]  # (or None for unspecified)
    prefer_popular: Optional[bool]  # True for mainstream, False for niche (or None)
    request_count: Optional[int]    # Number of songs requested (or None if not specified)
    confidence: float               # How confident in this parsing (0.0-1.0)


# ---------------------------------------------------------------------------
# Intent Resolver
# ---------------------------------------------------------------------------
class IntentResolver:
    """Parse natural language requests into structured intent."""

    # Supported values (used by extraction methods)
    GENRES = ["pop", "rock", "lofi", "jazz", "classical", "electronic",
              "hip-hop", "indie", "country", "blues", "ambient", "reggae",
              "synthwave", "dubstep", "soul", "experimental"]

    MOODS = ["happy", "chill", "intense", "sad", "melancholic", "energetic",
             "uplifting", "moody", "calm", "upbeat", "meditative", "nostalgic"]

    def __init__(self, api_key: Optional[str] = None):
        """Initialize resolver.

        Args:
            api_key: API key (unused in Phase 2, but kept for future Claude API integration)
        """
        self.api_key = api_key

    def resolve(self, user_message: str) -> Tuple[Dict, str, float]:
        """Parse user message → (user_prefs, recommended_mode, confidence).

        Args:
            user_message: Raw user input

        Returns:
            (user_prefs dict, scoring mode, confidence score)

        Raises:
            ValueError: If input validation fails
        """
        # 1. Validate input
        is_valid, error_msg = validate_user_input(user_message)
        if not is_valid:
            raise ValueError(f"Invalid input: {error_msg}")

        sanitized = sanitize_user_input(user_message)

        # 2. Parse intent
        intent = self._parse_intent(sanitized)

        # 3. Resolve conflicts & fill defaults
        resolved, intent_type = self._resolve_preferences(intent)

        # 4. Select scoring mode (using both prefs and explicit intent type)
        mode = self._select_mode(resolved, intent_type)

        return resolved, mode, intent.confidence

    # -----------------------------------------------------------------------
    # Private methods - Parsing
    # -----------------------------------------------------------------------
    def _parse_intent(self, message: str) -> IntentStructure:
        """Parse message into IntentStructure using heuristics.

        Args:
            message: Sanitized user message

        Returns:
            IntentStructure with parsed intent
        """
        message_lower = message.lower()

        # Extract each field (all follow Optional[T] pattern for consistency)
        intent_type = self._detect_intent_type(message_lower)
        primary_genre = self._extract_genre(message_lower)
        primary_mood = self._extract_mood(message_lower)
        target_energy = self._extract_energy(message_lower)
        likes_acoustic = self._extract_acoustic(message_lower)
        prefer_popular = self._extract_popularity(message_lower)

        # Calculate confidence based on how many fields were explicitly extracted
        extracted_count = sum([
            primary_genre is not None,
            primary_mood is not None,
            target_energy is not None,
            likes_acoustic is not None,
            prefer_popular is not None,
        ])
        confidence = 0.5 + (extracted_count * 0.1)  # 0.5 base + 0.1 per field

        return IntentStructure(
            intent_type=intent_type,
            primary_genre=primary_genre,
            primary_mood=primary_mood,
            target_energy=target_energy,
            likes_acoustic=likes_acoustic,
            prefer_popular=prefer_popular,
            request_count=None,  # Count is for display only, not used in prefs
            confidence=min(confidence, 1.0),
        )

    def _detect_intent_type(self, message: str) -> str:
        """Infer intent type from message keywords."""
        keywords = {
            "create_playlist": ["create", "playlist", "journey"],
            "discover": ["discover", "hidden", "gem", "explore", "new"],
            "compare": ["compare", "similar", "like"],
            "explain": ["why", "explain", "reason"],
        }

        for intent, words in keywords.items():
            if any(word in message for word in words):
                return intent

        return "recommend"  # default

    def _extract_genre(self, message: str) -> Optional[str]:
        """Extract primary genre from message (first match, handles hyphens)."""
        # Normalize: remove hyphens for flexible matching
        # This allows "lo-fi" to match "lofi" and "hip hop" to match "hip-hop"
        normalized_msg = message.replace("-", "")

        for genre in self.GENRES:
            normalized_genre = genre.replace("-", "")
            if normalized_genre in normalized_msg:
                return genre  # Return original genre with hyphen if present
        return None

    def _extract_mood(self, message: str) -> Optional[str]:
        """Extract primary mood from message (direct mood words or playlist type/genre keywords)."""
        # Direct mood keywords
        for mood in self.MOODS:
            if mood in message:
                return mood

        # Playlist-type and genre keywords that map to moods
        keyword_mood_map = {
            "study": "calm",
            "work": "calm",
            "focus": "calm",
            "focused": "calm",
            "concentration": "calm",
            "workout": "energetic",
            "running": "energetic",
            "gym": "energetic",
            "cardio": "energetic",
            "party": "energetic",
            "sleep": "meditative",
            "relax": "calm",
            "relaxing": "calm",
            # Genre-based mood defaults
            "lofi": "chill",
            "lo-fi": "chill",
            "lo fi": "chill",
            "ambient": "meditative",
            "classical": "meditative",
            "jazz": "relaxed",
        }

        for keyword, mood in keyword_mood_map.items():
            if keyword in message:
                return mood

        return None

    def _extract_energy(self, message: str) -> Optional[float]:
        """Extract target energy level from keywords."""
        high_keywords = ["high", "energetic", "fast", "intense", "loud", "pumped"]
        low_keywords = ["low", "chill", "slow", "calm", "quiet", "relax", "peaceful"]
        mid_keywords = ["medium", "moderate", "balanced", "middle"]
        lofi_keywords = ["lofi", "lo-fi", "lo fi"]  # lo-fi is typically low-energy

        if any(w in message for w in high_keywords):
            return 0.8
        if any(w in message for w in low_keywords):
            return 0.3
        # Lo-fi genre inherently suggests low energy
        if any(w in message for w in lofi_keywords):
            return 0.3
        if any(w in message for w in mid_keywords):
            return 0.5

        return None

    def _extract_acoustic(self, message: str) -> Optional[bool]:
        """Extract acoustic preference from keywords."""
        acoustic_keywords = ["acoustic", "guitar", "unplugged", "organic"]
        electronic_keywords = ["electronic", "digital", "synth", "produced"]

        if any(w in message for w in acoustic_keywords):
            return True
        if any(w in message for w in electronic_keywords):
            return False

        return None

    def _extract_popularity(self, message: str) -> Optional[bool]:
        """Extract popularity preference (mainstream vs niche)."""
        niche_keywords = ["niche", "hidden", "underground", "obscure", "unpopular", "gem"]
        popular_keywords = ["popular", "mainstream", "hits", "famous", "well-known"]

        if any(w in message for w in niche_keywords):
            return False  # Prefers niche
        if any(w in message for w in popular_keywords):
            return True   # Prefers popular

        return None

    def _extract_count(self, message: str) -> Optional[int]:
        """Extract requested song count from message."""
        matches = re.findall(r'\b(\d+)\s*(songs?|tracks?)\b', message, re.IGNORECASE)
        if matches:
            try:
                count = int(matches[0][0])
                return min(max(count, 1), 50)  # Clamp to 1-50
            except (ValueError, IndexError):
                pass
        return None  # No explicit count mentioned

    # -----------------------------------------------------------------------
    # Private methods - Resolution
    # -----------------------------------------------------------------------
    def _resolve_preferences(self, intent: IntentStructure) -> Tuple[Dict, str]:
        """Resolve parsed intent into user_prefs dict + intent_type for downstream use.

        Args:
            intent: Parsed IntentStructure

        Returns:
            (user_prefs dict, intent_type) compatible with recommender.recommend_songs()
        """
        # Fill defaults where not specified
        prefs = {
            "favorite_genre": intent.primary_genre or "pop",
            "favorite_mood": intent.primary_mood or "happy",
            "target_energy": intent.target_energy or 0.6,
            "likes_acoustic": intent.likes_acoustic if intent.likes_acoustic is not None else False,
            "prefer_popular": intent.prefer_popular if intent.prefer_popular is not None else True,
            "target_release_decade": 2020,
        }

        return prefs, intent.intent_type

    def _select_mode(self, user_prefs: Dict, intent_type: str = "recommend") -> str:
        """Select scoring mode based on resolved preferences and explicit intent.

        Decision tree (in order of priority):
        1. Niche preference → "niche-friendly"
        2. Energy level (if explicitly constrained): high → "genre-first", low → "discovery"
        3. Explicit intent: "discover" → "discovery", "create_playlist" → "personality"
        4. Default → "personality"

        Args:
            user_prefs: Resolved preferences dict
            intent_type: Explicit intent from parsed message

        Returns:
            Scoring mode: "genre-first", "discovery", "niche-friendly", "personality"
        """
        energy = user_prefs.get("target_energy", 0.6)
        popular = user_prefs.get("prefer_popular", True)

        # 1. Niche preference (highest priority)
        if not popular:
            return "niche-friendly"

        # 2. Energy level guidance (if explicitly constrained, use it even for playlists)
        if energy >= 0.75:
            return "genre-first"      # High energy → genre-focused for high-energy hits
        elif energy <= 0.35:
            return "genre-first"      # Low energy → genre-focused for calming/study playlists

        # 3. Intent type
        if intent_type == "discover":
            return "discovery"
        if intent_type == "create_playlist":
            return "personality"

        # 4. Default
        return "personality"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_resolver(api_key: Optional[str] = None) -> IntentResolver:
    """Create an IntentResolver instance.

    Args:
        api_key: Optional API key for future Claude integration

    Returns:
        New IntentResolver
    """
    return IntentResolver(api_key=api_key)
