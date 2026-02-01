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
   - Current progress: implemented quick fuzzy, full fuzzy, and position-aware promotion passes. See `docs/todo.md` for live metrics.
   - Key metrics: **3,459 accepted mappings**, **4,474 review rows**, **467 matches fully-matched (19.1%)**, **89.0% appearances mapped**.
2. Model choice: start with LightGBM for speed and explainability; progress to DeepSets/Set Transformer if data supports it.  
3. Data split: use season-based time split and rolling validation to avoid leakage across seasons.

### Immediate mapping roadmap (recommended)
- Add **country/nationality-aware** promotions (high impact). 🌍
- Implement **team/context heuristics** (promote ambiguous players when teammates and positions match cleanly). 🤝
- Build a **small classifier** (features: fuzzy scores, position match, token overlap, country match, team-context count) to predict correct mappings and increase safe auto-accepts. 🧠
- Provide `scripts/review_mapping.py` CLI for a single human reviewer to quickly accept/reject remaining candidates (page-by-page UX).

---

### Questions for you
1. Prefer starting with LightGBM (fast & explainable) or directly with DeepSets (richer set modeling)?  
2. Do you have GPU resources?  
3. Confirm target leagues (Big-5 only) and seasons to include.

Would you like me to draft the concrete file checklist and the first issue/todo list (no code changes) next?