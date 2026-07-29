"""
Phase 3: Matcher-Explainer - Score songs + generate RAG-enhanced explanations.

Orchestrates GMEWS scoring with RAG context retrieval to produce rich,
interpretable recommendations. Integrates Phase 1 (Knowledge Base) for context.

Public API:
    kb = KnowledgeBase.from_csv("data/songs.csv")
    matcher = MatcherExplainer(kb)
    results = matcher.match_and_explain(
        user_prefs={"genre": "pop", "mood": "happy", ...},
        songs=songs,
        k=5,
        mode="genre-first"
    )
    # Returns: [(song_dict, score_float, explanation_str), ...]
"""

from typing import Dict, List, Optional, Tuple

from src.recommender import recommend_songs, SCORING_MODES
from src.phase1_knowledge_base import KnowledgeBase, SongKnowledge


class MatcherExplainer:
    """Score songs with GMEWS + generate RAG-enhanced explanations."""

    def __init__(self, knowledge_base: KnowledgeBase):
        """Initialize with a knowledge base for RAG context retrieval.

        Args:
            knowledge_base: Phase 1 KnowledgeBase instance
        """
        self.kb = knowledge_base

    def match_and_explain(
        self,
        user_prefs: Dict,
        songs: List[Dict],
        k: int = 5,
        mode: str = "genre-first",
    ) -> List[Tuple[Dict, float, str]]:
        """Score and explain top-k recommendations using RAG context.

        Workflow:
        1. Score all songs via GMEWS (recommender)
        2. Select top-k by score
        3. Enrich each with RAG context (artist, genre, similar songs)
        4. Generate explanation combining score reasoning + context

        Args:
            user_prefs: User preferences dict (from Phase 2 resolver)
            songs: List of song dicts (from recommender.load_songs)
            k: Number of recommendations to return (default 5)
            mode: Scoring mode (default "genre-first")

        Returns:
            List of (song_dict, score, explanation_str) tuples, ranked by score
        """
        # 1. Score songs via GMEWS
        scored = self._score_songs(user_prefs, songs, k, mode)

        # 2. Enrich with RAG context
        enriched = [self._enrich_with_context(song, score) for song, score, _ in scored]

        # 3. Generate explanations
        results = [
            (song_data["song"], song_data["score"], self._generate_explanation(song_data))
            for song_data in enriched
        ]

        return results

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------
    def _score_songs(
        self,
        user_prefs: Dict,
        songs: List[Dict],
        k: int,
        mode: str,
    ) -> List[Tuple[Dict, float, str]]:
        """Score songs using GMEWS recommender (Phase 1 compatible).

        Args:
            user_prefs: User preferences dict
            songs: All songs to score
            k: Return top-k
            mode: Scoring mode name

        Returns:
            List of (song, score, explanation) tuples from recommender
        """
        # Validate mode exists
        if mode not in SCORING_MODES:
            mode = "genre-first"  # Fallback to default

        # Call existing recommender
        scored = recommend_songs(user_prefs, songs, k=k, mode=mode)

        return scored

    def _enrich_with_context(
        self,
        song: Dict,
        score: float,
    ) -> Dict:
        """Retrieve RAG context for a song using Phase 1 Knowledge Base.

        Args:
            song: Song dict
            score: GMEWS score

        Returns:
            Enriched dict with song, score, and RAG context
        """
        # Retrieve full context from KB
        song_title = song.get("title", "")
        rag_context = self.kb.retrieve_song_info(song_title)

        return {
            "song": song,
            "score": score,
            "rag_context": rag_context,
        }

    def _generate_explanation(self, song_data: Dict) -> str:
        """Generate explanation combining score reasoning + RAG context.

        Args:
            song_data: Dict with song, score, rag_context

        Returns:
            Human-readable explanation string
        """
        song = song_data["song"]
        score = song_data["score"]
        rag_context = song_data["rag_context"]

        # Build explanation from multiple sources
        parts = []

        # 1. Score reasoning (what GMEWS valued)
        parts.append(self._score_reasoning(song, score))

        # 2. Artist context (from RAG)
        if rag_context and rag_context.artist_profile:
            parts.append(self._artist_reasoning(rag_context.artist_profile))

        # 3. Genre context (from RAG)
        if rag_context and rag_context.genre_context:
            parts.append(self._genre_reasoning(rag_context.genre_context))

        # 4. Similar songs (from RAG)
        if rag_context and rag_context.similar_songs:
            parts.append(self._similarity_reasoning(rag_context.similar_songs))

        return " ".join(parts)

    def _score_reasoning(self, song: Dict, score: float) -> str:
        """Extract key scoring factors from song attributes."""
        if not song:
            return ""

        genre = song.get("genre", "Unknown")
        mood = song.get("mood", "Unknown")
        energy = song.get("energy", 0)

        return f"Score {score:.2f}: {genre.title()} song with {mood} mood ({energy:.1f} energy)."

    def _artist_reasoning(self, artist_profile) -> str:
        """Generate reasoning about artist consistency."""
        artist = artist_profile.name
        genres = ", ".join(artist_profile.genres[:2]) if artist_profile.genres else "unknown"
        energy_level = artist_profile.energy_level

        return f"{artist} consistently produces {energy_level}-energy music in {genres}."

    def _genre_reasoning(self, genre_context) -> str:
        """Generate reasoning about genre characteristics."""
        genre = genre_context.name
        energy_min, energy_max = genre_context.energy_range
        moods = ", ".join(genre_context.typical_moods[:2]) if genre_context.typical_moods else "varied"

        return f"{genre.title()} typically features {moods} moods with energy {energy_min:.2f}-{energy_max:.2f}."

    def _similarity_reasoning(self, similar_songs: List[Dict]) -> str:
        """Reference similar songs for context."""
        if not similar_songs:
            return ""

        titles = [s.get("title", "Unknown") for s in similar_songs[:2]]
        song_list = " and ".join(titles) if len(titles) > 1 else titles[0]

        return f"Similar to {song_list}."


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_matcher_explainer(knowledge_base: KnowledgeBase) -> MatcherExplainer:
    """Create a MatcherExplainer instance.

    Args:
        knowledge_base: Phase 1 KnowledgeBase instance

    Returns:
        New MatcherExplainer
    """
    return MatcherExplainer(knowledge_base)
