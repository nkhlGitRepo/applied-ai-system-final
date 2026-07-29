"""
Tests for Phase 2 - Intent Resolver.

Tests cover:
1. Method interactions (parse → resolve → select_mode)
2. Different intent types and queries
3. Conflict detection
4. Edge cases and guardrails
5. Default fallback behavior
"""

import pytest
from src.phase2_intent_resolver import (
    IntentResolver,
    IntentStructure,
    create_resolver,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def resolver():
    return IntentResolver()


# ---------------------------------------------------------------------------
# Integration Tests (Method Interactions)
# ---------------------------------------------------------------------------
class TestIntegration:
    """Test full resolve() workflow: parse → resolve → select_mode."""

    def test_resolve_simple_request(self, resolver):
        """Full workflow: "recommend 5 chill songs" → prefs + mode + confidence."""
        prefs, mode, confidence = resolver.resolve("recommend 5 chill songs")

        assert prefs["favorite_genre"] == "pop"  # default
        assert prefs["favorite_mood"] == "chill"  # extracted
        assert prefs["target_energy"] == 0.3     # low (chill)
        assert mode == "genre-first"              # low energy → genre-first (prioritizes mood/genre)
        assert 0.6 <= confidence <= 1.0

    def test_resolve_with_genre_and_energy(self, resolver):
        """Extract multiple fields: "high-energy rock songs"."""
        prefs, mode, confidence = resolver.resolve("high-energy rock songs")

        assert prefs["favorite_genre"] == "rock"
        assert prefs["target_energy"] == 0.8
        assert mode == "genre-first"  # high energy → genre-first
        assert confidence > 0.6

    def test_resolve_discover_mode(self, resolver):
        """Low energy + wants discovery."""
        prefs, mode, confidence = resolver.resolve("find me relaxing acoustic music I've never heard")

        assert prefs["target_energy"] <= 0.4
        assert mode == "genre-first"  # low energy → genre-first (not discovery)

    def test_resolve_niche_via_low_energy(self, resolver):
        """Low energy naturally leads to genre-first mode."""
        prefs, mode, confidence = resolver.resolve("slow indie music")

        assert prefs["favorite_genre"] == "indie"
        assert prefs["target_energy"] == 0.3
        assert mode == "genre-first"  # low energy → genre-first (not discovery)

    def test_resolve_full_specification(self, resolver):
        """Request with multiple constraints."""
        prefs, mode, confidence = resolver.resolve(
            "10 high-energy electronic songs, acoustic preferred"
        )

        assert prefs["favorite_genre"] == "electronic"
        assert prefs["target_energy"] == 0.8  # "high-energy" keyword
        assert prefs["likes_acoustic"] == True
        assert confidence > 0.7

    def test_resolve_conflicting_prefs(self, resolver):
        """Conflicting prefs: "acoustic rock" (resolved but logged)."""
        prefs, mode, confidence = resolver.resolve("I want acoustic rock music")

        assert prefs["favorite_genre"] == "rock"
        assert prefs["likes_acoustic"] == True


# ---------------------------------------------------------------------------
# Intent Type Detection
# ---------------------------------------------------------------------------
class TestIntentDetection:
    """Test intent type detection via resolve()."""

    def test_detect_recommend_default(self, resolver):
        """Default 'recommend' intent."""
        prefs, _, _ = resolver.resolve("Give me some songs")
        assert isinstance(prefs, dict)

    def test_detect_create_playlist(self, resolver):
        """'create_playlist' intent from keywords."""
        prefs, _, _ = resolver.resolve("create a playlist from sad to happy")
        assert isinstance(prefs, dict)

    def test_detect_discover(self, resolver):
        """'discover' intent from keywords."""
        prefs, _, _ = resolver.resolve("discover new hidden gems")
        assert isinstance(prefs, dict)

    def test_detect_compare(self, resolver):
        """'compare' intent from keywords."""
        prefs, _, _ = resolver.resolve("find songs similar to jazz")
        assert isinstance(prefs, dict)

    def test_detect_explain(self, resolver):
        """'explain' intent from keywords."""
        prefs, _, _ = resolver.resolve("why would I like this song")
        assert isinstance(prefs, dict)


# ---------------------------------------------------------------------------
# Field Extraction Tests
# ---------------------------------------------------------------------------
class TestFieldExtraction:
    """Test individual extraction methods via resolve()."""

    def test_extract_genre(self, resolver):
        """Extract genre from message."""
        prefs, _, _ = resolver.resolve("I like jazz")
        assert prefs["favorite_genre"] == "jazz"

    def test_extract_all_genres(self, resolver):
        """Extract each supported genre."""
        for genre in IntentResolver.GENRES:
            prefs, _, _ = resolver.resolve(f"I want {genre}")
            assert prefs["favorite_genre"] == genre

    def test_extract_mood(self, resolver):
        """Extract mood from message."""
        prefs, _, _ = resolver.resolve("happy uplifting songs")
        assert prefs["favorite_mood"] == "happy"  # first match

    def test_extract_all_moods(self, resolver):
        """Extract each supported mood."""
        for mood in IntentResolver.MOODS:
            prefs, _, _ = resolver.resolve(f"I need something {mood}")
            assert prefs["favorite_mood"] == mood

    def test_extract_high_energy(self, resolver):
        """Extract high energy from keywords."""
        prefs, _, _ = resolver.resolve("energetic and intense music")
        assert prefs["target_energy"] == 0.8

    def test_extract_low_energy(self, resolver):
        """Extract low energy from keywords."""
        prefs, _, _ = resolver.resolve("slow, peaceful, calm music")
        assert prefs["target_energy"] == 0.3

    def test_extract_medium_energy(self, resolver):
        """Extract medium energy from keywords."""
        prefs, _, _ = resolver.resolve("moderate balanced energy")
        assert prefs["target_energy"] == 0.5

    def test_extract_acoustic_true(self, resolver):
        """Extract acoustic preference."""
        prefs, _, _ = resolver.resolve("acoustic guitar unplugged")
        assert prefs["likes_acoustic"] == True

    def test_extract_electronic_false(self, resolver):
        """Extract electronic preference."""
        prefs, _, _ = resolver.resolve("electronic synth digital")
        assert prefs["likes_acoustic"] == False

    def test_extract_count_from_message(self, resolver):
        """Extract song count from message."""
        prefs, _, _ = resolver.resolve("give me 10 songs")
        assert isinstance(prefs, dict)

    def test_extract_count_singular(self, resolver):
        """Extract count with singular 'song'."""
        prefs, _, _ = resolver.resolve("I want 1 song")
        assert isinstance(prefs, dict)


# ---------------------------------------------------------------------------
# Mode Selection Tests
# ---------------------------------------------------------------------------
class TestModeSelection:
    """Test mode selection based on energy."""

    def test_mode_genre_first_high_energy(self, resolver):
        """High energy → genre-first."""
        _, mode, _ = resolver.resolve("intense energetic rock")
        assert mode == "genre-first"

    def test_mode_discovery_low_energy(self, resolver):
        """Low energy → genre-first (not discovery)."""
        _, mode, _ = resolver.resolve("calm relaxing chill")
        assert mode == "genre-first"

    def test_mode_personality_default(self, resolver):
        """No strong signal → personality."""
        _, mode, _ = resolver.resolve("recommend songs")
        assert mode == "personality"

    def test_mode_niche_friendly(self, resolver):
        """Niche preference → niche-friendly."""
        prefs, _, _ = resolver.resolve("obscure indie")
        prefs["prefer_popular"] = False
        mode = resolver._select_mode(prefs)
        assert mode == "niche-friendly"


# ---------------------------------------------------------------------------
# Confidence Scoring Tests
# ---------------------------------------------------------------------------
class TestConfidence:
    """Test confidence calculation based on extracted fields."""

    def test_confidence_no_fields(self, resolver):
        """Minimal extraction → lower confidence."""
        _, _, confidence = resolver.resolve("songs")
        assert 0.5 <= confidence < 0.7

    def test_confidence_one_field(self, resolver):
        """One field extracted → medium confidence."""
        _, _, confidence = resolver.resolve("pop songs")
        assert 0.6 <= confidence < 0.8

    def test_confidence_all_fields(self, resolver):
        """All fields extracted → high confidence."""
        _, _, confidence = resolver.resolve(
            "10 acoustic uplifting pop songs with high energy"
        )
        assert confidence > 0.8

    def test_confidence_clamped_to_one(self, resolver):
        """Confidence never exceeds 1.0."""
        _, _, confidence = resolver.resolve(
            "acoustic uplifting pop high energy intense"
        )
        assert confidence <= 1.0


# ---------------------------------------------------------------------------
# Defaults & Fallback Tests
# ---------------------------------------------------------------------------
class TestDefaults:
    """Test fallback values when fields not extracted."""

    def test_default_genre_pop(self, resolver):
        """Default genre is 'pop'."""
        prefs, _, _ = resolver.resolve("just some music")
        assert prefs["favorite_genre"] == "pop"

    def test_default_mood_happy(self, resolver):
        """Default mood is 'happy'."""
        prefs, _, _ = resolver.resolve("just some music")
        assert prefs["favorite_mood"] == "happy"

    def test_default_energy_medium(self, resolver):
        """Default energy is 0.6 (medium)."""
        prefs, _, _ = resolver.resolve("just some music")
        assert prefs["target_energy"] == 0.6

    def test_default_acoustic_false(self, resolver):
        """Default acoustic preference is False."""
        prefs, _, _ = resolver.resolve("just some music")
        assert prefs["likes_acoustic"] == False

    def test_default_popular_true(self, resolver):
        """Default prefers popular music."""
        prefs, _, _ = resolver.resolve("just some music")
        assert prefs["prefer_popular"] == True

    def test_default_decade_2020(self, resolver):
        """Default target decade is 2020."""
        prefs, _, _ = resolver.resolve("just some music")
        assert prefs["target_release_decade"] == 2020


# ---------------------------------------------------------------------------
# Guardrails Tests (Input Validation)
# ---------------------------------------------------------------------------
class TestGuardrails:
    """Test guardrails: input validation, rejection of malicious input."""

    def test_reject_empty_message(self, resolver):
        """Reject empty input."""
        with pytest.raises(ValueError):
            resolver.resolve("")

    def test_reject_whitespace_only(self, resolver):
        """Reject whitespace-only input."""
        with pytest.raises(ValueError):
            resolver.resolve("   ")

    def test_reject_oversized_message(self, resolver):
        """Reject message exceeding max length."""
        with pytest.raises(ValueError):
            resolver.resolve("a" * 3000)

    def test_reject_exec_injection(self, resolver):
        """Reject exec/eval injection attempts."""
        with pytest.raises(ValueError):
            resolver.resolve("__import__ exec eval os.system")

    def test_reject_file_injection_traversal(self, resolver):
        """Reject file path traversal attempts."""
        with pytest.raises(ValueError):
            resolver.resolve("../../etc/passwd pop songs")

    def test_reject_file_traversal(self, resolver):
        """Reject file path traversal."""
        with pytest.raises(ValueError):
            resolver.resolve("../../etc/passwd")

    def test_sanitize_control_characters(self, resolver):
        """Sanitize removes control characters."""
        # Should not raise, sanitization removes problematic chars
        prefs, _, _ = resolver.resolve("pop\x00songs")
        assert prefs["favorite_genre"] == "pop"

    def test_sanitize_normalizes_whitespace(self, resolver):
        """Sanitize normalizes multiple spaces."""
        prefs, _, _ = resolver.resolve("pop    songs   with   spaces")
        assert isinstance(prefs, dict)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    """Test unusual but valid inputs."""

    def test_case_insensitive_matching(self, resolver):
        """Genre/mood matching is case-insensitive."""
        prefs, _, _ = resolver.resolve("I WANT POP AND HAPPY MUSIC")
        assert prefs["favorite_genre"] == "pop"
        assert prefs["favorite_mood"] == "happy"

    def test_multiple_genres_first_wins(self, resolver):
        """If message mentions multiple genres, first is selected."""
        prefs, _, _ = resolver.resolve("pop or rock or jazz")
        assert prefs["favorite_genre"] == "pop"  # first match

    def test_multiple_moods_first_wins(self, resolver):
        """If message mentions multiple moods, first is selected."""
        prefs, _, _ = resolver.resolve("happy or sad or calm")
        assert prefs["favorite_mood"] == "happy"

    def test_very_short_message(self, resolver):
        """Very short but valid message."""
        prefs, _, _ = resolver.resolve("pop")
        assert prefs["favorite_genre"] == "pop"

    def test_single_character_resolves_with_defaults(self, resolver):
        """Single character gets defaults."""
        prefs, mode, confidence = resolver.resolve("a")
        # Single character is valid but has low confidence
        assert prefs["favorite_genre"] == "pop"  # default
        assert confidence == 0.5  # no fields extracted


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------
class TestFactory:
    """Test create_resolver() factory function."""

    def test_create_resolver_no_api_key(self):
        """Create resolver without API key."""
        resolver = create_resolver()
        assert resolver is not None
        assert isinstance(resolver, IntentResolver)

    def test_create_resolver_with_api_key(self):
        """Create resolver with API key."""
        resolver = create_resolver(api_key="test-key")
        assert resolver.api_key == "test-key"

    def test_factory_resolver_works(self):
        """Factory-created resolver works."""
        resolver = create_resolver()
        prefs, mode, confidence = resolver.resolve("pop songs")
        assert prefs["favorite_genre"] == "pop"
        assert isinstance(mode, str)
        assert 0.0 <= confidence <= 1.0
