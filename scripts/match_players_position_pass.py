#!/usr/bin/env python3
"""Position-aware pass to promote review candidates safely.

Rules:
- Promote review candidates (status in ['review','unmatched']) when:
  - `candidate_fifa_id` is present and a FIFA player exists
  - StatsBomb position group matches FIFA player position group
  - Score >= 75 (configurable)

- Writes updated `player_map.csv` (appending new accepted rows) and updates `player_map_review.csv` statuses
"""
# /// script
# dependencies = ["pandas", "pyarrow"]
# ///
from pathlib import Path
import pandas as pd

ROOT = Path('data')
MAPDIR = ROOT / 'mappings'
REVIEW_P = MAPDIR / 'player_map_review.csv'
ACCEPT_P = MAPDIR / 'player_map.csv'
SP_P = ROOT / 'cache' / 'matches_starting_players.parquet'
FIFA_PARQ = ROOT / 'cache' / 'fifa_players.parquet'

MIN_SCORE = 75


def pos_group_from_sb(pos: str) -> str:
    if not isinstance(pos, str):
        return 'UNK'
    p = pos.lower()
    if 'goal' in p or 'keeper' in p or p.startswith('g'):  # GK
        return 'GK'
    if any(k in p for k in ['back', 'defend', 'centre back', 'left back', 'right back', 'cb', 'rb', 'lb', 'lwb', 'rwb']):
        return 'DEF'
    if any(k in p for k in ['mid', 'centre', 'cm', 'dm', 'am', 'lm', 'rm']):
        return 'MID'
    if any(k in p for k in ['forward', 'att', 'st', 'cf', 'lw', 'rw', 'wing', 'fw']):
        return 'FWD'
    return 'UNK'


def pos_group_from_fifa(fifa_pos_str: str) -> str:
    if not isinstance(fifa_pos_str, str) or fifa_pos_str.strip() == '':
        return 'UNK'
    toks = [t.strip().lower() for t in fifa_pos_str.split(',')]
    for t in toks:
        if t in ['gk', 'goalkeeper']:
            return 'GK'
    for t in toks:
        if any(k in t for k in ['cb', 'rb', 'lb', 'lwb', 'rwb', 'back', 'def']):
            return 'DEF'
    for t in toks:
        if any(k in t for k in ['cm', 'cdm', 'cam', 'mid', 'central']):
            return 'MID'
    for t in toks:
        if any(k in t for k in ['st', 'cf', 'lw', 'rw', 'lf', 'rf', 'fw', 'att']):
            return 'FWD'
    return 'UNK'


def run_pass():
    review = pd.read_csv(REVIEW_P, dtype={'player_id_sb': int, 'candidate_fifa_id': object, 'score': float, 'status': object, 'candidate_name': object})
    try:
        accepted = pd.read_csv(ACCEPT_P, dtype={'player_id_sb': int, 'fifa_id': object, 'score': float})
    except Exception:
        accepted = pd.DataFrame(columns=['player_id_sb', 'player_name_sb', 'fifa_id', 'score', 'method'])

    sp = pd.read_parquet(SP_P)
    # map player_id_sb -> position from statsbomb (take first if multiple)
    pid_pos = sp.groupby('player_id_sb')['position'].first().to_dict()

    # load fifa players as lookup by fifa_id
    fifa = pd.read_parquet(FIFA_PARQ)
    # try to ensure fifa_id column exists; if not allocate index
    if 'sofifa_id' in fifa.columns:
        fifa = fifa.rename(columns={'sofifa_id': 'fifa_id'})
    if 'fifa_id' not in fifa.columns:
        fifa['fifa_id'] = fifa.index.astype(str)
    fifa_lookup = fifa.set_index('fifa_id')

    promoted = []
    for idx, r in review.iterrows():
        if r['status'] in ('accepted_fuzzy','accepted'):
            continue
        cand = r.get('candidate_fifa_id')
        score = r.get('score') if not pd.isna(r.get('score')) else 0
        if not pd.isna(cand) and score >= MIN_SCORE:
            cand_str = str(int(cand)) if isinstance(cand, (int, float)) and not pd.isna(cand) else str(cand)
            if cand_str in fifa_lookup.index:
                fifa_row = fifa_lookup.loc[cand_str]
                sb_pos = pid_pos.get(int(r['player_id_sb']), None)
                sb_group = pos_group_from_sb(sb_pos) if sb_pos else 'UNK'
                fifa_group = pos_group_from_fifa(fifa_row.get('player_positions', ''))
                # Accept if groups match (or if one is UNK and other present)
                if sb_group == fifa_group and sb_group != 'UNK':
                    # promote
                    review.at[idx, 'status'] = 'accepted_fuzzy_pos'
                    review.at[idx, 'candidate_fifa_id'] = cand_str
                    review.at[idx, 'candidate_name'] = fifa_row.get('short_name', '')
                    review.at[idx, 'score'] = int(score)
                    promoted.append({'player_id_sb': int(r['player_id_sb']), 'player_name_sb': r['player_name_sb'], 'fifa_id': cand_str, 'score': int(score), 'method': 'pos_fuzzy'})
                else:
                    # if sb_group is UNK but fifa_group known and score high, accept
                    if sb_group == 'UNK' and score >= 80:
                        review.at[idx, 'status'] = 'accepted_fuzzy_pos'
                        review.at[idx, 'candidate_fifa_id'] = cand_str
                        review.at[idx, 'candidate_name'] = fifa_row.get('short_name', '')
                        review.at[idx, 'score'] = int(score)
                        promoted.append({'player_id_sb': int(r['player_id_sb']), 'player_name_sb': r['player_name_sb'], 'fifa_id': cand_str, 'score': int(score), 'method': 'pos_fuzzy'})
                    # else leave as review
            else:
                # candidate id not in fifa lookup, skip
                continue

    # append promoted to accepted csv
    if promoted:
        promoted_df = pd.DataFrame(promoted)
        accepted = pd.concat([accepted, promoted_df], ignore_index=True)
        accepted.to_csv(ACCEPT_P, index=False)

    review.to_csv(REVIEW_P, index=False)
    print(f'Promoted {len(promoted)} mappings (position-aware).')

if __name__ == '__main__':
    run_pass()
