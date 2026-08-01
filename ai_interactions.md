# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Stretch Feature 2: Agentic Workflow Enhancement

### Implementation
Added comprehensive reasoning trace logging to capture all 6 steps of the agentic loop in Phase 4:

1. **UNDERSTAND** - Extract phases from natural language query
2. **PLAN** - Create scoring preferences for each phase  
3. **RETRIEVE** - Get song recommendations from matcher
4. **EXECUTE** - Build final playlist with deduplication
5. **VALIDATE** - Check if playlist meets user intent (0.7 threshold)
6. **ADJUST** - Refine plan and retry if validation score < 0.7


### Example Traces

#### Example 1: Multi-Phase Journey

Query: "Create a sad to happy journey"

**Trace Flow:**
```
Step 1: UNDERSTAND → Extracted 2 phases: ["happy", "sad"] (from arrow/journey pattern)
Step 2: PLAN → Created preferences for 2 phases using personality mode
Step 3: RETRIEVE → Retrieved 3 songs for happy phase, 3 songs for sad phase
Step 4: EXECUTE → Built 5-song playlist combining both phases
Step 5: VALIDATE → Validation score 0.70/1.0 (meets 0.7 threshold) ✓
```

**Full Trace:**
```
## Query: "Create a sad to happy journey"

### Reasoning Trace

#### Step 1: UNDERSTAND
Input: {"query": "Create a sad to happy journey"}
Output: {"phases": ["happy", "sad"]}
Reasoning: Extracted 2 phase(s) from query: ['happy', 'sad']

#### Step 2: PLAN
Input: {"phases": ["happy", "sad"], "mode": "personality"}
Output: {"base_prefs": {...}, "phase_count": 2}
Reasoning: Created preferences for 2 phase(s) using mode: personality

#### Step 3: RETRIEVE
Input: {"phases": ["happy", "sad"]}
Output: {"recommendations_per_phase": {"happy": 3, "sad": 3}}
Reasoning: Retrieved song recommendations for each phase: {'happy': 3, 'sad': 3}

#### Step 4: EXECUTE
Input: {"target_k": 5, "total_phases": 2}
Output: {"playlist_size": 5, "phase_labels": ["happy", "happy", "happy", "sad", "sad"]}
Reasoning: Built playlist with 5 songs, covering 2 unique phases

#### Step 5: VALIDATE
Input: {"playlist_size": 5, "phase_coverage": 2}
Output: {"validation_score": 0.7}
Reasoning: Initial validation: 0.70/1.0 (threshold: 0.7)

### Results
- Validation Score: 0.70 / 1.0
- Playlist Size: 5 songs
- Unique Songs: 5
```

#### Example 2: Simple Genre Search

Query: "Give me happy pop songs"

**Trace Flow:**
```
Step 1: UNDERSTAND → Extracted 1 phase: ["general"] (simple request, no journey)
Step 2: PLAN → Created preferences using personality mode (pop + happy)
Step 3: RETRIEVE → Retrieved 5 song recommendations matching preferences
Step 4: EXECUTE → Built 5-song playlist
Step 5: VALIDATE → Validation score 0.70/1.0 (meets threshold) ✓
```

**Note:** Single-phase requests don't trigger ADJUST loop as long as validation ≥ 0.7. Multi-phase or complex requests may iterate (max 3 attempts) if validation score < 0.7.

### Optional Trace Logging

**Traces are disabled by default** to avoid disk bloat from generating logs for every query. Users can enable tracing on-demand:

#### Command Line
```bash
# Enable traces at startup
python -m src.main -i --enable-traces

# Run without traces (default)
python -m src.main -i
```

#### Interactive Commands (during session)
```
traces              # Show current trace status
traces on           # Enable trace logging for this session
traces off          # Disable trace logging for this session
```

#### Programmatic
```python
# Traces disabled by default
cli = PlaylistCli(resolver, matcher, agent, kb, songs)

# Enable traces
cli = PlaylistCli(resolver, matcher, agent, kb, songs, enable_traces=True)

# Traces automatically saved only when enabled
cli.run_single_query("Create a sad to happy journey")
```

#### Storage Location
When enabled, traces are saved to [`logs/reasoning_traces/`](../logs/reasoning_traces/) (in .gitignore):
- `trace_YYYYMMDD_HHMMSS.json` — Structured data (for programmatic analysis)
- `trace_YYYYMMDD_HHMMSS.md` — Human-readable narrative (for debugging)

**Recent traces:** [`logs/reasoning_traces/`](../logs/reasoning_traces/)

---




