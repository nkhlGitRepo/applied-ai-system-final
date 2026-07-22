"""
Tests for Phase 1 - Knowledge Base.

Covers construction/indexing, all retrieval functions, the similarity metric,
and the guardrails applied at index/retrieval time.
"""

import pytest

from src.phase1_knowledge_base import (
    KnowledgeBase,
    ArtistProfile,
    GenreKnowledge,
    SongKnowledge,
)
from src.guardrails import (
    validate_song_metadata,
    validate_retrieval_count,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _song(**overrides):
    """Build a valid song dict, overriding specific fields."""
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


# ---------------------------------------------------------------------------
# Construction & indexing
# ---------------------------------------------------------------------------
class TestConstruction:
    def test_indexes_all_valid_songs(self, kb, sample_songs):
        assert len(kb.songs) == len(sample_songs)
        assert kb.rejected_count == 0

    def test_drops_invalid_songs(self, sample_songs):
        bad = _song(id=99, title="Broken", energy=5.0)  # energy out of range
        kb = KnowledgeBase(sample_songs + [bad])
        assert kb.rejected_count == 1
        assert all(s["id"] != 99 for s in kb.songs)

    def test_from_csv_loads_real_catalog(self):
        kb = KnowledgeBase.from_csv("data/songs.csv")
        assert len(kb.songs) > 0
        assert kb.rejected_count == 0

    def test_empty_catalog(self):
        kb = KnowledgeBase([])
        assert kb.songs == []
        assert kb.retrieve_song_info("anything") is None


# ---------------------------------------------------------------------------
# song_similarity
# ---------------------------------------------------------------------------
class TestSongSimilarity:
    def test_identical_song_scores_one(self, kb, sample_songs):
        assert kb.song_similarity(sample_songs[0], sample_songs[0]) == pytest.approx(1.0)

    def test_similarity_bounded(self, kb, sample_songs):
        for a in sample_songs:
            for b in sample_songs:
                s = kb.song_similarity(a, b)
                assert 0.0 <= s <= 1.0

    def test_same_genre_more_similar_than_different(self, kb, sample_songs):
        pop_a, pop_b, rock = sample_songs[0], sample_songs[1], sample_songs[4]
        assert kb.song_similarity(pop_a, pop_b) > kb.song_similarity(pop_a, rock)


# ---------------------------------------------------------------------------
# retrieve_similar_songs
# ---------------------------------------------------------------------------
class TestRetrieveSimilarSongs:
    def test_excludes_reference_song(self, kb, sample_songs):
        results = kb.retrieve_similar_songs(sample_songs[0], count=5)
        assert all(s["id"] != sample_songs[0]["id"] for s in results)

    def test_respects_count(self, kb, sample_songs):
        assert len(kb.retrieve_similar_songs(sample_songs[0], count=2)) == 2

    def test_sorted_by_similarity_desc(self, kb, sample_songs):
        results = kb.retrieve_similar_songs(sample_songs[0], count=4)
        sims = [kb.song_similarity(sample_songs[0], s) for s in results]
        assert sims == sorted(sims, reverse=True)

    def test_most_similar_is_same_genre(self, kb, sample_songs):
        # Sunrise City's nearest neighbor should be the other pop song.
        top = kb.retrieve_similar_songs(sample_songs[0], count=1)[0]
        assert top["genre"] == "pop"

    def test_count_clamped_to_catalog(self, kb):
        results = kb.retrieve_similar_songs(_song(id=1), count=999)
        # Only 4 other songs share no id with id=1 (5 total minus the match).
        assert len(results) <= 4

    def test_bad_reference_returns_empty(self, kb):
        assert kb.retrieve_similar_songs("not a dict") == []


# ---------------------------------------------------------------------------
# retrieve_song_info
# ---------------------------------------------------------------------------
class TestRetrieveSongInfo:
    def test_returns_song_knowledge(self, kb):
        info = kb.retrieve_song_info("Sunrise City")
        assert isinstance(info, SongKnowledge)
        assert info.song["title"] == "Sunrise City"
        assert isinstance(info.artist_profile, ArtistProfile)
        assert isinstance(info.genre_context, GenreKnowledge)
        assert len(info.similar_songs) > 0

    def test_case_insensitive(self, kb):
        assert kb.retrieve_song_info("SUNRISE CITY") is not None
        assert kb.retrieve_song_info("  sunrise city  ") is not None

    def test_missing_title_returns_none(self, kb):
        assert kb.retrieve_song_info("Nonexistent Song") is None

    def test_empty_title_returns_none(self, kb):
        assert kb.retrieve_song_info("") is None


# ---------------------------------------------------------------------------
# retrieve_artist_profile
# ---------------------------------------------------------------------------
class TestRetrieveArtistProfile:
    def test_aggregates_multiple_songs(self, kb):
        profile = kb.retrieve_artist_profile("Neon Echo")
        assert profile.song_count == 2
        assert profile.primary_genre == "pop"
        assert set(profile.song_titles) == {"Sunrise City", "Neon Nights"}

    def test_energy_level_label(self, kb):
        # Neon Echo averages ~0.85 -> high.
        assert kb.retrieve_artist_profile("Neon Echo").energy_level == "high"
        # LoRoom is a single 0.42 song -> medium.
        assert kb.retrieve_artist_profile("LoRoom").energy_level == "medium"

    def test_case_insensitive(self, kb):
        assert kb.retrieve_artist_profile("neon echo") is not None

    def test_unknown_artist_returns_none(self, kb):
        assert kb.retrieve_artist_profile("Nobody") is None


# ---------------------------------------------------------------------------
# retrieve_genre_context
# ---------------------------------------------------------------------------
class TestRetrieveGenreContext:
    def test_energy_range(self, kb):
        ctx = kb.retrieve_genre_context("lofi")
        assert ctx.energy_range == (0.35, 0.42)
        assert ctx.song_count == 2

    def test_acoustic_label(self, kb):
        assert kb.retrieve_genre_context("lofi").acoustic_characteristics == \
            "predominantly acoustic"
        assert kb.retrieve_genre_context("pop").acoustic_characteristics == \
            "predominantly electronic/produced"

    def test_example_songs_capped_at_five(self, kb):
        ctx = kb.retrieve_genre_context("pop")
        assert len(ctx.example_songs) <= 5

    def test_unknown_genre_returns_none(self, kb):
        assert kb.retrieve_genre_context("polka") is None


# ---------------------------------------------------------------------------
# retrieve_comparable_profiles
# ---------------------------------------------------------------------------
class TestRetrieveComparableProfiles:
    def test_excludes_own_genre_by_default(self, kb):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.85, "likes_acoustic": False}
        profiles = kb.retrieve_comparable_profiles(prefs)
        assert all(p["favorite_genre"] != "pop" for p in profiles)

    def test_include_self(self, kb):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.85, "likes_acoustic": False}
        profiles = kb.retrieve_comparable_profiles(prefs, count=10, include_self=True)
        assert any(p["favorite_genre"] == "pop" for p in profiles)

    def test_ranked_by_similarity(self, kb):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.85, "likes_acoustic": False}
        profiles = kb.retrieve_comparable_profiles(prefs, count=5)
        sims = [p["similarity"] for p in profiles]
        assert sims == sorted(sims, reverse=True)

    def test_high_energy_user_matches_rock_over_lofi(self, kb):
        prefs = {"favorite_genre": "electronic", "favorite_mood": "intense",
                 "target_energy": 0.92, "likes_acoustic": False}
        profiles = kb.retrieve_comparable_profiles(prefs, count=5)
        ranks = {p["favorite_genre"]: i for i, p in enumerate(profiles)}
        assert ranks["rock"] < ranks["lofi"]

    def test_count_respected(self, kb):
        prefs = {"favorite_genre": "pop", "target_energy": 0.5}
        assert len(kb.retrieve_comparable_profiles(prefs, count=1)) == 1

    def test_empty_prefs_does_not_crash(self, kb):
        assert isinstance(kb.retrieve_comparable_profiles({}), list)


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------
class TestGuardrails:
    def test_validate_song_metadata_accepts_valid(self):
        assert validate_song_metadata(_song()) is True

    def test_validate_song_metadata_rejects_missing_field(self):
        song = _song()
        del song["genre"]
        assert validate_song_metadata(song) is False

    def test_validate_song_metadata_rejects_out_of_range(self):
        assert validate_song_metadata(_song(energy=1.5)) is False
        assert validate_song_metadata(_song(popularity=200)) is False
        assert validate_song_metadata(_song(release_decade=1500)) is False

    def test_validate_song_metadata_rejects_non_dict(self):
        assert validate_song_metadata("not a dict") is False
        assert validate_song_metadata(None) is False

    def test_validate_song_metadata_rejects_bool_as_number(self):
        # bool is a subclass of int; must not be accepted as energy.
        assert validate_song_metadata(_song(energy=True)) is False

    def test_validate_retrieval_count_clamps(self):
        assert validate_retrieval_count(0) == 1
        assert validate_retrieval_count(999) == 50
        assert validate_retrieval_count(5) == 5

    def test_validate_retrieval_count_handles_bad_input(self):
        assert validate_retrieval_count("abc") == 1
        assert validate_retrieval_count(None) == 1
