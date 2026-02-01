# Mapping Findings & Actions ✅

**TL;DR:** We implemented a multi-pass mapping pipeline (exact normalize → quick fuzzy → full fuzzy → position-aware pass) and increased player-coverage substantially. Current state: **3,459 accepted mappings**, **4,474 review rows**, **47,873 / 53,761 player appearances mapped (89.0%)**, and **467 matches fully mapped (19.1%)**. The 80% match-level target requires an additional country/context-aware pass or a small classifier.

---

## What I implemented (scripts) 🔧
- `scripts/match_players.py` — starting-XI extraction, normalization, initial exact + quick-fuzzy pass
- `scripts/match_players_fullfuzzy.py` — exhaustive fuzzy pass (token blocking, multi-scorer)
- `scripts/match_players_position_pass.py` — position-aware promotion pass (accept if SB position group matches FIFA player group)
- `scripts/simulate_threshold_coverage.py` — simulate match-level coverage under different score thresholds
- `scripts/check_matches_full_match.py` — compute matches where both teams are fully mapped
- `scripts/check_mapping_stats.py` — quick stats printing helper

All scripts are runnable via `uv run scripts/<script>.py` (they include inline dependency metadata).

---

## Key metrics (latest run) 📊
- Unique StatsBomb players: **4,472**
- Accepted mappings: **3,459** (`data/mappings/player_map.csv`)
- Review / ambiguous rows: **4,474** (`data/mappings/player_map_review.csv`)
- Player appearances mapped: **47,873 / 53,761 (89.0%)**
- Matches where BOTH teams are fully matched: **467 / 2,445 (19.1%)**

Simulation notes:
- Promoting review candidates at score ≥75 would increase fully-matched matches to **1,215 (49.7%)**; however that is riskier.
- Position-aware promotions increased fully-matched matches from ~0.37% → 19.1% (big win).

---

## What we tried & observed 🧭
- Exact normalized matching alone provided very low coverage (many names have diacritics/variants).
- Quick fuzzy (token narrowing) improved matches but was limited by candidate-sizes and token commonness.
- Full fuzzy (exhaustive but blocked) found many safe matches — added ~2,445 accepted mappings.
- Position-aware promotions added **905** more safe mappings by validating FIFA position groups.

Performance & scale notes:
- FIFA parquet has ~10M rows; building indices and tokenization is CPU & memory heavy. Token-blocking + caps kept runs practical on CPU.
- Some pandas dtype issues (nullable ints vs float columns) required careful dtype handling when writing review updates.

---

## Issues & edge cases encountered ⚠️
- Name variants: middle names, suffixes, diacritics, apostrophes, and reordered names cause lots of ambiguity.
- Token common tokens like "de", "da" or first names require skipping or de-prioritizing.
- Lack of nationality/country alignment reduces confidence for international names with common tokens.
- A few scripts initially referenced variables in the wrong scope and needed fixes (now committed).

---

## Recommendations / Next steps (prioritized) 📈
1. **Add nationality/country-aware promotions** — high-impact (match SB `player_country` to FIFA `nationality` / `country` before promoting). 🌍
2. **Team / context heuristics** — promote ambiguous players when teammates/positions show consistent mapping in the same match.
3. **Train a small classifier** to predict correct mapping (features: fuzzy score(s), position match, country match, token overlap, team-context counts). Use it to safely auto-accept with a precision target. 🧠
4. **Add `scripts/review_mapping.py`** — single-reviewer CLI (page-by-page) to accept/reject rows in `player_map_review.csv`.
5. **Document coverage per season and set a cutoff season** for training so model sees a consistent mapping snapshot.

Optional: If you want immediate >80% match-level coverage, use fallback fills per position (e.g., use position means) — but this will introduce synthetic approximations.

---

## Files added by this work
- `scripts/match_players_fullfuzzy.py`
- `scripts/match_players_position_pass.py`
- `scripts/simulate_threshold_coverage.py`
- `scripts/check_matches_full_match.py`
- `scripts/check_mapping_stats.py`

---

## Repro & commands 🧪
- Check stats: `uv run scripts/check_mapping_stats.py` 
- Run exhaustive fuzzy pass: `uv run scripts/match_players_fullfuzzy.py`
- Run position-aware promotions: `uv run scripts/match_players_position_pass.py`
- Re-simulate thresholds: `uv run scripts/simulate_threshold_coverage.py`
- Compute fully-mapped matches: `uv run scripts/check_matches_full_match.py`

---

If you'd like, I can:
- Add a `CHANGELOG.md` summarizing these steps and commit history, or
- Open a pull request with these docs + scripts changes and a short summary for reviewers.

---

Last updated: 2026-02-01
