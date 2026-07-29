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
from typing import List, Tuple, Optional

from src.phase2_intent_resolver import IntentResolver
from src.phase3_matcher_explainer import MatcherExplainer
from src.phase4_playlist_agent import PlaylistAgent, Playlist
from src.phase1_knowledge_base import KnowledgeBase
from src.guardrails import sanitize_user_input, sanitize_explanation


@dataclass
class ConversationSession:
    """Track conversation state: messages and rate limit."""
    messages: List[Tuple[str, float]] = field(default_factory=list)
    playlists: List[Tuple[Playlist, float]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def age_seconds(self) -> float:
        """How old is this session (in seconds)."""
        return time.time() - self.created_at

    def is_expired(self, max_age_days: int = 30) -> bool:
        """Check if session has expired (default 30 days)."""
        max_age_seconds = max_age_days * 24 * 3600
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
        self.max_messages_per_hour = 100

    def run_single_query(self, query: str) -> str:
        """Process single query and return formatted playlist.

        Args:
            query: User's playlist request

        Returns:
            Formatted playlist string (ready for display)
        """
        # Validate and sanitize input
        sanitized = sanitize_user_input(query)

        # Check rate limit
        if not self._check_rate_limit():
            return "❌ Rate limit exceeded: max 100 messages per hour"

        # Track message
        self.session.messages.append((sanitized, time.time()))

        # Generate playlist (Phases 2-4)
        try:
            playlist = self.agent.plan_and_execute(sanitized)
        except Exception as e:
            return f"❌ Error generating playlist: {str(e)[:100]}"

        # Track playlist
        self.session.playlists.append((playlist, time.time()))

        # Format output
        return self._format_playlist(playlist)

    def run_interactive(self, prompt: str = "Playlist> ") -> None:
        """Multi-turn conversation loop with rate limiting.

        Args:
            prompt: Display prompt (default "Playlist> ")
        """
        print("\n🎵 Playlist Generator (Interactive Mode)")
        print("Commands: 'quit', 'exit', 'bye' to exit")
        print("Type a playlist request and hit Enter\n")

        while True:
            try:
                user_input = input(prompt).strip()

                # Handle empty input
                if not user_input:
                    continue

                # Handle exit commands
                if user_input.lower() in ["quit", "exit", "bye"]:
                    print("Goodbye! 👋")
                    break

                # Process query
                output = self.run_single_query(user_input)
                print(output)

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except EOFError:
                # Handle end of input (e.g., piped input)
                break

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------
    def _check_rate_limit(self) -> bool:
        """Check if user exceeds rate limit (max 100 messages/hour).

        Returns:
            True if under limit, False if exceeded
        """
        now = time.time()
        one_hour_ago = now - 3600

        # Count messages in last hour
        recent_messages = [m for m, t in self.session.messages if t > one_hour_ago]
        return len(recent_messages) < self.max_messages_per_hour

    def _format_playlist(self, playlist: Playlist) -> str:
        """Format playlist for terminal display.

        Args:
            playlist: Generated Playlist object

        Returns:
            Formatted string ready for printing
        """
        # Handle empty playlist
        if not playlist.songs:
            return "❌ No songs found. Try a different request (score: {:.1f})".format(
                playlist.validation_score
            )

        # Build output
        lines = [
            f"\n✅ Playlist Generated ({len(playlist.songs)} songs, score: {playlist.validation_score:.1f})",
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

        lines.append("\n" + "=" * 70 + "\n")

        return "\n".join(lines)

    def messages_remaining(self) -> int:
        """How many messages left before hitting rate limit.

        Returns:
            Integer count of remaining messages in current hour window
        """
        now = time.time()
        one_hour_ago = now - 3600
        recent_messages = [m for m, t in self.session.messages if t > one_hour_ago]
        return self.max_messages_per_hour - len(recent_messages)

    def session_stats(self) -> dict:
        """Get conversation session statistics.

        Returns:
            Dict with messages_count, playlists_count, age_minutes, expired
        """
        return {
            "messages_count": len(self.session.messages),
            "playlists_count": len(self.session.playlists),
            "age_seconds": self.session.age_seconds(),
            "expired": self.session.is_expired(),
            "messages_remaining": self.messages_remaining(),
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
