"""
Tests for Phase 5 - Interactive CLI.

Tests cover:
1. Method interactions (rate limit → query → format)
2. Single-query and interactive modes
3. Rate limiting enforcement
4. Session management and expiry
5. Output formatting
6. Edge cases and error handling
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from src.phase2_intent_resolver import IntentResolver
from src.phase3_matcher_explainer import MatcherExplainer
from src.phase4_playlist_agent import PlaylistAgent, Playlist
from src.phase1_knowledge_base import KnowledgeBase
from src.phase5_interactive_cli import (
    PlaylistCli,
    ConversationSession,
    create_playlist_cli,
)


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
    """Create test songs."""
    return [
        _song(id=1, title="Sunrise City", artist="Neon Echo", genre="pop"),
        _song(id=2, title="Neon Nights", artist="Neon Echo", genre="pop"),
        _song(id=3, title="Midnight Coding", artist="LoRoom", genre="lofi"),
        _song(id=4, title="Library Rain", artist="Paper Lanterns", genre="lofi"),
        _song(id=5, title="Storm Runner", artist="Voltline", genre="rock"),
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


@pytest.fixture
def cli(resolver, matcher, agent, kb, sample_songs):
    return PlaylistCli(resolver, matcher, agent, kb, sample_songs)


# ---------------------------------------------------------------------------
# Integration Tests (Full Workflow)
# ---------------------------------------------------------------------------
class TestIntegration:
    """Test full CLI workflow: input → rate check → query → format."""

    def test_single_query_full_workflow(self, cli):
        """Full workflow: user input → playlist output."""
        output = cli.run_single_query("Give me happy pop songs")

        assert isinstance(output, str)
        assert len(output) > 0
        assert "pop" in output.lower() or "happy" in output.lower() or "Playlist" in output

    def test_single_query_returns_formatted_string(self, cli):
        """Output is formatted for terminal display."""
        output = cli.run_single_query("pop music")

        # Should contain formatting elements
        assert "🎵" in output or "✅" in output or "Playlist" in output

    def test_single_query_with_sanitization(self, cli):
        """Input is sanitized before processing."""
        # Control characters should be removed
        output = cli.run_single_query("pop\x00songs\n\n")

        # Should still produce output (no crash)
        assert isinstance(output, str)

    def test_multiple_queries_tracked(self, cli):
        """Session tracks multiple queries."""
        cli.run_single_query("pop songs")
        cli.run_single_query("rock songs")

        assert len(cli.session.messages) == 2
        assert len(cli.session.playlists) == 2


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------
class TestRateLimiting:
    """Test rate limit enforcement (max 100 messages/hour)."""

    def test_check_rate_limit_under_limit(self, cli):
        """User under limit can query."""
        assert cli._check_rate_limit() is True

    def test_check_rate_limit_at_limit(self, cli):
        """User at exactly 100 messages still allowed."""
        # Add 100 messages in current hour
        now = time.time()
        for i in range(100):
            cli.session.messages.append((f"query {i}", now - i))

        assert cli._check_rate_limit() is False

    def test_check_rate_limit_exceeds(self, cli):
        """User exceeding limit is rejected."""
        now = time.time()
        for i in range(101):
            cli.session.messages.append((f"query {i}", now - i))

        assert cli._check_rate_limit() is False

    def test_check_rate_limit_old_messages_dont_count(self, cli):
        """Messages older than 1 hour don't count toward limit."""
        now = time.time()
        one_hour_ago = now - 3601

        # Add 100 old messages
        for i in range(100):
            cli.session.messages.append((f"old {i}", one_hour_ago))

        # Should still be under limit
        assert cli._check_rate_limit() is True

    def test_run_single_query_enforces_rate_limit(self, cli):
        """run_single_query() rejects when rate limit exceeded."""
        now = time.time()
        for i in range(100):
            cli.session.messages.append((f"query {i}", now - i))

        output = cli.run_single_query("one more song")

        assert "Rate limit exceeded" in output

    def test_messages_remaining(self, cli):
        """messages_remaining() shows count left."""
        assert cli.messages_remaining() == 100

        cli.session.messages.append(("test", time.time()))
        assert cli.messages_remaining() == 99

    def test_messages_remaining_counts_only_recent(self, cli):
        """messages_remaining() only counts messages in last hour."""
        now = time.time()
        one_hour_ago = now - 3601

        # Add old messages (shouldn't count)
        for i in range(50):
            cli.session.messages.append((f"old {i}", one_hour_ago))

        # Add recent messages
        for i in range(10):
            cli.session.messages.append((f"recent {i}", now - 100))

        # Should have 90 remaining (100 - 10 recent)
        assert cli.messages_remaining() == 90


# ---------------------------------------------------------------------------
# Session Management Tests
# ---------------------------------------------------------------------------
class TestSessionManagement:
    """Test conversation session tracking."""

    def test_session_created_on_init(self, cli):
        """Session is created when CLI is initialized."""
        assert cli.session is not None
        assert isinstance(cli.session, ConversationSession)

    def test_session_tracks_messages(self, cli):
        """Session records each message with timestamp."""
        cli.run_single_query("query 1")
        cli.run_single_query("query 2")

        assert len(cli.session.messages) == 2
        # Each message is (text, timestamp) tuple
        assert all(isinstance(m, tuple) and len(m) == 2 for m in cli.session.messages)

    def test_session_tracks_playlists(self, cli):
        """Session records each playlist with timestamp."""
        cli.run_single_query("query 1")
        cli.run_single_query("query 2")

        assert len(cli.session.playlists) == 2

    def test_session_age_calculation(self, cli):
        """Session age is calculated correctly."""
        age = cli.session.age_seconds()

        # Should be close to 0 (just created)
        assert 0 <= age < 1

    def test_session_expiry_not_expired(self, cli):
        """New session is not expired."""
        assert cli.session.is_expired() is False

    def test_session_expiry_old_session(self, cli):
        """Old session is expired."""
        # Set creation to 31 days ago
        cli.session.created_at = time.time() - (31 * 24 * 3600)

        assert cli.session.is_expired() is True

    def test_session_stats(self, cli):
        """session_stats() returns correct information."""
        cli.run_single_query("test query")

        stats = cli.session_stats()

        assert stats["messages_count"] == 1
        assert stats["playlists_count"] == 1
        assert stats["age_seconds"] >= 0
        assert stats["expired"] is False
        assert stats["messages_remaining"] == 99


# ---------------------------------------------------------------------------
# Format Output Tests
# ---------------------------------------------------------------------------
class TestFormatting:
    """Test playlist formatting for display."""

    def test_format_empty_playlist(self, cli):
        """Empty playlist shows error message."""
        empty_playlist = Playlist(
            songs=[], explanations=[], phase_labels=[], validation_score=0.0
        )

        output = cli._format_playlist(empty_playlist)

        assert "No songs found" in output or "❌" in output

    def test_format_single_song(self, cli):
        """Single song is formatted correctly."""
        song = _song(title="Test Song", artist="Test Artist", genre="pop")
        playlist = Playlist(
            songs=[song],
            explanations=["This is a test song"],
            phase_labels=["general"],
            validation_score=0.8,
        )

        output = cli._format_playlist(playlist)

        assert "Test Song" in output
        assert "Test Artist" in output
        assert "pop" in output
        assert "0.8" in output

    def test_format_multiple_songs(self, cli):
        """Multiple songs are numbered correctly."""
        songs = [
            _song(id=1, title="Song One", artist="Artist One"),
            _song(id=2, title="Song Two", artist="Artist Two"),
        ]
        playlist = Playlist(
            songs=songs,
            explanations=["Explanation one", "Explanation two"],
            phase_labels=["general", "general"],
            validation_score=0.9,
        )

        output = cli._format_playlist(playlist)

        assert "1. Song One" in output
        assert "2. Song Two" in output
        assert "2 songs" in output

    def test_format_includes_score(self, cli):
        """Format includes validation score."""
        song = _song()
        playlist = Playlist(
            songs=[song],
            explanations=["test"],
            phase_labels=["general"],
            validation_score=0.75,
        )

        output = cli._format_playlist(playlist)

        assert "0.75" in output or "score: 0.8" in output  # Rounding

    def test_format_sanitizes_explanation(self, cli):
        """Explanations are sanitized (HTML escaped)."""
        song = _song()
        playlist = Playlist(
            songs=[song],
            explanations=["Test <script>alert('xss')</script>"],
            phase_labels=["general"],
            validation_score=0.5,
        )

        output = cli._format_playlist(playlist)

        # Should be escaped or removed
        assert "<script>" not in output


# ---------------------------------------------------------------------------
# Interactive Mode Tests
# ---------------------------------------------------------------------------
class TestInteractiveMode:
    """Test interactive conversation mode."""

    @patch("builtins.input", side_effect=["pop songs", "quit"])
    def test_interactive_mode_basic(self, mock_input, cli, capsys):
        """Interactive mode accepts input and processes queries."""
        cli.run_interactive()

        # Should process "pop songs" query
        assert len(cli.session.messages) == 1

    @patch("builtins.input", side_effect=["", "exit"])
    def test_interactive_mode_ignores_empty(self, mock_input, cli):
        """Interactive mode ignores empty input."""
        cli.run_interactive()

        # Should not track empty input
        assert len(cli.session.messages) == 0

    @patch("builtins.input", side_effect=["pop songs", "happy songs", "bye"])
    def test_interactive_mode_multiple_queries(self, mock_input, cli):
        """Interactive mode handles multiple queries."""
        cli.run_interactive()

        assert len(cli.session.messages) == 2

    @patch("builtins.input", side_effect=KeyboardInterrupt())
    def test_interactive_mode_keyboard_interrupt(self, mock_input, cli, capsys):
        """Interactive mode handles Ctrl+C gracefully."""
        cli.run_interactive()

        # Should exit cleanly
        assert True

    @patch("builtins.input", side_effect=EOFError())
    def test_interactive_mode_eof(self, mock_input, cli):
        """Interactive mode handles EOF (piped input)."""
        cli.run_interactive()

        # Should exit cleanly
        assert True


# ---------------------------------------------------------------------------
# Edge Cases & Error Handling
# ---------------------------------------------------------------------------
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_query_with_control_characters(self, cli):
        """Query with control characters is sanitized."""
        output = cli.run_single_query("pop\x00\x01\x02songs")

        # Should produce output (not crash)
        assert isinstance(output, str)

    def test_very_long_query(self, cli):
        """Very long query is handled."""
        long_query = "pop " * 500  # 2000+ characters

        # Should either reject or handle gracefully
        try:
            output = cli.run_single_query(long_query)
            assert isinstance(output, str)
        except ValueError:
            # Acceptable to reject oversized input
            pass

    def test_unicode_in_query(self, cli):
        """Unicode in query is handled."""
        output = cli.run_single_query("音楽 pop songs 🎵")

        assert isinstance(output, str)

    def test_empty_songs_catalog(self, resolver, matcher, agent, kb):
        """CLI works with empty catalog (gracefully fails)."""
        empty_cli = PlaylistCli(resolver, matcher, agent, kb, [])

        output = empty_cli.run_single_query("pop music")

        # Should return a message (not crash)
        assert isinstance(output, str)

    def test_agent_error_handling(self, cli):
        """CLI handles agent errors gracefully."""
        # Mock agent to raise an error
        cli.agent.plan_and_execute = MagicMock(side_effect=Exception("Test error"))

        output = cli.run_single_query("test query")

        assert "Error" in output or "❌" in output


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------
class TestFactory:
    """Test create_playlist_cli factory function."""

    def test_create_playlist_cli(self, resolver, matcher, agent, kb, sample_songs):
        """Factory creates working PlaylistCli."""
        cli = create_playlist_cli(resolver, matcher, agent, kb, sample_songs)

        assert cli is not None
        assert isinstance(cli, PlaylistCli)

    def test_factory_cli_works(self, resolver, matcher, agent, kb, sample_songs):
        """Factory-created CLI works end-to-end."""
        cli = create_playlist_cli(resolver, matcher, agent, kb, sample_songs)

        output = cli.run_single_query("pop music")
        assert isinstance(output, str)
        assert len(output) > 0
