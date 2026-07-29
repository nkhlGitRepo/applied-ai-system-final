# 🎵 Music Recommender Simulation

## Project Summary

A complete 5-phase music recommendation system that combines knowledge representation, natural language understanding, and intelligent ranking with RAG-enhanced explanations.

**Key Features:**
- **Natural Language Processing:** Understands user requests like "Create a workout playlist" or "emotional journey from sad to happy"
- **Multi-phase Playlists:** Automatically detects journey requests and decomposes them into logical phases with distinct musical progressions
- **Explainable AI:** Every recommendation includes plain-English explanations citing genre matches, mood alignment, energy fit, and audio characteristics
- **Interactive Demo:** Try the system through a terminal chat interface with rate limiting (100 msgs/hour) and session tracking (30-day expiry)
- **Comprehensive Testing:** 289 tests verifying method interactions, edge cases, and system integration across all 5 phases

---

## How The System Works

### 5-Phase Architecture

**Phase 1: Knowledge Base (RAG)**
- Indexes all songs with 9+ attributes (genre, mood, energy, tempo, valence, danceability, acousticness, popularity, decade)
- Provides Retrieval-Augmented Generation (RAG) context: artist profiles, genre knowledge, similar songs
- Powers explanation enrichment by retrieving supporting context

**Phase 2: Intent Resolver**
- Parses natural language user requests to extract structured preferences
- Extracts: favorite_genre, favorite_mood, target_energy, acoustic_preference
- Confidence-based scoring: 0.5 base + 0.1 per field extracted (max ~0.8 confidence)
- Automatically selects best scoring mode (genre-first, discovery, niche-friendly, personality)

**Phase 3: Matcher & Explainer**
- Scores songs using GMEWS algorithm
- Generates explanations combining: score reasoning + RAG context + artist insights
- Provides 4 reasoning dimensions: genre match, mood match, energy distance, acoustic fit

**Phase 4: Playlist Agent (Agentic Loop)**
- Orchestrates Phases 1-3 in a PLAN → RETRIEVE → EXECUTE → VALIDATE → ADJUST loop
- **Journey Detection:** Automatically recognizes multi-phase requests via 5 strategies:
  - Arrow notation: `"sad → happy"`
  - Pattern matching: `"from X to Y"`, `"starting with X, ending with Y"`
  - Playlist type keywords: `workout`, `dinner`, `study`, `party`, `sleep`, `morning`
  - Explicit journey keywords: `journey`, `arc`, `transition`, `progression`
  - Mood keywords in context
- **Validation & Adjustment:** Validates playlist quality (score ≥0.7), progressively relaxes constraints if needed

**Phase 5: Interactive CLI**
- Single-query mode: `run_single_query()`
- Multi-turn interactive mode: `run_interactive()` for terminal chat
- Rate limiting: 100 messages per hour per session
- Session tracking: 30-day conversation expiry

### Scoring Algorithm (GMEWS)

```
SCORE = G + M + (E × 1.5) + (A × 1.0) + (D × 0.3)

  G: 2.0 if genre matches, else 0.0
  M: 2.0 if mood matches, else 0.0  
  E: 1.0 - |song.energy - target_energy| (distance-based, 0-1 range)
  A: acousticness if user likes acoustic, else 1.0 - acousticness
  D: danceability × 0.3 if target_energy ≥ 0.7, else 0.0
```

**Design Rationale:** Genre and mood are binary "deal-breakers" (2.0 points each). Energy uses distance-based scoring so users get variety within their preferred range. Acoustic preference is a secondary modifier. Danceability bonus only applies to high-energy contexts.


---

## Getting Started

### Setup

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac/Linux
   .venv\Scripts\activate         # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify data file exists:**
   - The system expects `data/songs.csv` with songs to recommend

### Running the System

The system has multiple modes depending on your use case:

#### Interactive Demo Mode (Recommended)
Chat naturally with the system in a terminal interface:
```bash
python -m src.main --interactive
# or
python -m src.main -i
```

**Supported playlist queries:**
- Simple requests: `"Give me happy pop songs"`
- Playlist types: `"Create a workout playlist"`, `"I need a study playlist"`
- Journey playlists: `"sad → happy"`, `"calm to energetic"`, `"Create a dinner playlist from uplifting to chill"`
- Niche/unpopular songs: `"Give me some hidden gems"`, `"I want obscure indie songs"`, `"Find me underground rock"`
- Custom sizes: `"Create a 5-song workout playlist"`, `"Give me 8 songs"`, `"playlist of size 15"`

**Interactive commands:**
- `help` or `?` → Show help with query examples
- `stats` → Display session statistics (queries made, rate limit status)
- `exit`, `quit`, `bye`, or `goodbye` → Exit the chat gracefully
- Ctrl+C → Exit the chat (keyboard interrupt)

**Playlist size notes:**
- Default size is **10 songs** if not specified
- You can specify size using patterns like: `"5-song"`, `"10 songs"`, `"size 12"`, or `"of size 8"`
- Maximum size is **100 songs** or the full catalog, whichever is smaller
- If you request more songs than available, the system returns what's available

**Rate limiting and sessions:**
- Maximum **100 messages per hour** per session
- Session tracks conversation history for **30 days**
- Use the `stats` command to see remaining messages and session age

**Example interaction:**
```
🎧 You: Create a workout playlist
✅ Playlist Generated (5 songs, score: 0.85)
======================================================================

1. GYM HERO - Max Pulse
   Genre: pop | Mood: intense
   [Energetic] Genre match: pop (+2.0), Mood match: intense (+2.0), ...

...
```

#### Single Query Mode
Process one request and see results:
```bash
python -m src.main --profile high_energy_pop --mode genre-first
```

**Available profiles:** `high_energy_pop`, `chill_lofi`, `deep_intense_rock`, and 5 adversarial profiles

**Available scoring modes:** `genre-first`, `discovery`, `niche-friendly`, `personality`

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

Run all 289 tests verifying the system:
```bash
pytest
```

View test coverage:
```bash
pytest --cov=src --cov-report=html
```

**Test breakdown:**
- Phase 1 (Knowledge Base): 38 tests
- Phase 2 (Intent Resolver): 52 tests
- Phase 3 (Matcher & Explainer): 22 tests
- Phase 4 (Playlist Agent): 39 tests
- Phase 5 (Interactive CLI): 35 tests
- **Total: 289 tests**

---

## Sample Interaction: Interactive Mode

**Request:** Create a workout playlist

```
🎵 MUSIC PLAYLIST GENERATOR - Interactive Demo
================================================================================
Loading system...
✓ Loaded 20 songs
✓ Initialized all 5 phases (Knowledge Base → Intent Resolver → Matcher → Agent → CLI)

================================================================================
EXAMPLES OF WHAT YOU CAN ASK:
================================================================================

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

================================================================================
START CHATTING (type your first request below):
================================================================================

🎧 You: Create a workout playlist

✅ Playlist Generated (5 songs, score: 0.82)
======================================================================

1. GYM HERO - Max Pulse
   Genre: pop | Mood: intense
   [Energetic] Genre match: pop (+2.0), Mood match: intense (+2.0), ...

2. STORM RUNNER - Voltline
   Genre: rock | Mood: intense
   [Intense] Genre match: rock (partial, +1.0), Energy 0.91 matches high-energy workout...

3. ELECTRIC DREAMS - Pulse Collective
   Genre: electronic | Mood: uplifting
   [Energetic] Perfect for workout energy. Electronic production builds momentum...

4. GLITCH GARDEN - Experimental Labs
   Genre: experimental | Mood: intense
   [Intense] Maintains high energy with unconventional sound design...

5. NEON NIGHTS - Neon Echo
   Genre: pop | Mood: happy
   [Energetic] Uplifting finish to the workout with positive energy...

======================================================================

🎧 You: quit
Goodbye! 👋
```

### Multi-Phase Journey Example

**Request:** sad → happy

The system automatically detects the arrow notation and creates a 2-phase playlist:
- **Phase 1 (sad):** Lower energy, melancholic mood
- **Phase 2 (happy):** Higher energy, uplifting mood

Output shows phase labels for each song, allowing you to follow the emotional arc through the playlist.

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

Phase 4 Step 1: Adversarial Profile Test Results

Profile: Extreme Low Energy (classical/meditative at 0.10 energy)
```
======================================================================
TOP RECOMMENDATIONS FOR: EXTREME LOW ENERGY
Profile: genre=classical, mood=meditative, energy=0.1, acoustic=yes
======================================================================

1. BACH SUITE NO.1
   Artist: Classical Ensemble | Genre: classical
   Score: 6.40 / 6.0

   Why you'll like it:
   • Genre match: classical (+2.0)
   • Mood match: meditative (+2.0)
   • Energy: 0.15 vs target 0.10 (1.42)
   • Acousticness: 0.98 (acoustic)
   • Danceability: N/A (low energy user)

2. SPACEWALK THOUGHTS
   Artist: Orbit Bloom | Genre: ambient
   Score: 2.15 / 6.0

3. LIBRARY RAIN
   Artist: Paper Lanterns | Genre: lofi
   Score: 1.98 / 6.0

4. COFFEE SHOP STORIES
   Artist: Slow Stereo | Genre: jazz
   Score: 1.98 / 6.0

5. FOCUS FLOW
   Artist: LoRoom | Genre: lofi
   Score: 1.83 / 6.0
```

Profile: Niche Genre No-Match (synthwave preference)
```
======================================================================
TOP RECOMMENDATIONS FOR: NICHE GENRE NOMATCH
Profile: genre=synthwave, mood=moody, energy=0.75, acoustic=no
======================================================================

1. NIGHT DRIVE LOOP
   Artist: Neon Echo | Genre: synthwave
   Score: 6.50 / 6.0

   Why you'll like it:
   • Genre match: synthwave (+2.0)
   • Mood match: moody (+2.0)
   • Energy: 0.75 vs target 0.75 (1.50)
   • Acousticness: 0.78 (electronic)
   • Danceability bonus: 0.73 (+0.22)

2. ELECTRIC DREAMS
   Artist: Pulse Collective | Genre: electronic
   Score: 2.51 / 6.0

3. GLITCH GARDEN
   Artist: Experimental Labs | Genre: experimental
   Score: 2.47 / 6.0

4. SUNRISE CITY
   Artist: Neon Echo | Genre: pop
   Score: 2.45 / 6.0

5. GYM HERO
   Artist: Max Pulse | Genre: pop
   Score: 2.44 / 6.0
```

Profile: Conflicting Energy/Mood (0.90 energy + melancholic mood)
```
======================================================================
TOP RECOMMENDATIONS FOR: CONFLICTING ENERGY MOOD
Profile: genre=indie, mood=melancholic, energy=0.9, acoustic=no
======================================================================

1. NEON THOUGHTS
   Artist: Indie Void | Genre: indie
   Score: 3.84 / 6.0

   Why you'll like it:
   • Genre match: indie (+2.0)
   • Mood mismatch: nostalgic vs melancholic (0.0)
   • Energy: 0.61 vs target 0.90 (1.06)
   • Acousticness: 0.57 (electronic)
   • Danceability bonus: 0.68 (+0.20)

2. DUSTY ROADS
   Artist: The Wanderers | Genre: country
   Score: 3.38 / 6.0

3. MIDNIGHT BLUES
   Artist: The Rooters | Genre: blues
   Score: 3.34 / 6.0

4. GYM HERO
   Artist: Max Pulse | Genre: pop
   Score: 2.67 / 6.0

5. ELECTRIC DREAMS
   Artist: Pulse Collective | Genre: electronic
   Score: 2.65 / 6.0
```

Profile: Acoustic/Rock Contradiction (rock + acoustic preference)
```
======================================================================
TOP RECOMMENDATIONS FOR: ACOUSTIC ROCK CONTRADICTION
Profile: genre=rock, mood=intense, energy=0.88, acoustic=yes
======================================================================

1. STORM RUNNER
   Artist: Voltline | Genre: rock
   Score: 5.75 / 6.0

   Why you'll like it:
   • Genre match: rock (+2.0)
   • Mood match: intense (+2.0)
   • Energy: 0.91 vs target 0.88 (1.46)
   • Acousticness: 0.10 (electronic)
   • Danceability bonus: 0.66 (+0.20)

2. GLITCH GARDEN
   Artist: Experimental Labs | Genre: experimental
   Score: 3.77 / 6.0

3. GYM HERO
   Artist: Max Pulse | Genre: pop
   Score: 3.74 / 6.0

4. ISLAND VIBES
   Artist: Reggae Kings | Genre: reggae
   Score: 2.09 / 6.0

5. MIDNIGHT BLUES
   Artist: The Rooters | Genre: blues
   Score: 1.99 / 6.0
```



---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

The catalog has only 20 songs, which makes recommendations limited and therefore unrealistic for getting truly accurate results.  Most genres are represented by just one or two songs, so users with niche preferences get stuck while mainstream users thrive.  Another issue with the algorithm is that it cannot understand lyrics to judge a song's appeal beyond its basic features.  Finally, the binary genre matching creates filter bubbles that prevent discovering songs outside a user's stated preferences.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this

While working on this project, I learned that recommenders work by converting song features into a numerical score that ranks items for each user.  This is achieved through weighted math, where each feature becomes a number that gets combined with others based on weights chosen.  The algorithm just applies the patterns we define and ranks items accordingly.  This means a recommender is only as good as the data we are able to acquire and the algorithm that purposes that data to deliver accurate results.

I also learned how easily bias creeps in through design choices that seem inconsequential on the surface.  Binary genre matching appears to be fair until you realize it creates unfairness by hacing mainstream users get multiple recommendations while fans of more niche content can get stuck with only one.  When setting the weights, it is important to choose whether energy matters more than genre and if danceability deserves a bonus.  


