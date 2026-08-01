# 🎵 Music Recommender Simulation

Initial Project (Music Recommender): The original music recommender is a song recommendation engine that loads a catalog and scores songs using the GMEWS algorithm. This is a weighted formula combining genre, mood, energy, acousticness, and danceability. It supports multiple scoring modes, including genre-first, discovery, niche-friendly, and personality to generate recommendations for different user preferences.

The interactive recommendation agent extends this by adding natural language understanding, RAG context, agentic reasoning, and an interactive interface that lets users have conversations with the recommender.

## Project Summary

A complete 5-phase music recommendation system that combines knowledge representation, natural language understanding, and intelligent ranking with RAG-enhanced explanations.

Key Features:
- Natural Language Processing: Understands user requests like "Create a workout playlist," "emotional journey from sad to happy," or "give me a niche lo-fi mix" with automatic mood/energy/genre detection
- Multi-phase Playlists: Automatically detects journey requests and decomposes them into logical phases with distinct musical progressions
- Explainable AI: Every recommendation includes plain-English explanations citing genre matches, mood alignment, energy fit, and audio characteristics
- Interactive Demo: Try the system through a terminal chat interface with rate limiting (100 msgs/hour) and session tracking (30-day expiry)
- Comprehensive Testing: 310 tests verifying method interactions, edge cases, and system integration across all 5 phases

---

## How The System Works

### How It Works

The system diagram (diagrams/system_architecture.mmd) shows how user queries flow through five integrated phases:

Phase 1: Knowledge Base retrieves song context and similar tracks using RAG, enriching recommendations with genre and artist insights.

Phase 2: Intent Resolver parses natural language to extract mood, genre, energy, and niche preferences, then selects the best scoring mode (genre-first, discovery, niche-friendly, or personality-based).

Phase 3: Matcher & Explainer scores candidates using the GMEWS algorithm and pairs each song with a plain-English explanation of why it matches.

Phase 4: Playlist Agent orchestrates a feedback loop: understand the request (detect multi-phase journeys), plan phase-specific preferences, retrieve candidates, execute deduplication, validate quality (score ≥0.7), and adjust constraints if needed.

Phase 5: Interactive CLI delivers the final playlist through a conversational interface with rate limiting (100 msgs/hour) and session tracking (30-day expiry).

The diagram also shows where 310 tests validate each phase and where human feedback helps the system improve through iterative constraint adjustment.

### Scoring Algorithm

The core GMEWS formula ranks songs across five dimensions:

```
SCORE = (G × weight) + (M × weight) + (E × weight) + (A × weight) + (D × weight)
        + vocal_style + production_quality + emotional_arc + popularity + decade

  G: 1.0 if genre matches, else 0.0
  M: 1.0 if mood matches, else 0.0  
  E: 1.0 - |song.energy - target_energy| (distance-based, 0-1 range)
  A: acousticness if user likes acoustic, else 1.0 - acousticness
  D: danceability if target_energy ≥ 0.7, else 0.0
```

When the algorithm runs, genre and mood are the primary matches. For the energy, distance based scoring is used to provide good song variety within a preferred range. Acoustic preference, production quality, and emotional arc adjust the score based on preferences. The danceability bonuses only applies when the system is looking at high energy songs. Other factors such as vocal style, popularity, and release decade are weighted differently depending on the scoring mode.  The different possible modes are genre first, discovery, niche friendly, and personality based.


---

## Getting Started

### Setup

1. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac/Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify data file exists:
   - The system expects `data/songs.csv` with songs to recommend

### Step by Step instructions for Running Code

Follow these steps to run the system for the first time:

1. Clone or download the project:
   ```bash
   cd applied-ai-system-final
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Mac/Linux
   # OR
   .venv\Scripts\activate           # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run tests to verify setup:
   ```bash
   pytest -q                    # Quick test run (should see "310 passed")
   ```

5. Launch interactive mode:
   ```bash
   python -m src.main --interactive
   ```

6. Try a sample query:
   ```
   🎧 You: Give me a study playlist with low intensity
   
   ✅ Playlist Generated (10 songs, score: 0.7)
   ...
   ```

7. Explore more features:
   - Type `help` or `?` to see available commands
   - Type `stats` to see session information
   - Type `exit` or `quit` to leave

### Running the System

The system has multiple modes depending on your use case:

#### Interactive Demo Mode (Recommended)
Chat naturally with the system in a terminal interface:
```bash
python -m src.main --interactive
# or
python -m src.main -i
```

Supported playlist queries:
- Simple requests: `"Give me happy pop songs"`
- Playlist types: `"Create a workout playlist"`, `"I need a study playlist"`
- Journey playlists: `"sad → happy"`, `"calm to energetic"`, `"Create a dinner playlist from uplifting to chill"`
- Niche/unpopular songs: `"Give me some hidden gems"`, `"I want obscure indie songs"`, `"Find me underground rock"`
- Custom sizes: `"Create a 5-song workout playlist"`, `"Give me 8 songs"`, `"playlist of size 15"`

Interactive commands:
- `help` or `?` → Show help with query examples
- `stats` → Display session statistics (queries made, rate limit status)
- `exit`, `quit`, `bye`, or `goodbye` → Exit the chat gracefully
- Ctrl+C → Exit the chat (keyboard interrupt)

Playlist size notes:
- Default size is 10 songs if not specified
- You can specify size using patterns like: `"5-song"`, `"10 songs"`, `"size 12"`, or `"of size 8"`
- Maximum size is 100 songs or the full catalog, whichever is smaller
- If you request more songs than available, the system returns what's available

Rate limiting and sessions:
- Maximum 100 messages per hour per session
- Session tracks conversation history for 30 days
- Use the `stats` command to see remaining messages and session age


#### Single Query Mode
Process one request and see results:
```bash
python -m src.main --profile high_energy_pop --mode genre-first
```

Available profiles: `high_energy_pop`, `chill_lofi`, `deep_intense_rock`, and 5 adversarial profiles

Available scoring modes: `genre-first`, `discovery`, `niche-friendly`, `personality`

#### Testing All Phases
Run an integration test with sample queries:
```bash
python -m src.main --test-full-system
```

#### Full Help
```bash
python -m src.main --help
```

### Running Tests

Run all 310 tests verifying the system:
```bash
pytest
```

View test coverage:
```bash
pytest --cov=src --cov-report=html
```

Test breakdown:
- Phase 1 (Knowledge Base): 38 tests
- Phase 2 (Intent Resolver): 55 tests (updated: added genre/mood/energy extraction tests)
- Phase 3 (Matcher & Explainer): 22 tests
- Phase 4 (Playlist Agent): 41 tests (updated: added energy filtering tests)
- Phase 5 (Interactive CLI): 35 tests
- Integration & Guardrails: 119 tests
- Total: 310 tests

---

## Sample Interactions (Examples of Inputs and Corresponding Outputs)

### Interactive Mode Examples

#### Example 1: High-intensity running playlist

```
🎧 You: give me a high intensity running playlist

✅ Playlist Generated (10 songs, score: 0.7)
======================================================================

1. Gym Hero - Max Pulse
   Genre: pop | Mood: intense
   [Intense] Score 7.56: Pop song with intense mood (0.9 energy).

2. Sunrise City - Neon Echo
   Genre: pop | Mood: happy
   [Intense] Score 7.30: Pop song with happy mood (0.8 energy).

3. Urban Beats - MC Cipher
   Genre: hip-hop | Mood: energetic
   [Intense] Score 7.15: Hip-Hop song with energetic mood (0.9 energy).

4. Hip Hop Flow - Hip Hop Artist
   Genre: hip-hop | Mood: energetic
   [Intense] Score 7.07: Hip-Hop song with energetic mood (0.8 energy).

5. Dancefloor Magic - House Masters
   Genre: house | Mood: energetic
   [Intense] Score 7.05: House song with energetic mood (0.9 energy).

6. Bass & Soul - Funk Legend
   Genre: funk | Mood: energetic
   [Intense] Score 7.03: Funk song with energetic mood (0.9 energy).

7. Afrobeat Groove - Afrobeat Master
   Genre: afrobeat | Mood: energetic
   [Intense] Score 7.00: Afrobeat song with energetic mood (0.8 energy).

8. Techno Beat - Techno DJ
   Genre: techno | Mood: energetic
   [Intense] Score 6.91: Techno song with energetic mood (0.9 energy).

9. Soul Train - Soul Queen
   Genre: soul | Mood: energetic
   [Intense] Score 6.83: Soul song with energetic mood (0.8 energy).

10. Dancehall Vibes - Dancehall Artist
    Genre: reggae | Mood: energetic
    [Intense] Score 6.81: Reggae song with energetic mood (0.9 energy).

======================================================================
```

#### Example 2: Niche lo-fi chill mix

```
🎧 You: create a niche lo-fi mix

✅ Playlist Generated (10 songs, score: 0.7)
======================================================================

1. Chill Vibes - Lo-Fi Beats
   Genre: lofi | Mood: chill
   [General] Score 7.48: Lofi song with chill mood (0.3 energy).

2. Midnight Coding - LoRoom
   Genre: lofi | Mood: chill
   [General] Score 7.46: Lofi song with chill mood (0.4 energy).

3. Library Rain - Paper Lanterns
   Genre: lofi | Mood: chill
   [General] Score 7.21: Lofi song with chill mood (0.3 energy).

4. Focus Flow - LoRoom
   Genre: lofi | Mood: focused
   [General] Score 5.42: Lofi song with focused mood (0.4 energy).

5. Chill Hop Beats - Chill Hop Artist
   Genre: chillhop | Mood: chill
   [General] Score 4.97: Chillhop song with chill mood (0.5 energy).

6. Spacewalk Thoughts - Orbit Bloom
   Genre: ambient | Mood: chill
   [General] Score 4.97: Ambient song with chill mood (0.3 energy).

7. Ethereal Vocals - Ethereal Singer
   Genre: pop | Mood: peaceful
   [General] Score 4.01: Pop song with peaceful mood (0.4 energy).

8. Coffee Shop Stories - Slow Stereo
   Genre: jazz | Mood: relaxed
   [General] Score 3.89: Jazz song with relaxed mood (0.4 energy).

9. Blue Note - Jazz Trio
   Genre: jazz | Mood: melancholic
   [General] Score 3.81: Jazz song with melancholic mood (0.5 energy).

10. Ethereal Spaces - Ambient Artist
    Genre: ambient | Mood: meditative
    [General] Score 3.67: Ambient song with meditative mood (0.2 energy).

======================================================================
```

#### Example 3: Emotional journey from sad to happy

```
🎧 You: sad → happy

✅ Playlist Generated (10 songs, score: 0.7)
======================================================================

1. Coffee Shop Stories - Slow Stereo
   Genre: jazz | Mood: relaxed
   [Sad] Score 6.41: Jazz song with relaxed mood (0.4 energy).

2. Blue Note - Jazz Trio
   Genre: jazz | Mood: melancholic
   [Sad] Score 6.32: Jazz song with melancholic mood (0.5 energy).

3. Ethereal Vocals - Ethereal Singer
   Genre: pop | Mood: peaceful
   [Sad] Score 5.86: Pop song with peaceful mood (0.4 energy).

4. Bluegrass Morning - Bluegrass Band
   Genre: country | Mood: happy
   [Sad] Score 5.67: Country song with happy mood (0.6 energy).

5. R&B Smooth - R&B Singer
   Genre: rnb | Mood: romantic
   [Sad] Score 5.66: Rnb song with romantic mood (0.6 energy).

6. Jazz Cafe - Cool Jazz Trio
   Genre: jazz | Mood: relaxed
   [Sad] Score 5.58: Jazz song with relaxed mood (0.4 energy).

7. Rainy Days - Folk Singer
   Genre: folk | Mood: sad
   [Sad] Score 5.53: Folk song with sad mood (0.4 energy).

8. Sunrise City - Neon Echo
   Genre: pop | Mood: happy
   [Happy] Score 8.34: Pop song with happy mood (0.8 energy).

9. Gym Hero - Max Pulse
   Genre: pop | Mood: intense
   [Happy] Score 7.34: Pop song with intense mood (0.9 energy).

10. Disco Fever - Disco Legends
    Genre: disco | Mood: happy
    [Happy] Score 6.96: Disco song with happy mood (0.9 energy).

======================================================================
```

### Examples Run via main.py

These examples show the system output when invoked through the command line (not interactive mode). Run these directly with: `python -m src.main --interactive` and type each query.

#### Example 4: Custom song count request (5 songs)

Request: "Give me 5 happy songs"

```
🎧 You: Give me 5 happy songs

✅ Playlist Generated (5 songs, score: 0.7)
======================================================================

1. Sunrise City - Neon Echo
   Genre: pop | Mood: happy
   [General] Score 7.90: Pop song with happy mood (0.8 energy). Neon Echo consistently produces high-energy music in pop, synthwave. Pop typically features romantic, happy moods with energy 0.42-0.93. Similar to Gym Hero and Starlight.

2. Gym Hero - Max Pulse
   Genre: pop | Mood: intense
   [General] Score 6.87: Pop song with intense mood (0.9 energy). Max Pulse consistently produces high-energy music in pop. Pop typically features romantic, happy moods with energy 0.42-0.93. Similar to Sunrise City and Starlight.

3. Bluegrass Morning - Bluegrass Band
   Genre: country | Mood: happy
   [General] Score 6.62: Country song with happy mood (0.6 energy). Bluegrass Band consistently produces medium-energy music in country. Country typically features melancholic, nostalgic moods with energy 0.45-0.60. Similar to Country Roads and Desert Wind.

4. Ethereal Vocals - Ethereal Singer
   Genre: pop | Mood: peaceful
   [General] Score 6.60: Pop song with peaceful mood (0.4 energy). Ethereal Singer consistently produces medium-energy music in pop. Pop typically features romantic, happy moods with energy 0.42-0.93. Similar to Ballad of Hope and Singer Songwriter.

5. Disco Fever - Disco Legends
   Genre: disco | Mood: happy
   [General] Score 6.47: Disco song with happy mood (0.9 energy). Disco Legends consistently produces high-energy music in disco. Disco typically features happy moods with energy 0.88-0.88. Similar to Sunrise City and Neon Paradise.

======================================================================
```

#### Example 5: Journey request - calm to energetic

Request: "calm to energetic"

```
🎧 You: calm to energetic

✅ Playlist Generated (10 songs, score: 0.7)
======================================================================

1. Gym Hero - Max Pulse
   Genre: pop | Mood: intense
   [General] Score 7.41: Pop song with intense mood (0.9 energy). Max Pulse consistently produces high-energy music in pop. Pop typically features romantic, happy moods with energy 0.42-0.93. Similar to Sunrise City and Starlight.

2. Sunrise City - Neon Echo
   Genre: pop | Mood: happy
   [General] Score 7.39: Pop song with happy mood (0.8 energy). Neon Echo consistently produces high-energy music in pop, synthwave. Pop typically features romantic, happy moods with energy 0.42-0.93. Similar to Gym Hero and Starlight.

3. Hip Hop Flow - Hip Hop Artist
   Genre: hip-hop | Mood: energetic
   [General] Score 7.07: Hip-Hop song with energetic mood (0.8 energy). Hip Hop Artist consistently produces high-energy music in hip-hop. Hip-Hop typically features energetic, dark moods with energy 0.82-0.89. Similar to Urban Beats and Urban Jungle.

4. Afrobeat Groove - Afrobeat Master
   Genre: afrobeat | Mood: energetic
   [General] Score 7.06: Afrobeat song with energetic mood (0.8 energy). Afrobeat Master consistently produces high-energy music in afrobeat. Afrobeat typically features energetic moods with energy 0.83-0.83. Similar to Soul Train and Dancehall Vibes.

5. Urban Beats - MC Cipher
   Genre: hip-hop | Mood: energetic
   [General] Score 7.03: Hip-Hop song with energetic mood (0.9 energy). MC Cipher consistently produces high-energy music in hip-hop. Hip-Hop typically features energetic, dark moods with energy 0.82-0.89. Similar to Hip Hop Flow and Urban Jungle.

6. Bass & Soul - Funk Legend
   Genre: funk | Mood: energetic
   [General] Score 7.00: Funk song with energetic mood (0.9 energy). Funk Legend consistently produces high-energy music in funk. Funk typically features energetic moods with energy 0.86-0.86. Similar to Dancehall Vibes and Urban Beats.

7. Soul Train - Soul Queen
   Genre: soul | Mood: energetic
   [General] Score 6.95: Soul song with energetic mood (0.8 energy). Soul Queen consistently produces high-energy music in soul. Soul typically features nostalgic, romantic moods with energy 0.48-0.81. Similar to Sunset Boulevard and Soul Searching.

8. Dancefloor Magic - House Masters
   Genre: house | Mood: energetic
   [General] Score 6.90: House song with energetic mood (0.9 energy). House Masters consistently produces high-energy music in house. House typically features energetic, relaxed moods with energy 0.68-0.91. Similar to Deep House and Techno Beat.

9. Dancehall Vibes - Dancehall Artist
   Genre: reggae | Mood: energetic
   [General] Score 6.78: Reggae song with energetic mood (0.9 energy). Dancehall Artist consistently produces high-energy music in reggae. Reggae typically features uplifting, peaceful moods with energy 0.62-0.86. Similar to Island Vibes and Reggae Sunset.

10. Techno Beat - Techno DJ
    Genre: techno | Mood: energetic
    [General] Score 6.76: Techno song with energetic mood (0.9 energy). Techno DJ consistently produces high-energy music in techno. Techno typically features energetic, dark moods with energy 0.62-0.93. Similar to Techno Industrial and Deep Techno.

======================================================================
```

#### Example 6: Genre + mood query - classical with peaceful vibes

Request: "I want classical music with peaceful vibes"

```
🎧 You: I want classical music with peaceful vibes

✅ Playlist Generated (10 songs, score: 0.7)
======================================================================

1. Bach Suite No.1 - Classical Ensemble
   Genre: classical | Mood: meditative
   [General] Score 6.87: Classical song with meditative mood (0.1 energy). Classical Ensemble consistently produces low-energy music in classical. Classical typically features intense, meditative moods with energy 0.15-0.75. Similar to Moonlight Sonata and Ambient Piano.

2. Electronic Zen - Ambient Electronics
   Genre: electronic | Mood: meditative
   [General] Score 6.28: Electronic song with meditative mood (0.3 energy). Ambient Electronics consistently produces low-energy music in electronic. Electronic typically features uplifting, playful moods with energy 0.30-0.95. Similar to Minimal Beats and Echoes.

3. Deep Techno - Techno Minimalist
   Genre: techno | Mood: meditative
   [General] Score 6.17: Techno song with meditative mood (0.6 energy). Techno Minimalist consistently produces medium-energy music in techno. Techno typically features energetic, dark moods with energy 0.62-0.93. Similar to Techno Industrial and Techno Beat.

4. Ambient Piano - Piano Artist
   Genre: classical | Mood: peaceful
   [General] Score 5.73: Classical song with peaceful mood (0.3 energy). Piano Artist consistently produces low-energy music in classical. Classical typically features intense, meditative moods with energy 0.15-0.75. Similar to Melancholy Waltz and Bach Suite No.1.

5. Ethereal Spaces - Ambient Artist
   Genre: ambient | Mood: meditative
   [General] Score 5.34: Ambient song with meditative mood (0.2 energy). Ambient Artist consistently produces low-energy music in ambient. Ambient typically features meditative, peaceful moods with energy 0.18-0.28. Similar to Forest Meditation and Ambient Rain.

6. Forest Meditation - Nature Sounds
   Genre: ambient | Mood: meditative
   [General] Score 5.25: Ambient song with meditative mood (0.2 energy). Nature Sounds consistently produces low-energy music in ambient. Ambient typically features meditative, peaceful moods with energy 0.18-0.28. Similar to Ethereal Spaces and Ambient Rain.

7. Melancholy Waltz - String Quartet
   Genre: classical | Mood: sad
   [General] Score 5.15: Classical song with sad mood (0.3 energy). String Quartet consistently produces low-energy music in classical. Classical typically features intense, meditative moods with energy 0.15-0.75. Similar to Ambient Piano and Moonlight Sonata.

8. Moonlight Sonata - Classical Ensemble
   Genre: classical | Mood: melancholic
   [General] Score 4.60: Classical song with melancholic mood (0.2 energy). Classical Ensemble consistently produces low-energy music in classical. Classical typically features intense, meditative moods with energy 0.15-0.75. Similar to Melancholy Waltz and Bach Suite No.1.

9. Sunrise City - Neon Echo
   Genre: pop | Mood: happy
   [General] Score 4.41: Pop song with happy mood (0.8 energy). Neon Echo consistently produces high-energy music in pop, synthwave. Pop typically features romantic, happy moods with energy 0.42-0.93. Similar to Gym Hero and Starlight.

10. R&B Smooth - R&B Singer
    Genre: rnb | Mood: romantic
    [General] Score 4.41: Rnb song with romantic mood (0.6 energy). R&B Singer consistently produces medium-energy music in rnb. Rnb typically features romantic moods with energy 0.58-0.58. Similar to Starlight and Sunset Boulevard.

======================================================================
```

### Multi-Phase Journey Example

Request: sad → happy

The system automatically detects the arrow notation and creates a 2-phase playlist:
- Phase 1 (sad): Lower energy, melancholic mood
- Phase 2 (happy): Higher energy, uplifting mood

Output shows phase labels for each song, allowing you to follow the emotional arc through the playlist.

---

## Safety & Validation (Guardrails)

The system includes multiple layers of validation to ensure safe operation:

### Input Validation

User input is checked for injection attacks, length limits, and malformed content before processing.

Input validation example:
```
Input: "Give me happy songs'; DROP TABLE songs; --"
Check: Detects SQL injection pattern
Result: ❌ Rejected - "Message contains potentially harmful content"
```

Oversized input example:
```
Input: (2500 character message)
Check: Exceeds 2000 character limit
Result: ❌ Rejected - "Message exceeds 2000 characters"
```

Valid input example:
```
Input: "Give me a happy pop playlist"
Check: No injection patterns, 29 characters
Result: ✅ Accepted - sanitized for processing
```

### Input Sanitization

Once validated, input is cleaned of control characters and normalized for safe LLM processing.

Sanitization example:
```
Input:    "Give  me   happy\x00songs"  (with null byte and extra spaces)
Process: Remove control chars, normalize whitespace
Result:   "Give me happy songs"
```

### Song Data Validation

Every song in the catalog must pass validation before being recommended:

Required fields check:
```
Song: {id: 1, title: "Sunrise City", artist: "Neon Echo", genre: "pop", ...}
Check: All required fields present (id, title, artist, genre, mood, energy, popularity, release_decade)
Result: ✅ Passed
```

Numeric range validation:
```
Song: {energy: 0.82, popularity: 78, release_decade: 2020, ...}
Check: energy in [0.0, 1.0]? ✅  | popularity in [0.0, 100.0]? ✅  | release_decade in [1600, 2100]? ✅
Result: ✅ Passed
```

Invalid numeric example:
```
Song: {energy: 1.5, popularity: 120, ...}
Check: energy out of range [0.0, 1.0] → ❌  | popularity out of range [0.0, 100.0] → ❌
Result: ❌ Rejected
```

### Output Sanitization

Generated explanations are sanitized to prevent injection before display:

HTML escaping example:
```
Output:   "Track <script>alert('xss')</script> is great"
Process: Escape HTML entities and remove tags
Result:   Safe HTML-escaped output
```

### Resource Limits

Requests for multiple items are clamped to safe ranges to prevent resource exhaustion:

Retrieval count example:
```
Request:  "Give me 500 songs"
Check:    Clamp to range [1, 50]
Result:   Returns 50 songs instead of 500
```

---

## Design Decisions

Five-Phase Architecture

The system splits into five seperate phases, being the Knowledge Base, Intent Resolver, Matcher Explainer, Playlist Agent, and Interactive CLI. Each phase handles one concern and is independently testable.

Trade-off: This architecture was more modular and testable, but added difficulty with coordination with the Phase 4 agentic feedback loop. I judged that this was easily worth it for clear separation and easy debugging.

GMEWS Heuristic Scoring

Instead of training an ML model, I used weighted formulas for genre, mood, energy, acousticness, and danceability. Each of these weights has rationality behind it that was achieved through testing trial and error.

Trade-off: This approach was simpler and more interpretable at the cost of being less accurate than Machine Learning. I judged that user understanding of why a song was recommended mattered more than what the AI estimated to be a 10% accuracy gain.

Multi-Phase Journey Detection

When users write "sad → happy" or "calm to energetic", the system treats it as a two part narrative playlist with seperate moods on each end.

Trade-off: This enables expressive requests but adds the need specific deduplication and constraint tuning. I judged that the expressiveness was worth the extra complexity.

Comprehensive Input Validation

All user input is checked for injection patterns, file traversal, code execution, and control characters before processing.

Trade-off: This approach lead to the agent rejecting some unusual but legitimate requests. However, I asserted that this level of safety was worth a querry occasionally getting incorrectly rejected.

---

## Testing Summary

All 310 tests passed with 100% success rate. The system was validated across 5 phases with comprehensive edge-case and guardrail testing.

### Test Results by Phase

| Phase | Category | Test Count | Status | Key Validations |
|-------|----------|-----------|--------|-----------------|
| Phase 1 | Knowledge Base | 38 | All Passed | Song similarity, RAG retrieval, artist/genre profiling, metadata validation |
| Phase 2 | Intent Resolver | 55 | All Passed | Genre/mood/energy extraction, mode selection, injection attack detection, sanitization |
| Phase 3 | Matcher & Explainer | 22 | All Passed | GMEWS scoring, explanation generation, RAG enrichment across all modes |
| Phase 4 | Playlist Agent | 41 | All Passed | Multi-phase journey detection, energy filtering, size validation, constraint adjustment |
| Phase 5 | Interactive CLI | 35 | All Passed | Session management, rate limiting, command parsing, feedback loop |
| Integration & Guardrails | Cross-system | 119 | All Passed | End-to-end workflows, injection prevention, resource limits, error handling |
| **Total** | | **310** | **100%** | |

### Edge Cases & Scenarios Tested

System Strengths (all passed):
- Multi-phase journey detection with arrow notation (e.g., "sad → happy", "calm to energetic")
- Energy-level filtering for high/low intensity playlists (running, study, sleep)
- Niche song discovery with popularity constraints
- Genre/mood extraction with hyphenated terms ("lo-fi", "hip-hop")
- Custom playlist sizing (5-song, 15-song requests, clamped to 1-100 range)
- Confidence scoring across 0.5-1.0 range based on extracted fields
- Phase-specific mood mapping (study→calm, running→energetic)

Guardrail Validation (all rejected malicious input):
- SQL injection patterns (detected and rejected)
- File path traversal attempts (../../etc/passwd rejected)
- Code execution injection (__import__, exec, eval rejected)
- Oversized messages (>2000 chars rejected)
- Control characters and whitespace normalization
- Empty/whitespace-only input rejection

Error Handling & Recovery (all handled gracefully):
- Resolver errors fall back to sensible defaults
- Empty song catalog returns empty playlist instead of crashing
- Single-song catalogs handled correctly
- Non-integer playlist sizes converted or rejected
- Zero, negative, or oversized requests clamped to valid range [1, 100]
- Invalid mood/genre combinations map to nearest valid option

### Confidence & Accuracy

- Average confidence score: 0.78 (range 0.5-1.0)
- Confidence improves 0.1 per successfully extracted field (genre, mood, energy, etc.)
- System defaults gracefully when fields missing: 5 defaults (pop, happy, 0.6 energy, etc.)
- Explanation quality improved after adding RAG context and advanced GMEWS factors
- Playlist quality validation: average score 0.75+ before adjustment loop
- Diversity penalties prevent artist/genre clustering while preserving top-quality matches

---

## Stretch Feature 1: RAG Enhancement

The system evolved from a hardcoded static CSV to support dynamic, multi-format data sources with single and multi-source loading. This improvement unlocked several benefits:

Before: Songs were loaded only from a single CSV file at startup. To test with different datasets, users had to modify code or file paths.

After: Users can now:
- Load from CSV or JSON files interchangeably
- Switch data sources mid-session with `load_data data/my_songs.json`
- Merge multiple sources into one catalog interactively with `load_data_merge file1.csv file2.json`
- Merge from command line with `--data-sources`: `python -m src.main -i --data-sources data/songs.csv data/songs_example.json`
- Use the system with custom catalogs (local collections, exported playlists, test datasets)
- Start interactive mode with a single data source: `python -m src.main -i --data-source data/songs_example.json`

Example (single source switching):
```bash
# Start with test set (37 songs: 22 duplicates + 15 unique)
python -m src.main -i --data-source data/songs_example.json

🎧 You: give me happy pop songs
✓ Loaded 2 pop songs

# Switch to full catalog mid-session
🎧 You: load_data data/songs.csv
✓ Loaded 100 songs
✓ Reinitialized system with new data source

🎧 You: give me happy pop songs
✓ Loaded 8 pop songs (more variety now)
```

Example (multi-source merge from command line):
```bash
# Start with merged sources from command line
python -m src.main -i --data-sources data/songs.csv data/songs_example.json

Loading and merging 2 data source(s)...
✓ Merged 115 unique songs (duplicates automatically removed)
✓ Initialized all 5 phases

🎧 You: give me happy pop songs
✓ Loaded 12 pop songs (expanded variety from merged sources)
```

Example (multi-source merge during interactive session):
```bash
# Start with one dataset, merge more mid-session
python -m src.main -i --data-source data/songs.csv

🎧 You: give me happy pop songs
✓ Loaded 8 pop songs

# Merge additional sources interactively
🎧 You: load_data_merge data/songs.csv data/songs_example.json
📂 Merging 2 data source(s)...
✓ Merged 115 unique songs
✓ Reinitialized system with merged data

🎧 You: give me happy pop songs
✓ Loaded 12 pop songs (more options now)
```

Impact on Output Quality:
- Small datasets (37 songs) reveal edge cases and limitations early
- Full datasets (100 songs) provide richer recommendations with better diversity
- Merged datasets (115+ songs) combine multiple sources while deduplicating automatically
- Custom datasets let users test domain-specific music (classical only, indie gems, etc.)
- Switching/merging data sources shows how recommendations scale—what works for 37 songs differs from 115+

The modular data loader (`src/data_loader.py`) handles validation, type conversion, deduplication, and error reporting consistently across formats and multiple sources, making the system resilient to data format variations.

---

## System Evaluation

The `scripts/eval_system.py` script runs the system against 13 predefined test cases covering single-phase requests, multi-phase journeys, specific sizes, and edge cases. It generates a detailed report with pass/fail status, confidence scores (0.0-1.0), and phase validation.

Run the evaluation:
```bash
python3 scripts/eval_system.py
```

Output includes:
- Pass/fail status for each test (100% pass rate = all test cases working)
- Confidence score per test based on playlist accuracy, validation, and phase correctness
- Detailed breakdown showing extracted phases, playlist size, and validation score
- Confidence distribution chart (Excellent/Good/Fair/Poor tiers)

Example test cases:
- "Create a playlist starting sad and ending happy" (multi-phase journey)
- "I want an 18 song swimming playlist that goes from intense to slow" (complex scenario)
- "Build a workout playlist" (single-phase with keyword)

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Building this system taught me that problem solving in AI is really about making several trade offs to enusre the best overall result. I was forced to make many several design choices, including safety over speed and modularity over simplicity. None of these choices were the clear correct choice, but they just reflected my overall design philosophy for this specific problem. I also realized how design decisions hide their consequences until much later. Binary genre matching was an approach that I had used throughout this project including before the extenstions.  However, during the testing phase I discovered that recommends very little niche music even when people specifically request it.  It ended up prioritizing popular mainstream music to a very high degree. The thing I most got out of creating this playlist agent is that good AI design means understanding how to be as accurate as possible with cost benefit analysis and using this knowledge to guide the AI assistant through the process.  


