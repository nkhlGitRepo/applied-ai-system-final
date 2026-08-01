"""
Data loader module supporting multiple data sources (CSV, JSON, dict).

Backward compatible: existing code using load_songs() continues to work.
New functionality allows loading from JSON files or Python dictionaries.
"""

import csv
import json
import logging
from typing import List, Dict, Union, Optional

logger = logging.getLogger(__name__)


def _validate_and_normalize_song(song: Dict, song_index: int = None) -> Dict:
    """Validate and normalize a single song dict with proper error context.

    Args:
        song: Song dictionary to validate
        song_index: Index of song (for error messages)

    Returns:
        Normalized song dictionary

    Raises:
        ValueError: If required fields missing or invalid types
    """
    context = f" (song {song_index})" if song_index is not None else ""

    # Required fields
    required_fields = ['id', 'title', 'artist', 'genre', 'mood', 'energy']
    for field in required_fields:
        if field not in song:
            raise ValueError(f"Missing required field '{field}'{context}")

    try:
        validated_song = {
            'id': int(song['id']),
            'title': str(song['title']),
            'artist': str(song['artist']),
            'genre': str(song['genre']),
            'mood': str(song['mood']),
            'energy': float(song['energy']),
            'tempo_bpm': int(song.get('tempo_bpm', 0)),
            'valence': float(song.get('valence', 0.5)),
            'danceability': float(song.get('danceability', 0.5)),
            'acousticness': float(song.get('acousticness', 0.5)),
            'popularity': float(song.get('popularity', 50)),
            'release_decade': int(song.get('release_decade', 2020)),
            'vocal_style': str(song.get('vocal_style', 'sung')),
            'production_quality': str(song.get('production_quality', 'polished')),
            'emotional_arc': str(song.get('emotional_arc', 'constant')),
        }
    except (ValueError, TypeError) as e:
        raise ValueError(f"Type conversion error{context}: {str(e)}")

    return validated_song


def load_from_csv(csv_path: str) -> List[Dict]:
    """Load songs from CSV file with validation."""
    logger.info(f"Loading songs from CSV: {csv_path}")
    songs = []

    try:
        with open(csv_path, 'r') as file:
            reader = csv.DictReader(file)
            for idx, row in enumerate(reader, start=2):  # start=2 (header is row 1)
                try:
                    validated_song = _validate_and_normalize_song(row, song_index=idx)
                    songs.append(validated_song)
                except ValueError as e:
                    logger.error(f"Skipping invalid song at CSV row {idx}: {e}")
                    raise  # Re-raise to match original behavior
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
        raise

    logger.info(f"Loaded {len(songs)} songs from CSV")
    return songs


def load_from_json(json_path: str) -> List[Dict]:
    """Load songs from JSON file.

    Expected JSON format:
    {
        "songs": [
            {
                "id": 1,
                "title": "Song Name",
                "artist": "Artist Name",
                ...
            },
            ...
        ]
    }
    """
    logger.info(f"Loading songs from JSON: {json_path}")

    try:
        with open(json_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.error(f"JSON file not found: {json_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        raise

    # Support both {"songs": [...]} and direct array formats
    songs = data.get('songs', data) if isinstance(data, dict) else data

    if not isinstance(songs, list):
        raise ValueError("JSON must contain a list of songs or {\"songs\": [...]}")

    # Validate and convert types
    validated_songs = []
    for idx, song in enumerate(songs):
        try:
            validated_song = _validate_and_normalize_song(song, song_index=idx)
            validated_songs.append(validated_song)
        except ValueError as e:
            logger.error(f"Skipping invalid song: {e}")
            raise

    logger.info(f"Loaded {len(validated_songs)} songs from JSON")
    return validated_songs


def load_from_dict(songs_dict: Union[List[Dict], Dict]) -> List[Dict]:
    """Load songs from Python dictionary or list.

    Useful for programmatic loading and testing.
    Accepts either a list of song dicts or {"songs": [...]}
    """
    # Handle both formats
    songs = songs_dict.get('songs', songs_dict) if isinstance(songs_dict, dict) else songs_dict

    if not isinstance(songs, list):
        raise ValueError("Must provide a list of songs or {\"songs\": [...]}")

    # Validate and normalize
    validated_songs = []
    for idx, song in enumerate(songs):
        try:
            validated_song = _validate_and_normalize_song(song, song_index=idx)
            validated_songs.append(validated_song)
        except ValueError as e:
            logger.error(f"Skipping invalid song: {e}")
            raise

    return validated_songs


def load_songs(source: str) -> List[Dict]:
    """
    Load songs from a data source (backward compatible wrapper).

    Auto-detects source type by file extension:
    - *.csv → CSV file
    - *.json → JSON file
    - Otherwise treats as CSV path for backward compatibility

    Args:
        source: Path to data file (CSV or JSON)

    Returns:
        List of song dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    if source.endswith('.json'):
        logger.debug(f"Auto-detected JSON format for {source}")
        return load_from_json(source)
    else:
        # Default to CSV for backward compatibility
        logger.debug(f"Auto-detected CSV format for {source}")
        return load_from_csv(source)


def load_and_merge_songs(sources: Union[str, List[str]]) -> List[Dict]:
    """Load and merge songs from multiple data sources.

    Args:
        sources: Single file path or list of file paths (CSV/JSON)

    Returns:
        List of merged song dictionaries with duplicates removed

    Raises:
        FileNotFoundError: If any file doesn't exist
        ValueError: If any file format is invalid
    """
    # Handle single source (backward compatibility)
    if isinstance(sources, str):
        return load_songs(sources)

    if not sources:
        raise ValueError("At least one data source must be provided")

    logger.info(f"Loading and merging {len(sources)} data source(s)...")
    all_songs = []
    seen_ids = set()

    for source in sources:
        try:
            songs = load_songs(source)
            logger.info(f"  Loaded {len(songs)} songs from {source}")

            # Add songs, skipping duplicates by ID
            for song in songs:
                song_id = song.get('id')
                if song_id not in seen_ids:
                    all_songs.append(song)
                    seen_ids.add(song_id)
                else:
                    logger.debug(f"  Skipped duplicate song ID {song_id} from {source}")

        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to load {source}: {e}")
            raise

    logger.info(f"Merged {len(all_songs)} unique songs from {len(sources)} source(s)")
    return all_songs
