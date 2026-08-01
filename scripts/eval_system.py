#!/usr/bin/env python3
"""
System Evaluation Script - Runs predefined test cases and prints summary.

Tests the agentic workflow on various query types and prints:
- Pass/fail status for each test
- Confidence ratings based on playlist quality
- Overall system performance metrics
- Detailed results for debugging
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.phase1_knowledge_base import KnowledgeBase
from src.phase2_intent_resolver import IntentResolver
from src.phase3_matcher_explainer import MatcherExplainer
from src.phase4_playlist_agent import PlaylistAgent
from src.data_loader import load_songs


@dataclass
class TestCase:
    """Single test case definition."""
    name: str
    query: str
    expected_size: int
    expected_phases: List[str]
    min_validation_score: float = 0.5
    description: str = ""


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    query: str
    passed: bool
    playlist_size: int
    expected_size: int
    validation_score: float
    phases_extracted: List[str]
    expected_phases: List[str]
    confidence: float  # 0.0-1.0
    reason: str


class SystemEvaluator:
    """Evaluates system performance on test cases."""

    def __init__(self, songs_path: str = "data/songs.csv"):
        """Initialize evaluator with song data."""
        self.songs = load_songs(songs_path)
        self.kb = KnowledgeBase(self.songs)
        self.resolver = IntentResolver()
        self.matcher = MatcherExplainer(self.kb)
        self.agent = PlaylistAgent(self.resolver, self.matcher, self.kb, self.songs)
        print(f"✓ Loaded {len(self.songs)} songs\n")

    def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case."""
        try:
            # Execute query
            playlist = self.agent.plan_and_execute(test_case.query, k=test_case.expected_size)

            # Extract phases from playlist, preserving order and uniqueness
            phases_extracted = self._extract_phases_ordered(playlist.phase_labels)

            # Calculate confidence score
            confidence = self._calculate_confidence(
                playlist_size=len(playlist.songs),
                expected_size=test_case.expected_size,
                validation_score=playlist.validation_score,
                phases_match=self._phases_match(phases_extracted, test_case.expected_phases),
            )

            # Determine pass/fail
            passed = (
                len(playlist.songs) > 0
                and playlist.validation_score >= test_case.min_validation_score
                and self._phases_match(phases_extracted, test_case.expected_phases)
            )

            reason = self._get_reason(playlist, test_case, phases_extracted)

            return TestResult(
                name=test_case.name,
                query=test_case.query,
                passed=passed,
                playlist_size=len(playlist.songs),
                expected_size=test_case.expected_size,
                validation_score=playlist.validation_score,
                phases_extracted=phases_extracted,
                expected_phases=test_case.expected_phases,
                confidence=confidence,
                reason=reason,
            )

        except Exception as e:
            return TestResult(
                name=test_case.name,
                query=test_case.query,
                passed=False,
                playlist_size=0,
                expected_size=test_case.expected_size,
                validation_score=0.0,
                phases_extracted=[],
                expected_phases=test_case.expected_phases,
                confidence=0.0,
                reason=f"Exception: {str(e)[:60]}",
            )

    def _extract_phases_ordered(self, phase_labels: List[str]) -> List[str]:
        """Extract unique phases while preserving order of first appearance.

        Important: Preserves order for journey playlists where "intense → slow"
        differs from "slow → intense".
        """
        seen = set()
        ordered = []
        for phase in phase_labels:
            if phase not in seen:
                ordered.append(phase)
                seen.add(phase)
        return ordered

    def _phases_match(self, extracted: List[str], expected: List[str]) -> bool:
        """Check if extracted phases match expected (ORDER-SENSITIVE).

        For journey playlists, order matters: "intense → slow" ≠ "slow → intense".
        """
        if not expected:
            return True
        # Order-sensitive comparison: list equality instead of set
        return extracted == expected

    def _calculate_confidence(
        self, playlist_size: int, expected_size: int, validation_score: float, phases_match: bool
    ) -> float:
        """Calculate confidence score 0.0-1.0."""
        if playlist_size == 0:
            return 0.0

        score = 0.0

        # Size score (0.4 weight)
        size_ratio = min(playlist_size, expected_size) / max(playlist_size, expected_size)
        score += size_ratio * 0.4

        # Validation score (0.35 weight)
        score += validation_score * 0.35

        # Phase matching (0.25 weight)
        if phases_match:
            score += 0.25

        return min(1.0, score)

    def _get_reason(self, playlist, test_case: TestCase, phases_extracted: List[str]) -> str:
        """Generate human-readable reason for test result."""
        if len(playlist.songs) == 0:
            return "No songs found"

        if not self._phases_match(phases_extracted, test_case.expected_phases):
            return f"Phase mismatch: got {phases_extracted}, expected {test_case.expected_phases}"

        if playlist.validation_score < test_case.min_validation_score:
            return f"Validation score {playlist.validation_score:.2f} < {test_case.min_validation_score}"

        return "Pass"

    def run_all_tests(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Run all test cases."""
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] {test_case.name}...", end=" ", flush=True)
            result = self.run_test(test_case)
            results.append(result)
            print("✓" if result.passed else "✗")

        return results

    def print_summary(self, results: List[TestResult]) -> None:
        """Print summary report."""
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0

        print("\n" + "=" * 80)
        print("TEST SUMMARY".center(80))
        print("=" * 80)

        # Overall stats
        print(f"\nTotal Tests: {len(results)}")
        print(f"Passed: {passed} ({100*passed//len(results)}%)")
        print(f"Failed: {failed} ({100*failed//len(results)}%)")
        print(f"Average Confidence: {avg_confidence:.2f} / 1.0")

        # Detailed results
        print("\n" + "-" * 80)
        print(f"{'Test':<30} {'Status':<8} {'Score':<10} {'Confidence':<12} {'Reason':<20}")
        print("-" * 80)

        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            score = f"{result.validation_score:.2f}"
            confidence = f"{result.confidence:.2f}"
            reason = result.reason[:19]

            print(f"{result.name:<30} {status:<8} {score:<10} {confidence:<12} {reason:<20}")

        # Breakdown by category
        print("\n" + "-" * 80)
        print("DETAILED RESULTS")
        print("-" * 80)

        for result in results:
            status = "✓" if result.passed else "✗"
            print(f"\n{status} {result.name}")
            print(f"   Query: \"{result.query}\"")
            print(f"   Playlist: {result.playlist_size}/{result.expected_size} songs")
            print(f"   Phases: {result.phases_extracted} (expected: {result.expected_phases})")
            print(f"   Validation: {result.validation_score:.2f} (min: 0.50)")
            print(f"   Confidence: {result.confidence:.2f}")
            if not result.passed:
                print(f"   Reason: {result.reason}")

        # Quality tiers
        print("\n" + "-" * 80)
        print("CONFIDENCE DISTRIBUTION")
        print("-" * 80)

        tiers = {
            "Excellent (0.9+)": sum(1 for r in results if r.confidence >= 0.9),
            "Good (0.7-0.9)": sum(1 for r in results if 0.7 <= r.confidence < 0.9),
            "Fair (0.5-0.7)": sum(1 for r in results if 0.5 <= r.confidence < 0.7),
            "Poor (<0.5)": sum(1 for r in results if r.confidence < 0.5),
        }

        for tier, count in tiers.items():
            pct = 100 * count // len(results) if results else 0
            bar = "█" * (count) + "░" * (len(results) - count)
            print(f"{tier:<20} {count:>2} ({pct:>3}%) {bar}")

        print("\n" + "=" * 80)


def get_test_cases() -> List[TestCase]:
    """Define test cases."""
    return [
        # Single-phase tests
        TestCase(
            name="Simple genre request",
            query="Give me happy pop songs",
            expected_size=10,
            expected_phases=["general"],
            description="Basic single-genre request",
        ),
        TestCase(
            name="Chill lofi songs",
            query="I want chill lo-fi music",
            expected_size=8,
            expected_phases=["chill"],
            description="Low-energy request with explicit mood",
        ),
        TestCase(
            name="Energetic rock",
            query="Find me some energetic rock",
            expected_size=12,
            expected_phases=["general"],
            description="High-energy request",
        ),

        # Multi-phase journey tests
        TestCase(
            name="Sad to happy journey",
            query="Create a playlist starting sad and ending happy",
            expected_size=10,
            expected_phases=["sad", "happy"],
            description="Emotional progression",
        ),
        TestCase(
            name="Intense to slow journey",
            query="I want a 12 song playlist that goes from intense to slow",
            expected_size=12,
            expected_phases=["intense", "slow"],
            description="Energy level progression",
        ),
        TestCase(
            name="Arrow notation journey",
            query="Relaxing → Energetic",
            expected_size=8,
            expected_phases=["relaxing", "energetic"],
            description="Arrow notation for journey",
        ),

        # Specific size requests
        TestCase(
            name="5 song playlist",
            query="Create a 5-song workout playlist",
            expected_size=5,
            expected_phases=["intense"],
            description="Exact size specification",
        ),
        TestCase(
            name="20 song playlist",
            query="Give me 20 songs of pop music",
            expected_size=20,
            expected_phases=["general"],
            description="Large playlist request",
        ),

        # Edge cases
        TestCase(
            name="Workout playlist",
            query="Build a workout playlist",
            expected_size=10,
            expected_phases=["intense"],
            description="Recognized playlist type",
        ),
        TestCase(
            name="Study/focus music",
            query="I need a study playlist",
            expected_size=10,
            expected_phases=["focused"],
            description="Study/focus keyword",
        ),
        TestCase(
            name="Sleep/meditative",
            query="Make me a sleep playlist",
            expected_size=8,
            expected_phases=["meditative"],
            description="Sleep/rest keyword",
        ),

        # Complex scenarios
        TestCase(
            name="Swimming playlist with journey",
            query="I want an 18 song swimming playlist that goes from intense to slow",
            expected_size=18,
            expected_phases=["intense", "slow"],
            min_validation_score=0.6,
            description="Complex multi-phase request",
        ),
        TestCase(
            name="Niche discovery",
            query="Give me some hidden gems",
            expected_size=10,
            expected_phases=["general"],
            description="Niche/discovery request",
        ),
    ]


if __name__ == "__main__":
    print("=" * 80)
    print("MUSIC RECOMMENDER SYSTEM - EVALUATION SUITE".center(80))
    print("=" * 80)
    print()

    # Initialize evaluator
    evaluator = SystemEvaluator("data/songs.csv")

    # Run tests
    test_cases = get_test_cases()
    print(f"Running {len(test_cases)} test cases...\n")
    results = evaluator.run_all_tests(test_cases)

    # Print summary
    evaluator.print_summary(results)
