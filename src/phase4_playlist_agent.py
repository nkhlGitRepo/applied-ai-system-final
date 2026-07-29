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

    @staticmethod
    def _validate_playlist_size(k: int) -> None:
        """Validate playlist size is in valid range (1-100).

        Args:
            k: Playlist size to validate

        Raises:
            ValueError: If k is not an integer or outside 1-100 range
        """
        if not isinstance(k, int) or k < 1:
            raise ValueError(f"Playlist size must be at least 1, got {k}")
        if k > 100:
            raise ValueError(f"Playlist size cannot exceed 100, got {k}")

    def plan_and_execute(self, user_message: str, k: int = 10) -> Playlist:
        """Execute agentic loop: UNDERSTAND → PLAN → RETRIEVE → EXECUTE → VALIDATE → ADJUST.

        Args:
            user_message: User's playlist request
            k: Total playlist size (default 10). Clamped to 1-100 and available songs.

        Returns:
            Playlist object with songs, explanations, phase labels, validation score

        Raises:
            ValueError: If k is not an integer or is invalid (not in 1-100 range)
        """
        # Validate and normalize playlist size
        self._validate_playlist_size(k)
        k = min(k, len(self.songs))

        # 1. UNDERSTAND: Extract phases from user message
        phases = self._understand(user_message)

        # 2. PLAN: Create preferences for each phase
        plan = self._plan(phases, user_message)
        plan["k"] = k

        # 3. RETRIEVE: Get recommendations for each phase
        recommendations = self._retrieve(plan)

        # 4. EXECUTE: Build playlist from recommendations (trim to target k)
        playlist = self._execute(recommendations, phases, target_k=k)

        # 5. VALIDATE + ADJUST loop (max 3 attempts)
        # Early exit if no songs: validation will always be 0.0, adjustments won't help
        if not self.songs:
            playlist.validation_score = 0.0
            return playlist

        for attempt in range(self.max_adjustments):
            validation_score = self._validate(playlist, plan)
            playlist.validation_score = validation_score

            if validation_score >= 0.7:
                break

            if attempt < self.max_adjustments - 1:
                plan = self._adjust(plan, playlist, attempt)
                recommendations = self._retrieve(plan)
                playlist = self._execute(recommendations, phases, target_k=k)

        return playlist

    # -----------------------------------------------------------------------
    # Step 1: UNDERSTAND
    # -----------------------------------------------------------------------
    def _understand(self, user_message: str) -> List[str]:
        """Extract phases from user message using multiple strategies.

        Recognizes:
        - Arrow notation: "sad → happy"
        - "Starting/beginning with X, ending with Y" patterns
        - "From X to Y" patterns
        - Playlist type keywords: "workout", "dinner", "study", "party", "focus"

        Args:
            user_message: User's request

        Returns:
            List of phase labels
        """
        message_lower = user_message.lower()

        # Strategy 1: Arrow notation (explicit)
        if "→" in message_lower:
            parts = message_lower.split("→")
            phases = [p.strip() for p in parts if p.strip()]
            return phases if phases else ["general"]

        if "->" in message_lower:
            parts = message_lower.split("->")
            phases = [p.strip() for p in parts if p.strip()]
            return phases if phases else ["general"]

        # Strategy 2: "starting/beginning with X and ending with Y" pattern
        if ("start" in message_lower or "begin" in message_lower) and "end" in message_lower:
            # Extract phrases between "starting/beginning with" and "ending with"
            import re
            match = re.search(
                r'(?:start|begin)ing?\s+with\s+([^,]+?)(?:\s+and\s+)?(?:and\s+)?ending\s+with\s+(.+?)(?:\.|$)',
                message_lower
            )
            if match:
                start_phase = match.group(1).strip()
                end_phase = match.group(2).strip()
                return [start_phase, end_phase]

        # Strategy 3: "from X to Y" pattern
        if " from " in message_lower and " to " in message_lower:
            import re
            match = re.search(r'from\s+([^,]+?)\s+to\s+(.+?)(?:\.|$)', message_lower)
            if match:
                start_phase = match.group(1).strip()
                end_phase = match.group(2).strip()
                return [start_phase, end_phase]

        # Strategy 4: Playlist type keywords with implied journey
        playlist_type_journeys = {
            "workout": ["energetic", "intense"],
            "dinner": ["uplifting", "chill"],
            "lunch": ["uplifting", "chill"],
            "breakfast": ["calm", "energetic"],
            "brunch": ["calm", "uplifting"],
            "study": ["calm", "focused"],
            "focus": ["calm", "focused"],
            "work": ["calm", "focused"],
            "party": ["energetic", "uplifting"],
            "relax": ["calm", "chill"],
            "sleep": ["calm", "meditative"],
            "morning": ["calm", "energetic"],
            "evening": ["uplifting", "calm"],
            "night": ["chill", "meditative"],
            "chill": ["chill", "relaxed"],
            "drive": ["calm", "energetic"],
            "commute": ["calm", "focused"],
        }

        for playlist_type, phases in playlist_type_journeys.items():
            if playlist_type in message_lower:
                return phases

        # Strategy 5: Check for explicit journey keywords
        journey_keywords = ["journey", "arc", "transition", "progression", "flow"]
        is_journey = any(kw in message_lower for kw in journey_keywords)

        if is_journey:
            # Extract moods/genres as phases if journey keyword present
            moods = ["happy", "sad", "chill", "intense", "energetic", "calm", "focused"]
            found_moods = [m for m in moods if m in message_lower]
            if found_moods:
                return found_moods

        # Default: single-phase request
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
            if phase_lower in ["sad", "melancholic", "emotional", "somber", "dark"]:
                prefs["favorite_mood"] = "sad"
                prefs["target_energy"] = 0.3
                prefs["likes_acoustic"] = True
                # For sad moods, jazz/acoustic genres work better than pop/electronic
                if prefs.get("favorite_genre") in ["pop", "electronic", "hip-hop"]:
                    prefs["favorite_genre"] = "jazz"

            elif phase_lower in ["happy", "uplifting", "joyful", "cheerful"]:
                prefs["favorite_mood"] = "happy"
                prefs["target_energy"] = 0.8

            elif phase_lower in ["chill", "calm", "relaxing", "relaxed", "mellow"]:
                prefs["favorite_mood"] = "chill"
                prefs["target_energy"] = 0.3
                prefs["likes_acoustic"] = True
                # For chill moods, jazz/ambient/acoustic genres work better than pop/electronic
                if prefs.get("favorite_genre") in ["pop", "electronic", "hip-hop", "rock"]:
                    prefs["favorite_genre"] = "jazz"

            elif phase_lower in ["intense", "energetic", "pumped", "dramatic", "powerful"]:
                prefs["favorite_mood"] = "energetic"
                prefs["target_energy"] = 0.9
                prefs["likes_acoustic"] = False
                # For intense moods, rock/hip-hop/electronic work better than jazz/acoustic
                if prefs.get("favorite_genre") in ["jazz", "lofi", "classical"]:
                    prefs["favorite_genre"] = "rock"

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

        For multi-phase playlists, requests extra songs to account for deduplication.

        Args:
            plan: Plan dict with phase preferences and total playlist size (k)

        Returns:
            Recommendations dict with songs per phase
        """
        recommendations = {}

        total_k = plan.get("k", 10)
        num_phases = len(plan["phases"])
        # Distribute k songs evenly across phases, minimum 1 per phase
        k_per_phase = max(1, total_k // num_phases)

        # For multi-phase playlists, request extra songs to account for deduplication
        # Single-phase playlists don't need buffer since there's no deduplication
        if num_phases > 1:
            # Request ~30% more songs to ensure we have enough after deduplication
            k_request = int(k_per_phase * 1.3) + 1
        else:
            k_request = k_per_phase

        for phase, prefs in plan["phase_prefs"].items():
            mode = plan["mode"]
            results = self.matcher.match_and_explain(prefs, self.songs, k=k_request, mode=mode)
            recommendations[phase] = results

        return recommendations

    # -----------------------------------------------------------------------
    # Step 4: EXECUTE
    # -----------------------------------------------------------------------
    def _execute(self, recommendations: Dict, phases: List[str], target_k: int = None) -> Playlist:
        """Build final playlist by combining phase recommendations in order.

        Avoids duplicate songs across phases by skipping songs already added.
        Trims final playlist to target_k if specified.

        Args:
            recommendations: Dict with (song, score, explanation) per phase
            phases: Phase labels in order
            target_k: Target playlist size (trim if exceeded)

        Returns:
            Playlist object
        """
        songs = []
        explanations = []
        phase_labels = []
        seen_song_ids = set()  # Track songs already added to avoid duplicates

        for phase in phases:
            if phase not in recommendations:
                continue

            phase_results = recommendations[phase]
            for song, score, explanation in phase_results:
                song_id = song.get("id")
                # Skip if we've already added this song (avoid duplicates across phases)
                if song_id in seen_song_ids:
                    continue

                songs.append(song)
                explanations.append(f"[{phase.title()}] {explanation}")
                phase_labels.append(phase)
                seen_song_ids.add(song_id)

                # Stop if we've reached the target size
                if target_k and len(songs) >= target_k:
                    break

            # If we've reached target, stop processing more phases
            if target_k and len(songs) >= target_k:
                break

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

        Validation checks (weights sum to 1.0):
        - Non-empty: +0.2
        - Phase coverage: +0.2 (full) or +0.1 (partial)
        - Song diversity (80%+ unique): +0.15
        - Energy progression sensible: +0.15

        Args:
            playlist: Generated playlist
            plan: Original plan with phase info

        Returns:
            Validation score (0.0-1.0), where >= 0.7 is acceptable
        """
        score = 0.0

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

        return score

    def _check_progression(self, playlist: Playlist) -> bool:
        """Check if energy/mood progresses logically through phases.

        Single-phase playlists always pass (no progression needed).
        Multi-phase playlists pass if energy varies by > 0.1 across songs.
        """
        if len(playlist.songs) < 2:
            return True

        # Single-phase: no progression check needed
        if len(set(playlist.phase_labels)) == 1:
            return True

        # Multi-phase: verify songs have varied energy (not all identical)
        energies = [s.get("energy", 0.5) for s in playlist.songs]
        variance = max(energies) - min(energies)
        return variance > 0.1

    # -----------------------------------------------------------------------
    # Step 6: ADJUST
    # -----------------------------------------------------------------------
    def _adjust(self, plan: Dict, playlist: Playlist, attempt: int) -> Dict:
        """Modify plan based on validation feedback for next iteration.

        Adjustment strategy (progressive relaxation):
        - Attempt 0: Lower energy target by 0.1 (broadens song pool)
        - Attempt 1: Toggle popularity preference (includes/excludes mainstream hits)
        - Attempt 2: Toggle acoustic preference (varied instrumentation)

        Args:
            plan: Original plan
            playlist: Current (invalid) playlist
            attempt: Adjustment attempt number (0, 1, 2)

        Returns:
            Modified plan
        """
        adjusted = deepcopy(plan)

        if attempt == 0:
            for phase_prefs in adjusted["phase_prefs"].values():
                # Broaden energy range by lowering target
                phase_prefs["target_energy"] = max(0.3, phase_prefs.get("target_energy", 0.6) - 0.1)

        elif attempt == 1:
            for phase_prefs in adjusted["phase_prefs"].values():
                # Toggle popularity to get different song selection
                phase_prefs["prefer_popular"] = not phase_prefs.get("prefer_popular", True)

        elif attempt == 2:
            for phase_prefs in adjusted["phase_prefs"].values():
                # Toggle acoustic to vary instrumentation
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
