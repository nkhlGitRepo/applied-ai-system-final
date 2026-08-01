# Loading Data from Multiple Sources

The system supports loading song data from CSV and JSON files, with automatic detection based on file extension.

## Quick Start

### CSV (default, backward compatible)
```python
from src.recommender import load_songs

songs = load_songs("data/songs.csv")
```

### JSON
```python
from src.data_loader import load_from_json

songs = load_from_json("data/songs.json")
```

### Python Dictionary
```python
from src.data_loader import load_from_dict

songs_data = {
    "songs": [
        {
            "id": 1,
            "title": "Song Title",
            "artist": "Artist Name",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            # ... rest of fields
        },
        # ... more songs
    ]
}

songs = load_from_dict(songs_data)
```

## JSON Format

Songs can be provided in either format:

**Format 1: Array**
```json
[
  {
    "id": 1,
    "title": "Song Title",
    ...
  }
]
```

**Format 2: Object with songs key**
```json
{
  "songs": [
    {
      "id": 1,
      "title": "Song Title",
      ...
    }
  ]
}
```

## Required Fields

All songs must include:
- `id` (integer)
- `title` (string)
- `artist` (string)
- `genre` (string)
- `mood` (string)
- `energy` (float, 0.0-1.0)

## Optional Fields

Fields with defaults:
- `tempo_bpm` (default: 0)
- `valence` (default: 0.5)
- `danceability` (default: 0.5)
- `acousticness` (default: 0.5)
- `popularity` (default: 50)
- `release_decade` (default: 2020)
- `vocal_style` (default: "sung")
- `production_quality` (default: "polished")
- `emotional_arc` (default: "constant")

## Example: Load from JSON

See `data/songs_example.json` for a complete example.

```python
from src.data_loader import load_from_json
from src.recommender import recommend_songs

# Load custom songs
songs = load_from_json("data/my_songs.json")

# Use with the recommender
prefs = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.7,
    "likes_acoustic": False,
    "prefer_popular": True,
    "target_release_decade": 2020,
}

results = recommend_songs(prefs, songs, k=10, mode="genre-first")
```

## Backward Compatibility

All existing code continues to work without changes. The `load_songs()` function from `recommender.py` still loads CSV files exactly as before.

## Future Extensions

The modular design makes it easy to add support for:
- Database connections (PostgreSQL, MongoDB)
- API integrations (Spotify, LastFM)
- Multiple sources merged into one catalog
- Streaming/pagination for large datasets
