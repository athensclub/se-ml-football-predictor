# TODO — Starting‑XI Match Predictor

Short: Prioritized, actionable todo list and milestones for the project (LightGBM first, Big‑5 leagues, single human reviewer for mapping).

---

## Milestones (priority order)

1. Data ingestion & basic mapping ✅
   - Scripts: `scripts/ingest_statsbomb.py`, `scripts/ingest_fifa.py`, `scripts/match_players.py`
   - Outcome: `data/cache/matches_with_starting_xi.parquet` and `data/mappings/player_map_review.csv`
   - Acceptance: Able to produce a merged table with starting XI and FIFA attribute candidates for ≥80% of players in Big‑5 matches.

2. Baseline features & LightGBM model ⚡
   - Scripts: `scripts/featurize.py`, `scripts/train_lightgbm.py`, `scripts/evaluate.py`
   - Outcome: `models/lightgbm_baseline/` (model + scaler + metrics report)
   - Acceptance: Beats home‑only prior on logloss on holdout season; outputs per-match probabilities and SHAP explainability plots.

3. Mapping review & iterative improvement 🧭
   - Script/Tooling: CSV export `data/mappings/player_map_review.csv`, CLI helper `scripts/review_mapping.py` to accept/reject mapping candidates and write `data/mappings/player_map.csv`
   - Outcome: Reduce ambiguous mappings to <10% for Big‑5.
   - Acceptance: Manual review UX works for single reviewer and is lightweight (review file rows < 1k per run).

4. Advanced features & set model (optional later) 🧠
   - Scripts: `scripts/train_set_model.py` (DeepSets / Set Transformer)
   - Outcome: `models/set_model/` and comparison report vs LightGBM
   - Acceptance: Improved logloss and calibration vs baseline OR valuable qualitative insights.

5. Inference + API 🚀
   - Scripts: `scripts/infer.py`, `api/fastapi_app.py`
   - Outcome: Single-match inference under 2s (CPU), endpoint to accept two starting XIs and return probabilities.
   - Acceptance: End-to-end flow (user input → mapping → prediction) works and latency < 2s on dev machine.

---

## Task breakdown (first sprint)

### A. Data ingestion (3–8 hours)
- [ ] `scripts/ingest_statsbomb.py` - read StatsBomb JSONs, filter Big‑5 leagues, output canonical matches table (match_id, date, home_team, away_team, home_score, away_score, season, competition_name)
- [ ] `scripts/ingest_fifa.py` - read FIFA CSV(s), select columns (`player_id, short_name, long_name, positions, overall, pace, shooting, passing, dribbling, defending, physic, age, nationality`), output `data/cache/fifa_players.parquet`
- [ ] Test: run and confirm file counts and sample rows

### B. Player mapping (4–16 hours)
- [ ] `scripts/match_players.py` - implement deterministic normalize + rapidfuzz matching to produce `player_map_review.csv` with candidate scores
- [ ] Thresholds: auto-accept score ≥ 90; flag 70–90 for review; <70 unmatched
- [ ] Log unmatched counts and produce `data/mappings/player_map_stats.json`

Notes on human-in-the-loop: you are the sole reviewer. Keep the review CSV small by auto-accepting high confidence matches and showing only ambiguous candidates.

### C. Featurization (4–12 hours)
- [ ] `scripts/featurize.py` - given matches + mapping + FIFA attributes, produce features:
  - per-team aggregations: mean/std/sum/max of selected attributes
  - role pools (GK/DEF/MID/FWD) aggregations
  - derived features: team_overall_diff, attack_score, defense_score, avg_age, home_flag
  - output `data/cache/features.parquet`
- [ ] Test: sanity-check correlation and value ranges

### D. LightGBM baseline (4–12 hours)
- [ ] `scripts/train_lightgbm.py` - load features, create time-aware train/val/test (e.g., train before 2022-23, val 2022-23), train LightGBM with logloss multiclass
- [ ] `scripts/evaluate.py` - metrics: logloss, macro-F1, Brier, calibration
- [ ] Save model artifacts under `models/lightgbm_baseline/`

### E. Minimal `scripts/infer.py` (2–6 hours)
- [ ] Single-match inference: accepts lists of FIFA player ids / names and returns probabilities
- [ ] Use mapping step; if player missing, use positional mean

---

## Reproducibility & tooling
- Use `uv` for script execution (scripts contain inline metadata when needed). Example: `uv run scripts/train_lightgbm.py` to run with dependencies installed.
- Use Parquet caches in `data/cache/` to speed iteration.
- Lock dependencies with `uv lock --script scripts/<script>.py` for reproducibility.

## Minimal acceptance tests
- `tests/test_ingest.py` reads small sample StatsBomb file and checks starting-xi extraction.
- `tests/test_mapping.py` ensures normalized exact matches succeed; ambiguous name returns candidate list.
- `tests/test_infer.py` runs `scripts/infer.py` on one historic match and returns a probability distribution that sums to 1

---

## Notes & constraints
- Seasons: include matches up until the last season where a comfortable majority of players map to FIFA snapshot. Implement a coverage check function to pick final cutoff season.
- Human review: keep manual reviews minimal — prefer thresholds that auto-accept most matches and only surface problematic cases.
- No local GPU: baseline LightGBM trains fast on CPU. Advanced deep models can be run on Modal or other GPU services if needed.

---

## Next immediate action (pick one)
- (A) I draft skeleton scripts and add them to `scripts/` (no full implementation), or
- (B) I implement ingestion + mapping and produce the first `data/cache/matches_with_starting_xi.parquet` and `player_map_review.csv`.

Reply which you want me to start with.