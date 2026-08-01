"""
Phase 5: Interactive CLI - Multi-turn conversation interface with rate limiting.

Provides single-query and interactive modes for playlist requests. Enforces rate
limiting (100 msgs/hr) and tracks conversation history (30-day expiry).

Public API:
    cli = PlaylistCli(resolver, matcher, agent, kb, songs)
    cli.run_single_query("Give me happy pop songs")
    cli.run_interactive()  # Multi-turn loop
"""

import time
from dataclasses import dataclass, field
from typing import List, Tuple

from src.phase2_intent_resolver import IntentResolver
from src.phase3_matcher_explainer import MatcherExplainer
from src.phase4_playlist_agent import PlaylistAgent, Playlist
from src.phase1_knowledge_base import KnowledgeBase
from src.guardrails import sanitize_user_input, sanitize_explanation
from src.data_loader import load_songs, load_and_merge_songs

# Constants
MAX_MESSAGES_PER_HOUR = 100
MAX_SESSION_AGE_DAYS = 30


@dataclass
class ConversationSession:
    """Track conversation state: messages and session age."""
    messages: List[Tuple[str, float]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def age_seconds(self) -> float:
        """How old is this session (in seconds)."""
        return time.time() - self.created_at

    def is_expired(self) -> bool:
        """Check if session has expired (max 30 days)."""
        max_age_seconds = MAX_SESSION_AGE_DAYS * 24 * 3600
        return self.age_seconds() > max_age_seconds


class PlaylistCli:
    """Interactive CLI orchestrating Phases 1-4 with rate limiting."""

    def __init__(
        self,
        resolver: IntentResolver,
        matcher: MatcherExplainer,
        agent: PlaylistAgent,
        kb: KnowledgeBase,
        songs: List[dict],
    ):
        """Initialize CLI with dependencies from Phases 1-4.

        Args:
            resolver: Phase 2 IntentResolver
            matcher: Phase 3 MatcherExplainer
            agent: Phase 4 PlaylistAgent
            kb: Phase 1 KnowledgeBase
            songs: Full song catalog
        """
        self.resolver = resolver
        self.matcher = matcher
        self.agent = agent
        self.kb = kb
        self.songs = songs
        self.session = ConversationSession()

    def run_single_query(self, query: str, k: int = 10) -> str:
        """Process single query and return formatted playlist.

        Args:
            query: User's playlist request
            k: Playlist size (default 10). Query can specify size (e.g., "5-song playlist")
              which overrides this parameter only if explicitly present in query.

        Returns:
            Formatted playlist string (ready for display)
        """
        # Validate and sanitize input
        sanitized = sanitize_user_input(query)
        now = time.time()

        # Check rate limit
        if not self._check_rate_limit(now):
            remaining = self.messages_remaining(now)
            return f"❌ Rate limit exceeded: max {MAX_MESSAGES_PER_HOUR} messages per hour ({remaining} remaining)"

        # Track message
        self.session.messages.append((sanitized, now))

        # Extract playlist size from query if explicitly specified, else use provided k
        try:
            query_size = self._extract_playlist_size(sanitized)
            if query_size is not None:
                k = query_size
        except ValueError as e:
            return f"❌ {str(e)}"

        # Generate playlist (Phases 2-4)
        try:
            playlist = self.agent.plan_and_execute(sanitized, k=k)
        except ValueError as e:
            return f"❌ {str(e)}"
        except Exception as e:
            return f"❌ Error generating playlist: {str(e)[:100]}"

        # Format output (pass requested k for comparison)
        return self._format_playlist(playlist, requested_k=k)

    def run_interactive(self, prompt: str = "🎧 You: ") -> None:
        """Multi-turn conversation loop with rate limiting and help.

        Args:
            prompt: Display prompt (default "🎧 You: ")
        """
        print("\n" + "=" * 80)
        print("🎵 INTERACTIVE PLAYLIST GENERATOR".center(80))
        print("=" * 80)
        print("\n📝 Commands:")
        print("  • Type your playlist request and press Enter")
        print("  • 'load_data <file>' → Load a different data source (CSV or JSON)")
        print("  • 'help' or '?' → Show available commands")
        print("  • 'stats' → Show session statistics")
        print("  • 'exit', 'quit', 'bye', 'goodbye' → Exit the chat\n")
        print("=" * 80 + "\n")

        while True:
            try:
                user_input = input(prompt).strip()

                # Handle empty input
                if not user_input:
                    continue

                # Handle load_data_merge command (merge multiple sources)
                if user_input.lower().startswith("load_data_merge "):
                    file_list = user_input[16:].strip()
                    files = [f.strip() for f in file_list.split()]
                    if files:
                        self._load_merged_data_sources(files)
                    continue

                # Handle load_data command (single source)
                if user_input.lower().split()[0] == "load_data" if user_input.lower().split() else False:
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        data_file = parts[1].strip()
                        self._load_data_source(data_file)
                    continue

                # Handle help command
                if user_input.lower() in ["help", "?"]:
                    self._show_help()
                    continue

                # Handle stats command
                if user_input.lower() == "stats":
                    self._show_session_stats()
                    continue

                # Handle exit commands
                if user_input.lower() in ["quit", "exit", "bye", "goodbye"]:
                    print("\nGoodbye! 👋 Thanks for using the Playlist Generator!\n")
                    break

                # Process query
                output = self.run_single_query(user_input)
                print(output)

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋 Thanks for using the Playlist Generator!\n")
                break
            except EOFError:
                # Handle end of input (e.g., piped input)
                break

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------
    def _extract_playlist_size(self, query: str) -> int:
        """Extract playlist size from user query, if specified.

        Recognizes patterns like:
        - "5-song workout playlist"
        - "create a 10 song playlist"
        - "size 20" or "of size 15"

        Args:
            query: User's query string

        Returns:
            Extracted playlist size (capped to available songs), or None if not specified

        Raises:
            ValueError: If specified size is out of valid range (1-100)
        """
        from src.phase4_playlist_agent import PlaylistAgent
        import re
        query_lower = query.lower()

        # Pattern 1: "N song(s)" - with optional words in between
        # Matches: "5 songs", "5-song", "12 happy pop songs", "10-song playlist", "8 songs of rock", etc.
        # Two approaches: (A) "N-song" or "N song" (B) "N [words] songs"

        # Approach A: "N-song(s)" or "N song(s)" as a compound modifier
        match = re.search(r'\b(\d+)(?:\s|-)?songs?\b', query_lower)
        if match:
            size = int(match.group(1))
            PlaylistAgent._validate_playlist_size(size)
            return min(size, len(self.songs))

        # Approach B: "N [words] songs" where words can be descriptive
        # Matches: "12 happy pop songs", "15 chill lofi songs", etc.
        match = re.search(r'\b(\d+)(?:\s+\w+)*\s+songs\b', query_lower)
        if match:
            size = int(match.group(1))
            PlaylistAgent._validate_playlist_size(size)
            return min(size, len(self.songs))

        # Pattern 2: "size N" or "of size N"
        match = re.search(r'(?:size|of\s+size)\s+(\d+)', query_lower)
        if match:
            size = int(match.group(1))
            PlaylistAgent._validate_playlist_size(size)
            return min(size, len(self.songs))

        # No size specified in query
        return None

    def _get_recent_message_count(self, now: float) -> int:
        """Count messages in last hour (helper to avoid duplication).

        Args:
            now: Current timestamp

        Returns:
            Number of messages in last 60 minutes
        """
        one_hour_ago = now - 3600
        recent_messages = [m for m, t in self.session.messages if t > one_hour_ago]
        return len(recent_messages)

    def _check_rate_limit(self, now: float) -> bool:
        """Check if user exceeds rate limit (max 100 messages/hour).

        Args:
            now: Current timestamp

        Returns:
            True if under limit, False if exceeded
        """
        recent_count = self._get_recent_message_count(now)
        return recent_count < MAX_MESSAGES_PER_HOUR

    def _format_playlist(self, playlist: Playlist, requested_k: int = None) -> str:
        """Format playlist for terminal display.

        Args:
            playlist: Generated Playlist object
            requested_k: Requested playlist size (for comparison message)

        Returns:
            Formatted string ready for printing
        """
        # Handle empty playlist
        if not playlist.songs:
            return "❌ No songs found. Try a different request (score: {:.1f})".format(
                playlist.validation_score
            )

        # Verify data integrity (songs and explanations should match)
        if len(playlist.songs) != len(playlist.explanations):
            return f"❌ Internal error: playlist data mismatch ({len(playlist.songs)} songs, {len(playlist.explanations)} explanations)"

        # Build output
        actual_count = len(playlist.songs)
        lines = [
            f"\n✅ Playlist Generated ({actual_count} songs, score: {playlist.validation_score:.1f})",
            "=" * 70,
        ]

        # Add each song with explanation
        for i, (song, explanation) in enumerate(zip(playlist.songs, playlist.explanations), 1):
            title = song.get("title", "Unknown")
            artist = song.get("artist", "Unknown")
            genre = song.get("genre", "?")
            mood = song.get("mood", "?")

            # Sanitize explanation for safe display
            safe_explanation = sanitize_explanation(explanation)

            lines.append(f"\n{i}. {title} - {artist}")
            lines.append(f"   Genre: {genre} | Mood: {mood}")
            lines.append(f"   {safe_explanation}")

        lines.append("\n" + "=" * 70)

        # Add note if playlist is smaller than requested
        if requested_k and actual_count < requested_k:
            lines.append(f"\n📝 Note: Returned {actual_count} of {requested_k} requested songs.")
            lines.append("   The catalog doesn't have enough songs matching your criteria")
            lines.append("   (mood, genre, energy level, and no duplicates across phases).")
            lines.append("   Try a different mood, genre, or smaller size for more options.")

        lines.append("\n")

        return "\n".join(lines)

    def _show_help(self) -> None:
        """Display help text with available commands and query examples."""
        print("\n" + "=" * 70)
        print("HELP & EXAMPLES".center(70))
        print("=" * 70)
        print("\n📍 Simple Requests:")
        print("   'Give me happy pop songs'")
        print("   'I want chill lo-fi music'")
        print("   'Find me some energetic rock'")
        print("\n🎯 Specific Playlists (auto-detects phases):")
        print("   'Create a workout playlist'")
        print("   'I need a study playlist'")
        print("   'Build a dinner playlist'")
        print("   'Make a party playlist'")
        print("\n🎵 Journey Playlists (emotional progressions):")
        print("   'sad → happy'")
        print("   'Create a playlist starting calm and ending energetic'")
        print("   'Build a morning playlist: calm → energetic'")
        print("\n💎 Niche/Unpopular Songs:")
        print("   'Give me some hidden gems'")
        print("   'I want obscure indie songs'")
        print("   'Find me underground rock'")
        print("   'Create a niche lo-fi mix'")
        print("\n🎚️  Custom Sizes:")
        print("   'Create a 5-song workout playlist'")
        print("   'Give me 8 songs of pop music'")
        print("   'lofi playlist of size 12'")
        print("\n⌨️  Commands:")
        print("   'load_data <file>' → Load a single data source (CSV or JSON)")
        print("   'load_data_merge <file1> <file2> ...' → Merge multiple data sources")
        print("   'help' or '?' → Show this help text")
        print("   'stats' → Show session statistics")
        print("   'exit', 'quit', 'bye', 'goodbye' → Exit the chat")
        print("\n📂 Data Source Examples:")
        print("   'load_data data/songs.csv'")
        print("   'load_data data/songs_example.json'")
        print("   'load_data_merge data/songs.csv data/songs_example.json'")
        print("=" * 70 + "\n")

    def _show_session_stats(self) -> None:
        """Display current session statistics."""
        stats = self.session_stats()
        print("\n" + "=" * 70)
        print("SESSION STATISTICS".center(70))
        print("=" * 70)
        print(f"\n📊 Queries this session: {stats['messages_count']}")
        print(f"⏱️  Session age: {stats['age_seconds']:.1f} seconds ({stats['age_seconds']/60:.1f} minutes)")
        print(f"📨 Messages remaining (this hour): {stats['messages_remaining']}/{MAX_MESSAGES_PER_HOUR}")

        if stats['expired']:
            print("⚠️  Session has expired (max 30 days)")
        else:
            days_left = (MAX_SESSION_AGE_DAYS * 24 * 3600 - stats['age_seconds']) / (24 * 3600)
            print(f"✅ Session active for {days_left:.1f} more days")

        print("=" * 70 + "\n")

    def _load_data_source(self, data_file: str) -> None:
        """Load a new data source and reinitialize the system.

        Args:
            data_file: Path to CSV or JSON data file

        Note:
            - Conversation history is cleared when switching datasets
            - All 5 phases are reinitialized from scratch
            - Rate limiting is preserved but message count resets
        """
        try:
            print(f"\n📂 Loading data from {data_file}...")
            new_songs = load_songs(data_file)
            print(f"✓ Loaded {len(new_songs)} songs")

            # Recreate all phases from scratch (safer than partial updates)
            new_kb = KnowledgeBase(new_songs)
            new_resolver = IntentResolver()
            new_matcher = MatcherExplainer(new_kb)
            new_agent = PlaylistAgent(new_resolver, new_matcher, new_kb, new_songs)

            # Commit changes (all-or-nothing to prevent inconsistent state)
            self.songs = new_songs
            self.kb = new_kb
            self.resolver = new_resolver
            self.matcher = new_matcher
            self.agent = new_agent

            # Clear conversation history since dataset changed
            self.session = ConversationSession()

            print(f"✓ Reinitialized system with new data source")
            print(f"ℹ️  Conversation history cleared (new dataset)\n")

        except FileNotFoundError:
            print(f"✗ Error: File not found: {data_file}\n")
        except (ValueError, IOError) as e:
            print(f"✗ Error loading data: {e}\n")

    def _load_merged_data_sources(self, data_files: list) -> None:
        """Load and merge multiple data sources into one catalog.

        Args:
            data_files: List of file paths (CSV or JSON)

        Note:
            - Duplicate songs (by ID) are automatically removed
            - Conversation history is cleared when dataset changes
            - All files must be valid; if any fails, nothing is loaded
        """
        try:
            print(f"\n📂 Merging {len(data_files)} data source(s)...")
            merged_songs = load_and_merge_songs(data_files)
            print(f"✓ Merged {len(merged_songs)} unique songs")

            # Recreate all phases from scratch with merged data
            new_kb = KnowledgeBase(merged_songs)
            new_resolver = IntentResolver()
            new_matcher = MatcherExplainer(new_kb)
            new_agent = PlaylistAgent(new_resolver, new_matcher, new_kb, merged_songs)

            # Commit changes
            self.songs = merged_songs
            self.kb = new_kb
            self.resolver = new_resolver
            self.matcher = new_matcher
            self.agent = new_agent

            # Clear conversation history
            self.session = ConversationSession()

            print(f"✓ Reinitialized system with merged data")
            print(f"ℹ️  Conversation history cleared (new dataset)\n")

        except FileNotFoundError as e:
            print(f"✗ Error: File not found: {e}\n")
        except (ValueError, IOError) as e:
            print(f"✗ Error merging data: {e}\n")

    def messages_remaining(self, now: float = None) -> int:
        """How many messages left before hitting rate limit.

        Args:
            now: Current timestamp (optional, defaults to current time)

        Returns:
            Integer count of remaining messages in current hour window
        """
        if now is None:
            now = time.time()
        recent_count = self._get_recent_message_count(now)
        return MAX_MESSAGES_PER_HOUR - recent_count

    def session_stats(self) -> dict:
        """Get conversation session statistics.

        Returns:
            Dict with messages_count, age_seconds, expired, messages_remaining
        """
        now = time.time()
        return {
            "messages_count": len(self.session.messages),
            "age_seconds": self.session.age_seconds(),
            "expired": self.session.is_expired(),
            "messages_remaining": self.messages_remaining(now),
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_playlist_cli(
    resolver: IntentResolver,
    matcher: MatcherExplainer,
    agent: PlaylistAgent,
    kb: KnowledgeBase,
    songs: List[dict],
) -> PlaylistCli:
    """Create a PlaylistCli instance.

    Args:
        resolver: Phase 2 IntentResolver
        matcher: Phase 3 MatcherExplainer
        agent: Phase 4 PlaylistAgent
        kb: Phase 1 KnowledgeBase
        songs: Full song catalog

    Returns:
        New PlaylistCli
    """
    return PlaylistCli(resolver, matcher, agent, kb, songs)
