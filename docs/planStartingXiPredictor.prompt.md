## Plan: Starting-XI Match Predictor

TL;DR — Build a probabilistic Home/Draw/Away predictor using StatsBomb (match + lineups) + FIFA23 player attributes. Steps: ingest & map players, produce permutation‑invariant team representations, train baselines (Elo, logistic, LightGBM), then advanced set models (DeepSets/Set Transformer), evaluate with time-aware splits, and expose a fast inference API.

### Steps
1. Ingest StatsBomb & FIFA files into `data/raw/` and cache Parquet in `data/cache/`.  
2. Implement mapping tool `scripts/match_players.py` and output `data/mappings/player_map.csv`.  
3. Create featurization `scripts/featurize.py` (per-player → role pools + set embeddings).  
4. Train baseline models `scripts/train_baseline.py` and advanced set models `scripts/train_set_model.py`.  
5. Evaluate with `scripts/evaluate.py` (time-split CV, logloss/Brier/macro-F1, calibration).  
6. Add inference `scripts/infer.py` + lightweight FastAPI endpoint for <2s predictions.

### Further Considerations
1. Mapping options: automatic (rapidfuzz) + manual CSV review — Recommend human-in-the-loop for ambiguous matches.  
2. Model choice: start with LightGBM for speed and explainability; progress to DeepSets/Set Transformer if data supports it.  
3. Data split: use season-based time split and rolling validation to avoid leakage across seasons.

---

### Questions for you
1. Prefer starting with LightGBM (fast & explainable) or directly with DeepSets (richer set modeling)?  
2. Do you have GPU resources?  
3. Confirm target leagues (Big-5 only) and seasons to include.

Would you like me to draft the concrete file checklist and the first issue/todo list (no code changes) next?