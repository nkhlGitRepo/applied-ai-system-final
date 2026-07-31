# Music Advisor Development Guide

**Project**: AI110 Module 3 - Music Recommender with RAG & Agentic Workflow  
**Status**: All 5 phases complete, 289 tests passing  
**Structure**: 5-phase simplified implementation, flat file organization

---

## Quick Navigation

| Need | File/Command |
|------|--------------|
| Run all tests | `pytest tests/ -q` |
| Run Phase N tests | `pytest tests/test_phaseN_* -v` |
| Check structure | `ls -1 src/phase*.py tests/test_phase*.py` |
| Safety requirements | Section "Guardrails" below |
| Implementation details | See "5 Phases" section |
| Project history | `Music_Recommender_Conversation_Context.md` |

---

## File Structure (Minimal)

```
src/                              # All Python modules
├── recommender.py               # Core GMEWS algorithm (don't modify)
├── main.py                      # CLI (don't modify)
├── guardrails.py                # Validators for all phases ✅
├── phase1_knowledge_base.py     # ✅ DONE - 38 tests
├── phase2_intent_resolver.py    # ✅ DONE - 52 tests
├── phase3_matcher_explainer.py  # ✅ DONE - 22 tests
├── phase4_playlist_agent.py     # ✅ DONE - 39 tests
└── phase5_interactive_cli.py    # ✅ DONE - 35 tests

tests/
├── test_recommender.py          # 103 core tests (don't modify)
├── test_phase1_knowledge_base.py # ✅ DONE - 38 tests
├── test_phase2_intent_resolver.py # ✅ DONE - 52 tests
├── test_phase3_matcher_explainer.py # ✅ DONE - 22 tests
├── test_phase4_playlist_agent.py # ✅ DONE - 39 tests
└── test_phase5_interactive_cli.py # ✅ DONE - 35 tests

data/
└── songs.csv                    # 40-song catalog (don't modify)

assets/                          # For future diagrams
```

**Total**: 6 directories, ~24 files. Everything flat and navigable.

---

## 5-Phase Implementation Plan

### Phase 1 ✅ DONE (Knowledge Base)
- **File**: `src/phase1_knowledge_base.py` + `src/guardrails.py`
- **What**: Song indexing, 5 retrieval functions, similarity metric
- **Tests**: 38 passing in `tests/test_phase1_knowledge_base.py`
- **Imports**: `from src.phase1_knowledge_base import KnowledgeBase`

### Phase 2 🔲 Intent Resolver (NLP + Preferences)
- **File**: `src/phase2_intent_resolver.py`
- **What**: Parse natural language using Claude API → structured intent
- **API**: `resolve(message) → (user_prefs, recommended_mode, confidence)`
- **Guardrails**: Input validation, prompt injection prevention, safe logging
- **Tests**: `tests/test_phase2_intent_resolver.py` (target: >90% coverage)

### Phase 3 ✅ DONE (Matcher-Explainer)
- **File**: `src/phase3_matcher_explainer.py` + `src/guardrails.py`
- **What**: Call GMEWS from recommender + retrieve RAG context + generate explanations
- **API**: `match_and_explain(user_prefs, songs, k=5, mode) → [(song, score, explanation), ...]`
- **Tests**: 22 passing in `tests/test_phase3_matcher_explainer.py`
- **Imports**: `from src.phase3_matcher_explainer import MatcherExplainer, create_matcher_explainer`

### Phase 4 ✅ DONE (Playlist Agent)
- **File**: `src/phase4_playlist_agent.py`
- **What**: Unified agentic loop: UNDERSTAND → PLAN → RETRIEVE → EXECUTE → VALIDATE → ADJUST
- **API**: `plan_and_execute(message) → Playlist` (songs, explanations, phase_labels, validation_score)
- **Example**: "Create journey sad→happy" extracts phases, creates phase-specific preferences, validates progression
- **Features**: Phase extraction from arrow notation, preference modification per phase, validation loop with 3 max adjustments
- **Tests**: 39 passing in `tests/test_phase4_playlist_agent.py`
- **Imports**: `from src.phase4_playlist_agent import PlaylistAgent, Playlist, create_playlist_agent`

### Phase 5 ✅ DONE (Interactive CLI)
- **File**: `src/phase5_interactive_cli.py`
- **What**: Single-query and multi-turn conversation modes with rate limiting and session management
- **API**:
  - `cli.run_single_query(query)` → formatted string output
  - `cli.run_interactive()` → multi-turn conversation loop
- **Features**: Rate limiting (max 100 msg/hr), session expiry (30 days), output sanitization, error handling
- **Tests**: 35 passing in `tests/test_phase5_interactive_cli.py`
- **Imports**: `from src.phase5_interactive_cli import PlaylistCli, ConversationSession, create_playlist_cli`

---

## Guardrails (Safety First)

**Apply these to each phase** (see `GUARDRAILS.md` for full details):

| Phase | Guardrail | Implementation |
|-------|-----------|-----------------|
| 1 | Content filtering | `validate_song_metadata()` ✅ in `guardrails.py` |
| 2 | Input validation | Sanitize user messages, reject injections |
| 2 | Prompt injection | Structured LLM prompts, schema validation |
| 2 | Safe logging | No credentials/full messages in logs |
| 3 | Output sanitization | HTML escape, verify scores in range |
| 4 | Validation logic | Don't over-constrain; max 3 adjustments |
| 5 | Rate limiting | Max 100 messages/hour per session |
| 5 | History expiry | Delete conversations after 30 days |

**Guardrails utilities in `src/guardrails.py`**:
- `validate_song_metadata(song)` ✅ Phase 1
- `validate_retrieval_count(count)` ✅ Phase 1
- `validate_user_input(message)` 🔲 Phase 2
- `sanitize_explanation(text)` 🔲 Phase 3
- `validate_retrieval_count()` already handles Phase 5 limits

---

## Implementation Checklist (Per Phase)

### Before Starting Phase N
- [ ] Read this section
- [ ] Read `GARDRAILS.md` for phase-specific safety requirements
- [ ] Check stub file exists: `src/phaseN_*.py`
- [ ] Check test file exists: `tests/test_phaseN_*.py`

### During Implementation
- [ ] Write tests first (TDD recommended)
- [ ] Implement the component
- [ ] Apply all guardrails for that phase
- [ ] All tests pass: `pytest tests/test_phaseN_* -v`
- [ ] Check coverage: `pytest tests/test_phaseN_* --cov=src.phaseN --cov-report=term`
- [ ] No regressions: `pytest tests/ -q` (all 141+ tests pass)

### When Done
- [ ] Update section below with phase status
- [ ] Update imports in next phase if needed
- [ ] Commit with message: "Phase N: [component name]"

---

## Current Status

**Total Tests**: 289 passing ✅ (103 core + 38 Phase 1 + 52 Phase 2 + 22 Phase 3 + 39 Phase 4 + 35 Phase 5)

| Phase | Component | Status | Tests |
|-------|-----------|--------|-------|
| ✅ 1 | Knowledge Base | Complete | 38 ✅ |
| ✅ 2 | Intent Resolver | Complete | 52 ✅ |
| ✅ 3 | Matcher-Explainer | Complete | 22 ✅ |
| ✅ 4 | Playlist Agent | Complete | 39 ✅ |
| ✅ 5 | Interactive CLI | Complete | 35 ✅ |

---

## Key Concepts

**RAG** (Retrieval-Augmented Generation): Phase 1 (KB) + Phase 3 (retrieval + context in explanations)

**Agentic Workflow**: Phase 4 (plan → act → validate → adjust loop)

**Natural Language**: Phase 2 (parse user requests) + Phase 5 (multi-turn memory)

**Core GMEWS** (unchanged): `src/recommender.py` with 4 scoring modes

---

## Imports Template

```python
# Standard
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Phase 1 (Knowledge Base)
from src.phase1_knowledge_base import KnowledgeBase, ArtistProfile, GenreKnowledge

# Core recommender
from src.recommender import load_songs, recommend_songs, SCORING_MODES

# Guardrails
from src.guardrails import validate_song_metadata, validate_user_input, ...
```

---

## Common Tasks

### Run Phase 1 tests only
```bash
pytest tests/test_phase1_knowledge_base.py -v
```

### Run all tests with coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Test a single function
```bash
pytest tests/test_phaseN_*.py::TestClassName::test_function_name -v
```

### Check what changed
```bash
git status
git diff src/phaseN_*.py
```

---

## Project Complete ✅

All 5 phases implemented with comprehensive tests covering method interactions and workflows:

- **Phase 1** (Knowledge Base): Song indexing + RAG retrieval (38 tests)
- **Phase 2** (Intent Resolver): NLP parsing + preference extraction (52 tests)
- **Phase 3** (Matcher-Explainer): GMEWS scoring + RAG-enhanced explanations (22 tests)
- **Phase 4** (Playlist Agent): Agentic loop with validation/adjustment (39 tests)
- **Phase 5** (Interactive CLI): Single-query and multi-turn modes with rate limiting (35 tests)

**Next steps**: Deploy, test with real users, refine based on feedback.

---

## Questions?

- **Project history**: `Music_Recommender_Conversation_Context.md`
- **Detailed safety**: `GUARDRAILS.md`
- **Existing tests**: `tests/test_recommender.py` (patterns to follow)
- **Core algorithm**: `src/recommender.py` (don't modify)

---

**Last Updated**: 2026-07-29  
**Ready**: All 5 phases complete, 289 tests passing
