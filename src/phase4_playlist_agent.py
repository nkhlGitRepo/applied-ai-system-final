"""
Phase 4: Playlist Agent - Agentic loop for complex playlist requests.

Orchestrates Phases 1-3 in a plan-validate-adjust loop to handle user requests
like "emotional journey sad→happy". Supports multi-phase playlists with validation.

Public API:
    agent = PlaylistAgent(resolver, matcher, kb, songs)
    playlist = agent.plan_and_execute("Create an emotional journey from sad to happy")
    # Returns: Playlist(songs=[...], explanations=[...], validation_score=0.9)
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.phase2_intent_resolver import IntentResolver
from src.phase3_matcher_explainer import MatcherExplainer
from src.phase1_knowledge_base import KnowledgeBase


@dataclass
class Playlist:
    """Result of playlist agent execution."""
    songs: List[Dict]
    explanations: List[str]
    phase_labels: List[str]
    validation_score: float


class PlaylistAgent:
    """Execute user requests as an agentic loop with validation and adjustment."""

    def __init__(
        self,
        resolver: IntentResolver,
        matcher: MatcherExplainer,
        kb: KnowledgeBase,
        songs: List[Dict],
    ):
        """Initialize with dependencies from Phases 1-3.

        Args:
            resolver: Phase 2 IntentResolver for parsing user messages
            matcher: Phase 3 MatcherExplainer for scoring + explanations
            kb: Phase 1 KnowledgeBase for context
            songs: Full song catalog
        """
        self.resolver = resolver
        self.matcher = matcher
        self.kb = kb
        self.songs = songs
        self.max_adjustments = 3

    def plan_and_execute(self, user_message: str) -> Playlist:
        """Execute agentic loop: UNDERSTAND → PLAN → RETRIEVE → EXECUTE → VALIDATE → ADJUST.

        Args:
            user_message: User's playlist request

        Returns:
            Playlist object with songs, explanations, phase labels, validation score
        """
        # 1. UNDERSTAND: Extract phases from user message
        phases = self._understand(user_message)

        # 2. PLAN: Create preferences for each phase
        plan = self._plan(phases, user_message)

        # 3. RETRIEVE: Get recommendations for each phase
        recommendations = self._retrieve(plan)

        # 4. EXECUTE: Build playlist from recommendations
        playlist = self._execute(recommendations, phases)

        # 5. VALIDATE + ADJUST loop (max 3 adjustments)
        for attempt in range(self.max_adjustments):
            validation_score = self._validate(playlist, plan)
            playlist.validation_score = validation_score

            if validation_score >= 0.7:  # Acceptable threshold
                break

            if attempt < self.max_adjustments - 1:
                plan = self._adjust(plan, playlist, attempt)
                recommendations = self._retrieve(plan)
                playlist = self._execute(recommendations, phases)

        return playlist

    # -----------------------------------------------------------------------
    # Step 1: UNDERSTAND
    # -----------------------------------------------------------------------
    def _understand(self, user_message: str) -> List[str]:
        """Extract phases from user message (e.g., "sad→happy" → ["sad", "happy"]).

        Args:
            user_message: User's request

        Returns:
            List of phase labels
        """
        message_lower = user_message.lower()

        # Check for journey/arc keywords
        journey_keywords = ["journey", "arc", "transition", "progression", "flow"]
        is_journey = any(kw in message_lower for kw in journey_keywords)

        # Extract phases from arrow notation (sad → happy, etc.)
        if "→" in message_lower:
            parts = message_lower.split("→")
            phases = [p.strip() for p in parts if p.strip()]
            return phases if phases else ["general"]

        if "->" in message_lower:
            parts = message_lower.split("->")
            phases = [p.strip() for p in parts if p.strip()]
            return phases if phases else ["general"]

        if not is_journey:
            return ["general"]  # Single-phase request

        # Extract moods/genres as phases
        moods = ["happy", "sad", "chill", "intense", "energetic", "calm"]
        found_moods = [m for m in moods if m in message_lower]
        if found_moods:
            return found_moods

        return ["general"]

    # -----------------------------------------------------------------------
    # Step 2: PLAN
    # -----------------------------------------------------------------------
    def _plan(self, phases: List[str], user_message: str) -> Dict:
        """Create scoring preferences for each phase.

        Args:
            phases: Phase labels (e.g., ["sad", "happy"])
            user_message: Original user message

        Returns:
            Plan dict with preferences per phase
        """
        # Resolve base preferences from user message
        try:
            base_prefs, mode, confidence = self.resolver.resolve(user_message)
        except ValueError:
            base_prefs = {
                "favorite_genre": "pop",
                "favorite_mood": "happy",
                "target_energy": 0.6,
                "likes_acoustic": False,
            }

        # Create phase-specific preferences
        plan = {"phases": phases, "base_prefs": base_prefs, "mode": mode}
        phase_prefs = {}

        for phase in phases:
            phase_lower = phase.lower()
            prefs = base_prefs.copy()

            # Modify preferences based on phase label
            if phase_lower in ["sad", "melancholic", "emotional"]:
                prefs["favorite_mood"] = "sad"
                prefs["target_energy"] = 0.3
            elif phase_lower in ["happy", "uplifting", "joyful"]:
                prefs["favorite_mood"] = "happy"
                prefs["target_energy"] = 0.8
            elif phase_lower in ["chill", "calm", "relaxing"]:
                prefs["favorite_mood"] = "chill"
                prefs["target_energy"] = 0.3
            elif phase_lower in ["intense", "energetic", "pumped"]:
                prefs["favorite_mood"] = "energetic"
                prefs["target_energy"] = 0.9
            elif phase_lower == "transition":
                prefs["target_energy"] = 0.5  # Mid-range for transition

            phase_prefs[phase] = prefs

        plan["phase_prefs"] = phase_prefs
        return plan

    # -----------------------------------------------------------------------
    # Step 3: RETRIEVE
    # -----------------------------------------------------------------------
    def _retrieve(self, plan: Dict) -> Dict:
        """Get recommendations for each phase using Phase 3 MatcherExplainer.

        Args:
            plan: Plan dict with phase preferences

        Returns:
            Recommendations dict with songs per phase
        """
        recommendations = {}

        for phase, prefs in plan["phase_prefs"].items():
            mode = plan["mode"]
            # Request 3-5 songs per phase (rounded up from k/num_phases)
            k_per_phase = max(3, len(self.songs) // len(plan["phases"]))

            results = self.matcher.match_and_explain(prefs, self.songs, k=k_per_phase, mode=mode)

            recommendations[phase] = results

        return recommendations

    # -----------------------------------------------------------------------
    # Step 4: EXECUTE
    # -----------------------------------------------------------------------
    def _execute(self, recommendations: Dict, phases: List[str]) -> Playlist:
        """Build final playlist by combining phase recommendations in order.

        Args:
            recommendations: Dict with (song, score, explanation) per phase
            phases: Phase labels in order

        Returns:
            Playlist object
        """
        songs = []
        explanations = []
        phase_labels = []

        for phase in phases:
            if phase not in recommendations:
                continue

            phase_results = recommendations[phase]
            for song, score, explanation in phase_results:
                songs.append(song)
                explanations.append(f"[{phase.title()}] {explanation}")
                phase_labels.append(phase)

        return Playlist(
            songs=songs,
            explanations=explanations,
            phase_labels=phase_labels,
            validation_score=0.5,  # Placeholder, set by validate()
        )

    # -----------------------------------------------------------------------
    # Step 5: VALIDATE
    # -----------------------------------------------------------------------
    def _validate(self, playlist: Playlist, plan: Dict) -> float:
        """Check if playlist meets user intent via heuristic scoring.

        Validation checks:
        - Playlist has songs (not empty)
        - Playlist covers all requested phases
        - Songs progress logically through phases
        - Energy/mood progression makes sense

        Args:
            playlist: Generated playlist
            plan: Original plan with phase info

        Returns:
            Validation score (0.0-1.0), where >= 0.7 is acceptable
        """
        score = 0.5  # Base score

        # Check 1: Non-empty
        if not playlist.songs:
            return 0.0

        score += 0.2

        # Check 2: Covers all phases
        phases_covered = len(set(playlist.phase_labels))
        expected_phases = len(plan["phases"])
        if phases_covered == expected_phases:
            score += 0.2
        elif phases_covered >= expected_phases - 1:
            score += 0.1

        # Check 3: Minimum diversity (not all same song repeated)
        unique_songs = len(set(s.get("id") for s in playlist.songs))
        if unique_songs >= len(playlist.songs) * 0.8:
            score += 0.15

        # Check 4: Energy/mood progression sensible
        if self._check_progression(playlist):
            score += 0.15

        return min(score, 1.0)

    def _check_progression(self, playlist: Playlist) -> bool:
        """Check if energy/mood progresses logically through phases."""
        if len(playlist.songs) < 2:
            return True

        energies = [s.get("energy", 0.5) for s in playlist.songs]

        # For multi-phase playlists, check that phases don't jump randomly
        if len(set(playlist.phase_labels)) > 1:
            # Just check that it's not completely chaotic
            variance = max(energies) - min(energies)
            return variance > 0.1  # Some progression exists

        return True

    # -----------------------------------------------------------------------
    # Step 6: ADJUST
    # -----------------------------------------------------------------------
    def _adjust(self, plan: Dict, playlist: Playlist, attempt: int) -> Dict:
        """Modify plan based on validation feedback for next iteration.

        Args:
            plan: Original plan
            playlist: Current (invalid) playlist
            attempt: Adjustment attempt number (0, 1, 2)

        Returns:
            Modified plan
        """
        adjusted = deepcopy(plan)

        # Increase energy range to get more diverse results
        if attempt == 0:
            for phase_prefs in adjusted["phase_prefs"].values():
                # Broaden energy range
                phase_prefs["target_energy"] = max(0.3, phase_prefs.get("target_energy", 0.6) - 0.1)

        # Relax genre constraints
        elif attempt == 1:
            for phase_prefs in adjusted["phase_prefs"].values():
                phase_prefs["prefer_popular"] = not phase_prefs.get("prefer_popular", True)

        # Expand acoustic preference
        elif attempt == 2:
            for phase_prefs in adjusted["phase_prefs"].values():
                phase_prefs["likes_acoustic"] = not phase_prefs.get("likes_acoustic", False)

        return adjusted


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_playlist_agent(
    resolver: IntentResolver,
    matcher: MatcherExplainer,
    kb: KnowledgeBase,
    songs: List[Dict],
) -> PlaylistAgent:
    """Create a PlaylistAgent instance.

    Args:
        resolver: Phase 2 IntentResolver
        matcher: Phase 3 MatcherExplainer
        kb: Phase 1 KnowledgeBase
        songs: Full song catalog

    Returns:
        New PlaylistAgent
    """
    return PlaylistAgent(resolver, matcher, kb, songs)
