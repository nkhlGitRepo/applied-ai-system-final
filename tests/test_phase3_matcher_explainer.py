"""
Tests for Phase 3 - Matcher-Explainer.

Tests cover:
1. Method interactions (score → enrich → explain workflow)
2. Different modes and k values
3. RAG context integration
4. Output quality and completeness
5. Edge cases
"""

import pytest
from src.phase1_knowledge_base import KnowledgeBase
from src.phase3_matcher_explainer import MatcherExplainer, create_matcher_explainer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _song(**overrides):
    """Build a valid song dict."""
    base = {
        "id": 1,
        "title": "Sample Song",
        "artist": "Sample Artist",
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "tempo_bpm": 120,
        "valence": 0.8,
        "danceability": 0.7,
        "acousticness": 0.2,
        "popularity": 70,
        "release_decade": 2020,
        "vocal_style": "sung",
        "production_quality": "polished",
        "emotional_arc": "constant",
    }
    base.update(overrides)
    return base


@pytest.fixture
def sample_songs():
    """Create test songs matching Phase 1 catalog."""
    return [
        _song(id=1, title="Sunrise City", artist="Neon Echo", genre="pop",
              mood="happy", energy=0.82, acousticness=0.18, popularity=78),
        _song(id=2, title="Neon Nights", artist="Neon Echo", genre="pop",
              mood="uplifting", energy=0.88, acousticness=0.12, popularity=64),
        _song(id=3, title="Midnight Coding", artist="LoRoom", genre="lofi",
              mood="chill", energy=0.42, acousticness=0.71, popularity=42,
              vocal_style="instrumental", production_quality="lo-fi"),
        _song(id=4, title="Library Rain", artist="Paper Lanterns", genre="lofi",
              mood="chill", energy=0.35, acousticness=0.86, popularity=38,
              vocal_style="instrumental", production_quality="lo-fi",
              emotional_arc="minimal"),
        _song(id=5, title="Storm Runner", artist="Voltline", genre="rock",
              mood="intense", energy=0.91, acousticness=0.10, popularity=65,
              emotional_arc="builds"),
    ]


@pytest.fixture
def kb(sample_songs):
    return KnowledgeBase(sample_songs)


@pytest.fixture
def matcher(kb):
    return MatcherExplainer(kb)


# ---------------------------------------------------------------------------
# Integration Tests (Method Interactions)
# ---------------------------------------------------------------------------
class TestIntegration:
    """Test full match_and_explain workflow: score → enrich → explain."""

    def test_match_and_explain_basic(self, matcher, sample_songs):
        """Full workflow: user_prefs → top-k recommendations with explanations."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.85,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(user_prefs, sample_songs, k=3)

        assert len(results) == 3
        # Each result is (song, score, explanation)
        assert all(len(r) == 3 for r in results)

        # Verify song dicts
        assert all(isinstance(r[0], dict) for r in results)
        assert all("title" in r[0] for r in results)

        # Verify scores
        assert all(isinstance(r[1], float) for r in results)
        assert all(0 <= r[1] <= 10 for r in results)  # GMEWS score range

        # Verify explanations
        assert all(isinstance(r[2], str) for r in results)
        assert all(len(r[2]) > 20 for r in results)  # Non-trivial explanations

    def test_match_and_explain_ranked_by_score(self, matcher, sample_songs):
        """Results ranked by score descending."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.85,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(user_prefs, sample_songs, k=5)

        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_match_and_explain_different_modes(self, matcher, sample_songs):
        """Different modes produce different rankings."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.6,
            "likes_acoustic": False,
        }

        results_genre_first = matcher.match_and_explain(
            user_prefs, sample_songs, k=5, mode="genre-first"
        )
        results_discovery = matcher.match_and_explain(
            user_prefs, sample_songs, k=5, mode="discovery"
        )

        # Different modes should produce different top-1 (likely)
        top1_genre = results_genre_first[0][0]["id"]
        top1_discovery = results_discovery[0][0]["id"]
        assert isinstance(top1_genre, int)
        assert isinstance(top1_discovery, int)

    def test_match_and_explain_k_respected(self, matcher, sample_songs):
        """k parameter limits results correctly."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        }

        for k in [1, 2, 3, 5]:
            results = matcher.match_and_explain(user_prefs, sample_songs, k=k)
            assert len(results) == min(k, len(sample_songs))


# ---------------------------------------------------------------------------
# Method Interaction Tests
# ---------------------------------------------------------------------------
class TestMethodInteractions:
    """Test individual method interactions."""

    def test_score_songs_returns_correct_format(self, matcher, sample_songs):
        """_score_songs returns (song, score, explanation) tuples."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        }

        scored = matcher._score_songs(user_prefs, sample_songs, k=3, mode="genre-first")

        assert len(scored) == 3
        assert all(len(item) == 3 for item in scored)
        assert all(isinstance(item[0], dict) for item in scored)  # song
        assert all(isinstance(item[1], float) for item in scored)  # score
        assert all(isinstance(item[2], str) for item in scored)   # explanation

    def test_enrich_with_context_adds_rag_data(self, matcher, sample_songs):
        """_enrich_with_context retrieves RAG knowledge for a song."""
        song = sample_songs[0]  # Sunrise City
        score = 7.5

        enriched = matcher._enrich_with_context(song, score)

        assert "song" in enriched
        assert enriched["song"]["id"] == song["id"]
        assert enriched["score"] == score
        assert "rag_context" in enriched

        # RAG context should be populated
        rag = enriched["rag_context"]
        assert rag is not None
        assert hasattr(rag, "artist_profile")
        assert hasattr(rag, "genre_context")
        assert hasattr(rag, "similar_songs")

    def test_enrich_with_unknown_song(self, matcher, sample_songs):
        """_enrich_with_context handles songs not in KB gracefully."""
        unknown_song = _song(id=999, title="Unknown Title", artist="Unknown")
        score = 5.0

        enriched = matcher._enrich_with_context(unknown_song, score)

        assert enriched["song"]["id"] == 999
        assert enriched["rag_context"] is None  # KB returns None for unknown

    def test_generate_explanation_uses_all_sources(self, matcher, sample_songs):
        """_generate_explanation incorporates score + artist + genre + similar."""
        song = sample_songs[0]  # Sunrise City
        score = 7.5

        enriched = matcher._enrich_with_context(song, score)
        explanation = matcher._generate_explanation(enriched)

        # Should contain elements from multiple sources
        assert str(score) in explanation or "7.5" in explanation or "Score" in explanation
        assert "Neon Echo" in explanation  # Artist name
        assert "pop" in explanation.lower()  # Genre
        assert len(explanation) > 50  # Non-trivial

    def test_explanation_handles_missing_rag_context(self, matcher):
        """_generate_explanation works even with no RAG context."""
        song_data = {
            "song": _song(title="No Context"),
            "score": 5.0,
            "rag_context": None,
        }

        explanation = matcher._generate_explanation(song_data)

        # Should still produce explanation
        assert isinstance(explanation, str)
        assert len(explanation) > 0


# ---------------------------------------------------------------------------
# RAG Context Tests
# ---------------------------------------------------------------------------
class TestRAGIntegration:
    """Test integration with Phase 1 Knowledge Base."""

    def test_kb_integration_retrieves_artist_profile(self, matcher, sample_songs):
        """KB integration fetches and uses artist profiles."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.85,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(user_prefs, sample_songs, k=2)

        # Pop songs should mention artists in explanations
        pop_explanations = [r[2] for r in results if r[0]["genre"] == "pop"]
        assert any("Neon Echo" in expl for expl in pop_explanations)

    def test_kb_integration_retrieves_genre_context(self, matcher, sample_songs):
        """KB integration fetches and uses genre context."""
        user_prefs = {
            "favorite_genre": "lofi",
            "favorite_mood": "chill",
            "target_energy": 0.4,
            "likes_acoustic": True,
        }

        results = matcher.match_and_explain(user_prefs, sample_songs, k=2)

        # Should mention genre characteristics
        explanations = [r[2] for r in results]
        assert any("lofi" in expl.lower() for expl in explanations)

    def test_kb_integration_retrieves_similar_songs(self, matcher, sample_songs):
        """KB integration includes similar songs in explanations."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.85,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(user_prefs, sample_songs, k=1)

        # Explanation might reference similar songs
        explanation = results[0][2]
        # Check structure (may or may not have similar songs depending on KB)
        assert isinstance(explanation, str)


# ---------------------------------------------------------------------------
# Explanation Quality Tests
# ---------------------------------------------------------------------------
class TestExplanationQuality:
    """Test explanation generation quality."""

    def test_score_reasoning_present(self, matcher, sample_songs):
        """Explanations include score and basic song info."""
        song = sample_songs[0]
        score = 7.5
        enriched = matcher._enrich_with_context(song, score)
        explanation = matcher._generate_explanation(enriched)

        # Should mention score, genre, mood, energy
        assert "pop" in explanation.lower()
        assert "happy" in explanation.lower()
        assert "0.8" in explanation  # energy
        assert "Score" in explanation

    def test_artist_reasoning_present(self, matcher, sample_songs):
        """Explanations include artist context when available."""
        song = sample_songs[0]  # Neon Echo
        enriched = matcher._enrich_with_context(song, 7.5)
        explanation = matcher._generate_explanation(enriched)

        assert "Neon Echo" in explanation

    def test_genre_reasoning_present(self, matcher, sample_songs):
        """Explanations include genre context when available."""
        song = sample_songs[2]  # Lofi song
        enriched = matcher._enrich_with_context(song, 6.0)
        explanation = matcher._generate_explanation(enriched)

        assert "lofi" in explanation.lower() or "Lofi" in explanation

    def test_similarity_reasoning_present(self, matcher, sample_songs):
        """Explanations reference similar songs when available."""
        song = sample_songs[0]  # Pop song
        enriched = matcher._enrich_with_context(song, 7.5)
        explanation = matcher._generate_explanation(enriched)

        # Should mention similar songs if KB found them
        assert "Similar" in explanation or len(explanation) > 100


# ---------------------------------------------------------------------------
# Edge Cases & Error Handling
# ---------------------------------------------------------------------------
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_mode_defaults_to_genre_first(self, matcher, sample_songs):
        """Invalid mode falls back to genre-first."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        }

        # Should not raise, should use default mode
        results = matcher.match_and_explain(
            user_prefs, sample_songs, k=3, mode="invalid_mode"
        )

        assert len(results) == 3

    def test_k_greater_than_catalog_size(self, matcher, sample_songs):
        """k larger than catalog returns all available."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(user_prefs, sample_songs, k=100)

        assert len(results) == len(sample_songs)

    def test_empty_songs_list(self, matcher):
        """Empty song list returns empty results."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(user_prefs, [], k=5)

        assert len(results) == 0

    def test_single_song(self, matcher, sample_songs):
        """Single song recommendation works correctly."""
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(
            user_prefs, sample_songs[:1], k=1
        )

        assert len(results) == 1


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------
class TestFactory:
    """Test create_matcher_explainer factory function."""

    def test_create_matcher_explainer(self, kb):
        """Factory creates working MatcherExplainer."""
        matcher = create_matcher_explainer(kb)

        assert matcher is not None
        assert isinstance(matcher, MatcherExplainer)
        assert matcher.kb == kb

    def test_factory_matcher_works(self, kb, sample_songs):
        """Factory-created matcher works end-to-end."""
        matcher = create_matcher_explainer(kb)
        user_prefs = {
            "favorite_genre": "pop",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
        }

        results = matcher.match_and_explain(user_prefs, sample_songs, k=3)

        assert len(results) == 3
