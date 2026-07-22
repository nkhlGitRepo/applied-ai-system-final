"""
Knowledge Base - Phase 1 of the Music Advisor (RAG foundation).

Indexes the song catalog and provides retrieval functions that supply rich
context (song info, similar songs, artist profiles, genre characteristics, and
comparable user profiles) to the rest of the advisor pipeline.

Design notes:
  - Consumes the same `List[Dict]` song format produced by
    `recommender.load_songs`, so it drops straight into the existing system.
  - Reuses the similarity functions already defined in `recommender.py`
    (vocal / production / emotional-arc) rather than re-implementing them.
  - Every song is validated at index time and every retrieval count is clamped,
    per GUARDRAILS.md sections 3.1 and 3.2.

Public API:
    kb = KnowledgeBase(songs)                 # or KnowledgeBase.from_csv(path)
    kb.retrieve_song_info(title)              -> SongKnowledge | None
    kb.retrieve_similar_songs(song, count=5)  -> List[Dict]
    kb.retrieve_artist_profile(artist)        -> ArtistProfile | None
    kb.retrieve_genre_context(genre)          -> GenreKnowledge | None
    kb.retrieve_comparable_profiles(prefs)    -> List[Dict]
    kb.song_similarity(song_a, song_b)        -> float
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.recommender import (
    load_songs,
    vocal_style_similarity,
    production_quality_similarity,
    emotional_arc_similarity,
)
from src.guardrails import (
    validate_song_metadata,
    validate_retrieval_count,
)


# ---------------------------------------------------------------------------
# Similarity weighting
# ---------------------------------------------------------------------------
# Weights sum to 1.0 so song_similarity() always returns a value in [0.0, 1.0].
_SIMILARITY_WEIGHTS = {
    "genre": 0.30,
    "mood": 0.20,
    "energy": 0.20,
    "valence": 0.10,
    "danceability": 0.05,
    "acousticness": 0.05,
    "vocal_style": 0.05,
    "production": 0.03,
    "emotional_arc": 0.02,
}


# ---------------------------------------------------------------------------
# Data structures returned by retrieval functions
# ---------------------------------------------------------------------------
@dataclass
class ArtistProfile:
    """Aggregated knowledge about a single artist, derived from their songs."""
    name: str
    song_count: int
    genres: List[str]
    primary_genre: str
    typical_moods: List[str]
    avg_energy: float
    energy_level: str          # "high" | "medium" | "low"
    vocal_styles: List[str]
    primary_vocal_style: str
    avg_popularity: float
    decades_active: List[int]
    song_titles: List[str]


@dataclass
class GenreKnowledge:
    """Characteristics of a genre, aggregated across the catalog."""
    name: str
    song_count: int
    typical_moods: List[str]
    energy_range: Tuple[float, float]
    avg_energy: float
    avg_acousticness: float
    acoustic_characteristics: str
    common_vocal_styles: List[str]
    example_songs: List[str]


@dataclass
class SongKnowledge:
    """Everything the explainer needs to reason about one song."""
    song: Dict
    artist_profile: Optional[ArtistProfile]
    genre_context: Optional[GenreKnowledge]
    similar_songs: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
class KnowledgeBase:
    """Indexes songs and serves retrieval queries for the RAG pipeline."""

    def __init__(self, songs: List[Dict]):
        """Build indexes from a list of song dicts.

        Songs that fail metadata validation are dropped (not served), keeping
        the knowledge base safe by construction.

        Args:
            songs: List of song dicts (see recommender.load_songs).
        """
        # Content filtering at index time (GUARDRAILS.md 3.1).
        self.songs: List[Dict] = [s for s in songs if validate_song_metadata(s)]
        self.rejected_count: int = len(songs) - len(self.songs)

        # Lookup indexes (keyed lowercase for case-insensitive retrieval).
        self._by_title: Dict[str, Dict] = {}
        self._by_artist: Dict[str, List[Dict]] = {}
        self._by_genre: Dict[str, List[Dict]] = {}

        for song in self.songs:
            self._by_title[song["title"].lower()] = song
            self._by_artist.setdefault(song["artist"].lower(), []).append(song)
            self._by_genre.setdefault(song["genre"].lower(), []).append(song)

    # -- constructors -------------------------------------------------------
    @classmethod
    def from_csv(cls, csv_path: str) -> "KnowledgeBase":
        """Convenience constructor that loads songs from a CSV file."""
        return cls(load_songs(csv_path))

    # -- similarity ---------------------------------------------------------
    def song_similarity(self, song_a: Dict, song_b: Dict) -> float:
        """Compute a 0.0-1.0 similarity score between two songs.

        Combines categorical matches (genre, mood), numeric closeness
        (energy, valence, danceability, acousticness), and the shared
        similarity functions for vocal style, production, and emotional arc.
        """
        score = 0.0

        # Categorical matches.
        score += _SIMILARITY_WEIGHTS["genre"] * (
            1.0 if song_a.get("genre") == song_b.get("genre") else 0.0
        )
        score += _SIMILARITY_WEIGHTS["mood"] * (
            1.0 if song_a.get("mood") == song_b.get("mood") else 0.0
        )

        # Numeric closeness on 0-1 fields.
        for field_name in ("energy", "valence", "danceability", "acousticness"):
            score += _SIMILARITY_WEIGHTS[field_name] * _closeness(
                song_a.get(field_name), song_b.get(field_name)
            )

        # Categorical-similarity helpers reused from the recommender.
        score += _SIMILARITY_WEIGHTS["vocal_style"] * vocal_style_similarity(
            song_a.get("vocal_style", ""), song_b.get("vocal_style", "")
        )
        score += _SIMILARITY_WEIGHTS["production"] * production_quality_similarity(
            song_a.get("production_quality", ""), song_b.get("production_quality", "")
        )
        score += _SIMILARITY_WEIGHTS["emotional_arc"] * emotional_arc_similarity(
            song_a.get("emotional_arc", ""), song_b.get("emotional_arc", "")
        )

        return round(score, 4)

    # -- retrieval ----------------------------------------------------------
    def retrieve_song_info(self, song_title: str) -> Optional[SongKnowledge]:
        """Return full context for a song by title (case-insensitive).

        Returns None if the title is not in the catalog.
        """
        if not song_title:
            return None

        song = self._by_title.get(song_title.strip().lower())
        if song is None:
            return None

        return SongKnowledge(
            song=song,
            artist_profile=self.retrieve_artist_profile(song["artist"]),
            genre_context=self.retrieve_genre_context(song["genre"]),
            similar_songs=self.retrieve_similar_songs(song, count=5),
        )

    def retrieve_similar_songs(self, song: Dict, count: int = 5) -> List[Dict]:
        """Return the `count` songs most similar to `song`.

        The reference song itself is excluded. Ties break by popularity then
        title for deterministic ordering. `count` is clamped to a safe range.
        """
        count = validate_retrieval_count(count)
        if not isinstance(song, dict):
            return []

        ref_id = song.get("id")
        scored = [
            (candidate, self.song_similarity(song, candidate))
            for candidate in self.songs
            if candidate.get("id") != ref_id
        ]

        scored.sort(
            key=lambda pair: (
                pair[1],
                pair[0].get("popularity", 0),
                pair[0].get("title", ""),
            ),
            reverse=True,
        )
        return [candidate for candidate, _ in scored[:count]]

    def retrieve_artist_profile(self, artist_name: str) -> Optional[ArtistProfile]:
        """Return an aggregated profile for an artist (case-insensitive)."""
        if not artist_name:
            return None

        artist_songs = self._by_artist.get(artist_name.strip().lower())
        if not artist_songs:
            return None

        genres = _by_frequency(s["genre"] for s in artist_songs)
        moods = _by_frequency(s["mood"] for s in artist_songs)
        vocals = _by_frequency(s["vocal_style"] for s in artist_songs)
        avg_energy = _mean(s["energy"] for s in artist_songs)

        return ArtistProfile(
            name=artist_songs[0]["artist"],
            song_count=len(artist_songs),
            genres=genres,
            primary_genre=genres[0],
            typical_moods=moods,
            avg_energy=round(avg_energy, 3),
            energy_level=_energy_label(avg_energy),
            vocal_styles=vocals,
            primary_vocal_style=vocals[0],
            avg_popularity=round(_mean(s["popularity"] for s in artist_songs), 1),
            decades_active=sorted({s["release_decade"] for s in artist_songs}),
            song_titles=[s["title"] for s in artist_songs],
        )

    def retrieve_genre_context(self, genre_name: str) -> Optional[GenreKnowledge]:
        """Return aggregated characteristics for a genre (case-insensitive)."""
        if not genre_name:
            return None

        genre_songs = self._by_genre.get(genre_name.strip().lower())
        if not genre_songs:
            return None

        energies = [s["energy"] for s in genre_songs]
        avg_acoustic = _mean(s["acousticness"] for s in genre_songs)

        return GenreKnowledge(
            name=genre_songs[0]["genre"],
            song_count=len(genre_songs),
            typical_moods=_by_frequency(s["mood"] for s in genre_songs),
            energy_range=(round(min(energies), 2), round(max(energies), 2)),
            avg_energy=round(_mean(energies), 3),
            avg_acousticness=round(avg_acoustic, 3),
            acoustic_characteristics=_acoustic_label(avg_acoustic),
            common_vocal_styles=_by_frequency(s["vocal_style"] for s in genre_songs),
            example_songs=[s["title"] for s in genre_songs[:5]],
        )

    def retrieve_comparable_profiles(
        self, user_prefs: Dict, count: int = 3, include_self: bool = False
    ) -> List[Dict]:
        """Return archetypal user profiles similar to `user_prefs`.

        Without real user history, archetypes are derived from the catalog: one
        representative profile per genre. They are ranked by closeness to the
        supplied preferences, enabling "listeners like you also enjoy..." style
        suggestions. Each returned dict is user_prefs-shaped plus a `label` and
        `similarity` score.

        Args:
            user_prefs: The active user's preference dict.
            count: Number of comparable profiles to return (clamped).
            include_self: If False (default), skip the archetype whose genre
                matches the user's favorite genre.
        """
        count = validate_retrieval_count(count)
        user_prefs = user_prefs or {}
        user_genre = str(user_prefs.get("favorite_genre", "")).lower()

        scored: List[Tuple[float, Dict]] = []
        for genre, archetype in self._build_genre_archetypes().items():
            if not include_self and genre == user_genre:
                continue
            similarity = _profile_similarity(user_prefs, archetype)
            scored.append((similarity, archetype))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        results = []
        for similarity, archetype in scored[:count]:
            enriched = dict(archetype)
            enriched["similarity"] = round(similarity, 3)
            results.append(enriched)
        return results

    # -- internal helpers ---------------------------------------------------
    def _build_genre_archetypes(self) -> Dict[str, Dict]:
        """Build one representative user profile per genre from the catalog."""
        archetypes: Dict[str, Dict] = {}
        for genre_key, genre_songs in self._by_genre.items():
            avg_energy = _mean(s["energy"] for s in genre_songs)
            avg_acoustic = _mean(s["acousticness"] for s in genre_songs)
            top_mood = _by_frequency(s["mood"] for s in genre_songs)[0]
            display_genre = genre_songs[0]["genre"]
            archetypes[genre_key] = {
                "label": f"{display_genre} listener",
                "favorite_genre": display_genre,
                "favorite_mood": top_mood,
                "target_energy": round(avg_energy, 2),
                "likes_acoustic": avg_acoustic > 0.5,
            }
        return archetypes


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
def _closeness(a: Optional[float], b: Optional[float]) -> float:
    """Return 1 - |a - b| for two 0-1 values; 0.0 if either is missing."""
    if a is None or b is None:
        return 0.0
    return max(0.0, 1.0 - abs(float(a) - float(b)))


def _mean(values) -> float:
    """Arithmetic mean of an iterable; 0.0 when empty."""
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _by_frequency(values) -> List[str]:
    """Return unique values ordered from most to least frequent."""
    counts = Counter(values)
    return [value for value, _ in counts.most_common()]


def _energy_label(avg_energy: float) -> str:
    """Bucket an average energy into a human-readable level."""
    if avg_energy >= 0.7:
        return "high"
    if avg_energy >= 0.4:
        return "medium"
    return "low"


def _acoustic_label(avg_acousticness: float) -> str:
    """Describe a genre's acoustic character from its average acousticness."""
    if avg_acousticness >= 0.6:
        return "predominantly acoustic"
    if avg_acousticness <= 0.3:
        return "predominantly electronic/produced"
    return "mixed acoustic and electronic"


def _profile_similarity(user_prefs: Dict, archetype: Dict) -> float:
    """Score how close an archetype is to the user's preferences (0.0-1.0)."""
    score = 0.0

    # Mood match (0.35).
    if user_prefs.get("favorite_mood") == archetype.get("favorite_mood"):
        score += 0.35

    # Energy closeness (0.40).
    score += 0.40 * _closeness(
        user_prefs.get("target_energy"), archetype.get("target_energy")
    )

    # Acoustic preference match (0.25).
    if user_prefs.get("likes_acoustic") == archetype.get("likes_acoustic"):
        score += 0.25

    return score
