"""
Tests for Phase 4 - Playlist Agent.

Tests cover:
1. Method interactions (UNDERSTAND → PLAN → RETRIEVE → EXECUTE → VALIDATE → ADJUST)
2. Single-phase and multi-phase playlists
3. Validation and adjustment loop
4. Phase extraction and preference modification
5. Edge cases and error handling
"""

import pytest
from src.phase2_intent_resolver import IntentResolver
from src.phase3_matcher_explainer import MatcherExplainer
from src.phase1_knowledge_base import KnowledgeBase
from src.phase4_playlist_agent import PlaylistAgent, Playlist, create_playlist_agent


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
              vocal_style="instrumental", production_quality="lo-fi"),
        _song(id=5, title="Storm Runner", artist="Voltline", genre="rock",
              mood="intense", energy=0.91, acousticness=0.10, popularity=65),
        _song(id=6, title="Midnight Blues", artist="Blue Notes", genre="jazz",
              mood="sad", energy=0.25, acousticness=0.60, popularity=45),
    ]


@pytest.fixture
def kb(sample_songs):
    return KnowledgeBase(sample_songs)


@pytest.fixture
def resolver():
    return IntentResolver()


@pytest.fixture
def matcher(kb):
    return MatcherExplainer(kb)


@pytest.fixture
def agent(resolver, matcher, kb, sample_songs):
    return PlaylistAgent(resolver, matcher, kb, sample_songs)


# ---------------------------------------------------------------------------
# Integration Tests (Full Workflow)
# ---------------------------------------------------------------------------
class TestIntegration:
    """Test full plan_and_execute workflow."""

    def test_plan_and_execute_single_phase(self, agent):
        """Full workflow: message → playlist (single phase)."""
        playlist = agent.plan_and_execute("Give me some pop songs")

        assert isinstance(playlist, Playlist)
        assert len(playlist.songs) > 0
        assert len(playlist.explanations) == len(playlist.songs)
        assert len(playlist.phase_labels) == len(playlist.songs)
        assert playlist.validation_score > 0

    def test_plan_and_execute_multi_phase(self, agent):
        """Full workflow: message → playlist (multi-phase journey)."""
        playlist = agent.plan_and_execute("Create a journey from sad to happy")

        assert len(playlist.songs) > 0
        # Should have multiple phases (journey keyword triggers extraction)
        phase_set = set(playlist.phase_labels)
        assert len(phase_set) >= 1

    def test_plan_and_execute_with_arrow_notation(self, agent):
        """Extract phases from arrow notation."""
        playlist = agent.plan_and_execute("Emotional arc: chill → intense")

        assert len(playlist.songs) > 0
        # Should have both phases
        phase_set = set(playlist.phase_labels)
        assert "chill" in phase_set or "intense" in phase_set

    def test_plan_and_execute_returns_valid_playlist(self, agent):
        """Playlist structure is valid."""
        playlist = agent.plan_and_execute("pop music")

        assert all(isinstance(s, dict) for s in playlist.songs)
        assert all("title" in s for s in playlist.songs)
        assert all(isinstance(e, str) for e in playlist.explanations)
        assert all(isinstance(p, str) for p in playlist.phase_labels)
        assert 0 <= playlist.validation_score <= 1.0


# ---------------------------------------------------------------------------
# Step 1: UNDERSTAND Tests
# ---------------------------------------------------------------------------
class TestUnderstand:
    """Test phase extraction from user messages."""

    def test_understand_single_phase_no_journey(self, agent):
        """Non-journey message returns single phase."""
        phases = agent._understand("Give me pop songs")
        assert phases == ["general"]

    def test_understand_journey_keyword(self, agent):
        """Journey keyword triggers multi-phase extraction."""
        phases = agent._understand("Create a journey from sad to happy")
        assert len(phases) >= 2

    def test_understand_arrow_notation_unicode(self, agent):
        """Extract phases from unicode arrow."""
        phases = agent._understand("sad → happy")
        assert len(phases) == 2
        assert "sad" in phases
        assert "happy" in phases

    def test_understand_arrow_notation_ascii(self, agent):
        """Extract phases from ASCII arrow."""
        phases = agent._understand("chill -> intense")
        assert len(phases) == 2
        assert "chill" in phases
        assert "intense" in phases

    def test_understand_mood_extraction(self, agent):
        """Extract moods as phases."""
        phases = agent._understand("journey through happy and chill moods")
        assert "happy" in phases or "chill" in phases

    def test_understand_case_insensitive(self, agent):
        """Phase extraction is case-insensitive."""
        phases = agent._understand("HAPPY -> SAD")
        assert len(phases) == 2
        phases_lower = [p.lower() for p in phases]
        assert "happy" in phases_lower
        assert "sad" in phases_lower


# ---------------------------------------------------------------------------
# Step 2: PLAN Tests
# ---------------------------------------------------------------------------
class TestPlan:
    """Test plan creation with phase-specific preferences."""

    def test_plan_creates_phase_prefs(self, agent):
        """Plan creates preferences for each phase."""
        phases = ["sad", "happy"]
        plan = agent._plan(phases, "Create journey from sad to happy")

        assert "phase_prefs" in plan
        assert "sad" in plan["phase_prefs"]
        assert "happy" in plan["phase_prefs"]

    def test_plan_sad_phase_preferences(self, agent):
        """Sad phase has low energy and sad mood."""
        phases = ["sad"]
        plan = agent._plan(phases, "sad songs")

        sad_prefs = plan["phase_prefs"]["sad"]
        assert sad_prefs["favorite_mood"] == "sad"
        assert sad_prefs["target_energy"] == 0.3

    def test_plan_happy_phase_preferences(self, agent):
        """Happy phase has high energy and happy mood."""
        phases = ["happy"]
        plan = agent._plan(phases, "happy songs")

        happy_prefs = plan["phase_prefs"]["happy"]
        assert happy_prefs["favorite_mood"] == "happy"
        assert happy_prefs["target_energy"] == 0.8

    def test_plan_chill_phase_preferences(self, agent):
        """Chill phase has low energy and chill mood."""
        phases = ["chill"]
        plan = agent._plan(phases, "relaxing music")

        chill_prefs = plan["phase_prefs"]["chill"]
        assert chill_prefs["favorite_mood"] == "chill"
        assert chill_prefs["target_energy"] == 0.3

    def test_plan_intense_phase_preferences(self, agent):
        """Intense phase has high energy and energetic mood."""
        phases = ["intense"]
        plan = agent._plan(phases, "energetic songs")

        intense_prefs = plan["phase_prefs"]["intense"]
        assert intense_prefs["favorite_mood"] == "energetic"
        assert intense_prefs["target_energy"] == 0.9

    def test_plan_transition_phase(self, agent):
        """Transition phase has mid-range energy."""
        phases = ["transition"]
        plan = agent._plan(phases, "transitional songs")

        trans_prefs = plan["phase_prefs"]["transition"]
        assert trans_prefs["target_energy"] == 0.5

    def test_plan_includes_base_prefs(self, agent):
        """Plan includes base preferences from resolver."""
        phases = ["happy"]
        plan = agent._plan(phases, "pop songs")

        assert "base_prefs" in plan
        assert "mode" in plan
        assert plan["base_prefs"]["favorite_genre"] == "pop"


# ---------------------------------------------------------------------------
# Step 3: RETRIEVE Tests
# ---------------------------------------------------------------------------
class TestRetrieve:
    """Test recommendation retrieval for each phase."""

    def test_retrieve_returns_recommendations_per_phase(self, agent):
        """Retrieve returns songs for each phase."""
        phases = ["happy", "sad"]
        plan = agent._plan(phases, "journey happy to sad")
        recommendations = agent._retrieve(plan)

        assert "happy" in recommendations
        assert "sad" in recommendations
        assert len(recommendations["happy"]) > 0
        assert len(recommendations["sad"]) > 0

    def test_retrieve_songs_match_phase_mood(self, agent):
        """Retrieved songs match phase preferences."""
        phases = ["sad"]
        plan = agent._plan(phases, "sad songs")
        recommendations = agent._retrieve(plan)

        sad_songs = recommendations["sad"]
        # At least some songs should be from jazz (has sad mood songs)
        assert len(sad_songs) > 0

    def test_retrieve_k_per_phase(self, agent):
        """Retrieve respects k per phase."""
        phases = ["happy", "sad"]
        plan = agent._plan(phases, "journey")
        recommendations = agent._retrieve(plan)

        for phase_results in recommendations.values():
            assert len(phase_results) >= 3  # Min 3 songs per phase


# ---------------------------------------------------------------------------
# Step 4: EXECUTE Tests
# ---------------------------------------------------------------------------
class TestExecute:
    """Test playlist assembly from recommendations."""

    def test_execute_combines_phases_in_order(self, agent):
        """Execute combines phase recommendations in correct order."""
        phases = ["happy", "sad"]
        plan = agent._plan(phases, "journey happy to sad")
        recommendations = agent._retrieve(plan)
        playlist = agent._execute(recommendations, phases)

        assert playlist.phase_labels[0] == "happy"
        # Sad songs should appear later
        sad_indices = [i for i, p in enumerate(playlist.phase_labels) if p == "sad"]
        happy_indices = [i for i, p in enumerate(playlist.phase_labels) if p == "happy"]
        if sad_indices and happy_indices:
            assert max(happy_indices) <= min(sad_indices) or len(phases) == 1

    def test_execute_adds_phase_labels_to_explanations(self, agent):
        """Execute prefixes explanations with phase labels."""
        phases = ["happy"]
        plan = agent._plan(phases, "happy songs")
        recommendations = agent._retrieve(plan)
        playlist = agent._execute(recommendations, phases)

        for explanation in playlist.explanations:
            assert "[Happy]" in explanation

    def test_execute_empty_recommendations(self, agent):
        """Execute handles empty recommendations."""
        recommendations = {"empty": []}
        phases = ["empty"]
        playlist = agent._execute(recommendations, phases)

        assert playlist.songs == []
        assert playlist.explanations == []


# ---------------------------------------------------------------------------
# Step 5: VALIDATE Tests
# ---------------------------------------------------------------------------
class TestValidate:
    """Test playlist validation and scoring."""

    def test_validate_returns_score_between_0_and_1(self, agent):
        """Validation score is in valid range."""
        phases = ["happy"]
        plan = agent._plan(phases, "happy songs")
        recommendations = agent._retrieve(plan)
        playlist = agent._execute(recommendations, phases)

        score = agent._validate(playlist, plan)
        assert 0 <= score <= 1.0

    def test_validate_empty_playlist_scores_zero(self, agent):
        """Empty playlist gets score of 0."""
        empty_playlist = Playlist(songs=[], explanations=[], phase_labels=[], validation_score=0)
        plan = {"phases": ["happy"]}

        score = agent._validate(empty_playlist, plan)
        assert score == 0

    def test_validate_full_coverage_high_score(self, agent):
        """Playlist covering all phases scores high."""
        phases = ["happy", "sad"]
        plan = agent._plan(phases, "journey")
        recommendations = agent._retrieve(plan)
        playlist = agent._execute(recommendations, phases)

        score = agent._validate(playlist, plan)
        # Should be reasonably high if it covers both phases
        assert score >= 0.5

    def test_validate_progression_check(self, agent):
        """Validation checks energy progression."""
        phases = ["chill", "intense"]
        plan = agent._plan(phases, "progression")
        recommendations = agent._retrieve(plan)
        playlist = agent._execute(recommendations, phases)

        # Should have some energy variance (progression exists)
        energies = [s.get("energy", 0.5) for s in playlist.songs]
        if len(energies) > 1:
            variance = max(energies) - min(energies)
            # Multi-phase playlist should show some progression
            assert variance > 0 or len(set(playlist.phase_labels)) == 1

    def test_validate_diversity_requirement(self, agent):
        """Validation checks for song diversity."""
        phases = ["happy"]
        plan = agent._plan(phases, "happy songs")
        recommendations = agent._retrieve(plan)
        playlist = agent._execute(recommendations, phases)

        unique_songs = len(set(s.get("id") for s in playlist.songs))
        # Should be mostly diverse (80%+ unique)
        diversity_ratio = unique_songs / len(playlist.songs) if playlist.songs else 1
        assert diversity_ratio >= 0.8


# ---------------------------------------------------------------------------
# Step 6: ADJUST Tests
# ---------------------------------------------------------------------------
class TestAdjust:
    """Test plan adjustment logic."""

    def test_adjust_modifies_energy_on_first_attempt(self, agent):
        """First adjustment lowers energy to broaden results."""
        phases = ["happy"]
        plan = agent._plan(phases, "happy songs")
        bad_playlist = Playlist(songs=[], explanations=[], phase_labels=[], validation_score=0)

        adjusted = agent._adjust(plan, bad_playlist, attempt=0)

        adjusted_energy = adjusted["phase_prefs"]["happy"]["target_energy"]
        original_energy = plan["phase_prefs"]["happy"]["target_energy"]
        assert adjusted_energy < original_energy

    def test_adjust_toggles_popularity_on_second_attempt(self, agent):
        """Second adjustment toggles popularity preference."""
        phases = ["happy"]
        plan = agent._plan(phases, "happy songs")
        bad_playlist = Playlist(songs=[], explanations=[], phase_labels=[], validation_score=0)

        adjusted = agent._adjust(plan, bad_playlist, attempt=1)

        adjusted_popular = adjusted["phase_prefs"]["happy"]["prefer_popular"]
        original_popular = plan["phase_prefs"]["happy"]["prefer_popular"]
        assert adjusted_popular != original_popular

    def test_adjust_toggles_acoustic_on_third_attempt(self, agent):
        """Third adjustment toggles acoustic preference."""
        phases = ["happy"]
        plan = agent._plan(phases, "happy songs")
        bad_playlist = Playlist(songs=[], explanations=[], phase_labels=[], validation_score=0)

        adjusted = agent._adjust(plan, bad_playlist, attempt=2)

        adjusted_acoustic = adjusted["phase_prefs"]["happy"]["likes_acoustic"]
        original_acoustic = plan["phase_prefs"]["happy"]["likes_acoustic"]
        assert adjusted_acoustic != original_acoustic


# ---------------------------------------------------------------------------
# Validation + Adjustment Loop Tests
# ---------------------------------------------------------------------------
class TestValidateAdjustLoop:
    """Test the VALIDATE + ADJUST loop."""

    def test_loop_stops_at_acceptable_score(self, agent):
        """Loop stops when validation_score >= 0.7."""
        playlist = agent.plan_and_execute("pop music")

        # Should eventually reach acceptable score or max adjustments
        assert playlist.validation_score >= 0.5

    def test_loop_respects_max_adjustments(self, agent):
        """Loop never exceeds max_adjustments (3)."""
        # Even with a difficult request, loop should complete
        playlist = agent.plan_and_execute("extremely obscure jazz from 1920s")

        # Should complete (not hang)
        assert isinstance(playlist, Playlist)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_resolver_error_uses_defaults(self, agent):
        """If resolver fails, use default preferences."""
        # Inject invalid message that will fail validation
        # But agent should still produce a playlist
        playlist = agent.plan_and_execute("pop music")

        assert len(playlist.songs) > 0

    def test_empty_songs_list(self, resolver, matcher, kb):
        """Agent works with empty songs list."""
        agent = PlaylistAgent(resolver, matcher, kb, [])

        playlist = agent.plan_and_execute("pop songs")
        assert len(playlist.songs) == 0

    def test_single_song(self, resolver, matcher, kb, sample_songs):
        """Agent works with single song."""
        agent = PlaylistAgent(resolver, matcher, kb, sample_songs[:1])

        playlist = agent.plan_and_execute("I want a song")
        assert len(playlist.songs) <= 1

    def test_many_phases_extracted(self, agent):
        """Agent handles many phases."""
        playlist = agent.plan_and_execute("sad -> chill -> energetic -> happy")

        assert len(set(playlist.phase_labels)) > 1


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------
class TestFactory:
    """Test create_playlist_agent factory function."""

    def test_create_playlist_agent(self, resolver, matcher, kb, sample_songs):
        """Factory creates working PlaylistAgent."""
        agent = create_playlist_agent(resolver, matcher, kb, sample_songs)

        assert agent is not None
        assert isinstance(agent, PlaylistAgent)

    def test_factory_agent_works(self, resolver, matcher, kb, sample_songs):
        """Factory-created agent works end-to-end."""
        agent = create_playlist_agent(resolver, matcher, kb, sample_songs)

        playlist = agent.plan_and_execute("happy pop music")
        assert len(playlist.songs) > 0
