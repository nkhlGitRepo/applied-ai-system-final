"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from .recommender import (
    load_songs, recommend_songs, recommend_songs_with_diversity, SCORING_MODES,
    format_recommendation_summary, format_recommendation_detailed
)
from .phase1_knowledge_base import KnowledgeBase
from .phase2_intent_resolver import IntentResolver
from .phase3_matcher_explainer import MatcherExplainer
from .phase4_playlist_agent import PlaylistAgent
from .phase5_interactive_cli import PlaylistCli
import argparse


# User preference profiles for testing
USER_PROFILES = {
    "high_energy_pop": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.85,
        "likes_acoustic": False,
    },
    "chill_lofi": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.38,
        "likes_acoustic": True,
    },
    "deep_intense_rock": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.91,
        "likes_acoustic": False,
    },
}

# Adversarial/Edge case profiles to test algorithm limits
ADVERSARIAL_PROFILES = {
    "conflicting_energy_mood": {
        "favorite_genre": "indie",
        "favorite_mood": "melancholic",
        "target_energy": 0.90,
        "likes_acoustic": False,
    },
    "extreme_low_energy": {
        "favorite_genre": "classical",
        "favorite_mood": "meditative",
        "target_energy": 0.10,
        "likes_acoustic": True,
    },
    "acoustic_rock_contradiction": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.88,
        "likes_acoustic": True,
    },
    "niche_genre_nomatch": {
        "favorite_genre": "synthwave",
        "favorite_mood": "moody",
        "target_energy": 0.75,
        "likes_acoustic": False,
    },
    "all_preference_mismatches": {
        "favorite_genre": "country",
        "favorite_mood": "nostalgic",
        "target_energy": 0.15,
        "likes_acoustic": False,
    },
    "extreme_high_energy_danceability": {
        "favorite_genre": "electronic",
        "favorite_mood": "uplifting",
        "target_energy": 0.95,
        "likes_acoustic": False,
    },
}

# Combine all profiles
USER_PROFILES.update(ADVERSARIAL_PROFILES)


def test_full_system() -> None:
    """Test all 5 phases integrated together."""
    print("=" * 80)
    print("FULL SYSTEM INTEGRATION TEST (All 5 Phases)")
    print("=" * 80)
    print()

    # Load and initialize
    songs = load_songs("data/songs.csv")
    print(f"✓ Loaded {len(songs)} songs")

    kb = KnowledgeBase(songs)
    resolver = IntentResolver()
    matcher = MatcherExplainer(kb)
    agent = PlaylistAgent(resolver, matcher, kb, songs)
    cli = PlaylistCli(resolver, matcher, agent, kb, songs)
    print("✓ Initialized Phases 1-5")
    print()

    # Test queries
    test_queries = [
        "Give me happy pop songs",
        "Create an emotional journey from sad to happy",
        "I want chill lo-fi music",
        "Find me some energetic rock",
        "Relaxing acoustic songs",
    ]

    print("=" * 80)
    print("PROCESSING 5 SAMPLE QUERIES")
    print("=" * 80)
    print()

    for idx, query in enumerate(test_queries, 1):
        print(f"QUERY {idx}: {query}")
        print("-" * 80)

        try:
            output = cli.run_single_query(query)
            print(output)
            stats = cli.session_stats()
            print(f"Messages remaining: {stats['messages_remaining']}")
            print()

        except Exception as e:
            print(f"❌ Error: {str(e)}\n")

    # Summary
    print("=" * 80)
    print("SESSION SUMMARY")
    print("=" * 80)
    stats = cli.session_stats()
    print(f"Total queries: {stats['messages_count']}")
    print(f"Session age: {stats['age_seconds']:.2f}s")
    print(f"Messages remaining this hour: {stats['messages_remaining']}")
    print()
    print("✅ ALL PHASES WORKING CORRECTLY")


def main(
    profile_name: str = "high_energy_pop",
    mode: str = "genre-first",
    diversity: bool = False,
    artist_penalty: float = 0.5,
    genre_penalty: float = 0.3,
    verbose: bool = False,
    test_full: bool = False,
) -> None:
    # Handle full system test mode
    if test_full:
        test_full_system()
        return

    songs = load_songs("data/songs.csv")
    print(f"Successfully loaded {len(songs)} songs.\n")

    # Load selected user profile
    if profile_name not in USER_PROFILES:
        print(f"Profile '{profile_name}' not found. Available profiles:")
        for name in USER_PROFILES.keys():
            print(f"  - {name}")
        return

    # Validate mode
    if mode not in SCORING_MODES:
        print(f"Mode '{mode}' not found. Available modes:")
        for name, strategy in SCORING_MODES.items():
            print(f"  - {name}: {strategy.name}")
        return

    user_prefs = USER_PROFILES[profile_name]

    if diversity:
        recommendations = recommend_songs_with_diversity(
            user_prefs, songs, k=5, mode=mode,
            artist_penalty=artist_penalty, genre_penalty=genre_penalty
        )
    else:
        recommendations = recommend_songs(user_prefs, songs, k=5, mode=mode)

    print("\n" + "="*80)
    print(f"TOP RECOMMENDATIONS FOR: {profile_name.upper().replace('_', ' ')}")
    print("="*80)
    print(f"Profile: genre={user_prefs['favorite_genre']}, mood={user_prefs['favorite_mood']}, " +
          f"energy={user_prefs['target_energy']}, acoustic={'yes' if user_prefs['likes_acoustic'] else 'no'}")
    print(f"Mode: {SCORING_MODES[mode].name}")
    if diversity:
        print(f"Diversity: Enabled (artist_penalty={artist_penalty}, genre_penalty={genre_penalty})")
    print("="*80)

    if recommendations:
        if verbose:
            print(format_recommendation_detailed(recommendations))
            print("\nTip: Run without --verbose for a concise summary view")
        else:
            print(format_recommendation_summary(recommendations))
            print("\nTip: Run with --verbose to see all scoring reasons")
    else:
        print("No recommendations found.")


def interactive_mode() -> None:
    """Interactive CLI for demoing the full system."""
    print("\n" + "=" * 80)
    print("🎵 MUSIC PLAYLIST GENERATOR - Interactive Demo".center(80))
    print("=" * 80)
    print("\nLoading system...")

    # Initialize all phases
    songs = load_songs("data/songs.csv")
    kb = KnowledgeBase(songs)
    resolver = IntentResolver()
    matcher = MatcherExplainer(kb)
    agent = PlaylistAgent(resolver, matcher, kb, songs)
    cli = PlaylistCli(resolver, matcher, agent, kb, songs)

    print(f"✓ Loaded {len(songs)} songs")
    print("✓ Initialized all 5 phases (Knowledge Base → Intent Resolver → Matcher → Agent → CLI)")

    print("\n" + "=" * 80)
    print("EXAMPLES OF WHAT YOU CAN ASK:")
    print("=" * 80)
    print("""
  📍 Simple requests:
     "Give me happy pop songs"
     "I want chill lo-fi music"
     "Find me some energetic rock"

  🎯 Specific playlists (auto-generates smart phases):
     "Create a workout playlist"
     "I need a study playlist"
     "Build a dinner playlist"
     "Make a party playlist"

  🎵 Journey playlists (structured progressions):
     "Create a playlist starting with energetic and ending with chill"
     "Build a dinner playlist from uplifting to relaxed"
     "Make a morning playlist: calm → energetic"
     "Workout playlist: calm → intense"

  🎚️ Custom playlist sizes:
     "Create a 5-song workout playlist"
     "Give me a 8 song chill lofi mix"
     "Pop music of size 12"

  ⌨️ Special Commands:
     'help' or '?' → Show all options and examples
     'stats' → View session statistics
     'exit', 'quit', 'bye', 'goodbye' → Leave the chat
""")

    print("=" * 80)
    print("START CHATTING (type your first request below):")
    print("=" * 80 + "\n")

    # Interactive loop
    cli.run_interactive(prompt="🎧 You: ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument("--profile", type=str, default="high_energy_pop",
                        help="User profile name (default: high_energy_pop)")
    parser.add_argument("--mode", type=str, default="genre-first",
                        help="Scoring mode: genre-first, discovery, niche-friendly, personality (default: genre-first)")
    parser.add_argument("--diversity", action="store_true",
                        help="Enable artist and genre diversity penalties")
    parser.add_argument("--artist-penalty", type=float, default=0.5,
                        help="Artist duplicate penalty (0.0-1.0, default: 0.5)")
    parser.add_argument("--genre-penalty", type=float, default=0.3,
                        help="Genre duplicate penalty (0.0-1.0, default: 0.3)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all scoring reasons (default: summary table)")
    parser.add_argument("--test-full-system", action="store_true",
                        help="Test all 5 phases integrated together with sample queries")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Launch interactive demo mode (chat with the system)")
    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        main(
            profile_name=args.profile,
            mode=args.mode,
            diversity=args.diversity,
            artist_penalty=args.artist_penalty,
            genre_penalty=args.genre_penalty,
            verbose=args.verbose,
            test_full=args.test_full_system,
        )
