#!/usr/bin/env python3
"""Run a more exhaustive fuzzy matching pass over the full FIFA parquet.

This script:
- Loads `data/mappings/player_map_review.csv` and `data/mappings/player_map.csv`
- For rows with status in ['unmatched','review'] attempts to find matches using full FIFA names
- Uses token-based blocking and allows larger candidate sets, tries multiple scorers
- Updates review CSV statuses and appends any new accepted mappings to player_map.csv

Usage: uv run scripts/match_players_fullfuzzy.py
"""
# /// script
# requires-python = ">=3.12"
# dependencies = ["pandas", "rapidfuzz", "pyarrow"]
# ///

from pathlib import Path
import pandas as pd
from rapidfuzz import process, fuzz
import unicodedata

ROOT = Path('data')
FIFA_PARQ = ROOT / 'cache' / 'fifa_players.parquet'
MAPDIR = ROOT / 'mappings'
REVIEW_P = MAPDIR / 'player_map_review.csv'
ACCEPT_P = MAPDIR / 'player_map.csv'

# thresholds and caps
AUTO_ACCEPT_SCORE = 85  # keep same as quick pass
REVIEW_LOW = 75
MAX_TOKEN_CANDIDATES = 5000  # allow larger candidate pools
MAX_TOTAL_CANDIDATES = 5000
COMMON_TOKEN_SKIP = 100000  # skip tokens present in more than this many fifa names


def normalize_name(s: str) -> str:
    if not isinstance(s, str):
        return ''
    s = s.lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join([c for c in s if not unicodedata.combining(c)])
    s = s.replace("'", "").replace('"', '').replace('.', '')
    s = ' '.join(s.split())
    return s


def build_fifa_index():
    if not FIFA_PARQ.exists():
        raise FileNotFoundError('FIFA parquet not found; run ingest_fifa.py first')
    df = pd.read_parquet(FIFA_PARQ)
    name_candidates = (df.get('short_name', '').fillna('') + ' || ' + df.get('long_name', '').fillna('')).astype(str).tolist()
    norms = [normalize_name(x) for x in name_candidates]
    # build lookup frame with stable fifa_id
    if 'sofifa_id' in df.columns:
        lookup = df[['sofifa_id', 'short_name']].copy().rename(columns={'sofifa_id': 'fifa_id'})
    else:
        lookup = df[['short_name']].copy()
        lookup['fifa_id'] = lookup.index.astype(str)
    # attach normalized
    lookup['normalized'] = norms
    # build token index (token -> list of indices)
    token_index = {}
    for idx, norm in enumerate(norms):
        toks = [t for t in norm.split() if len(t) > 1]
        for t in toks:
            token_index.setdefault(t, []).append(idx)
    return lookup, norms, token_index


def run_full_pass():
    print('Loading review and accepted mapping files...')
    review = pd.read_csv(REVIEW_P)
    # ensure writable object dtypes for fields we'll update
    if 'candidate_fifa_id' in review.columns:
        review['candidate_fifa_id'] = review['candidate_fifa_id'].astype(object)
    else:
        review['candidate_fifa_id'] = pd.Series([pd.NA] * len(review), dtype=object)
    if 'candidate_name' not in review.columns:
        review['candidate_name'] = pd.Series([pd.NA] * len(review), dtype=object)
    if 'score' not in review.columns:
        review['score'] = pd.Series([pd.NA] * len(review), dtype='Int64')
    else:
        # make score nullable integer type
        review['score'] = review['score'].where(pd.notnull(review['score']), pd.NA).astype('Int64')

    try:
        accepted = pd.read_csv(ACCEPT_P)
    except Exception:
        accepted = pd.DataFrame(columns=['player_id_sb', 'player_name_sb', 'fifa_id', 'score', 'method'])

    lookup, fifa_norms, token_index = build_fifa_index()
    print('FIFA names:', len(fifa_norms))
    print('Review rows:', len(review))

    # process rows that need work
    to_process = review['status'].isin(['unmatched', 'review'])
    processed = 0
    new_accepted = []

    for idx, row in review.loc[to_process].iterrows():
        processed += 1
        sbname = row['player_name_sb']
        n = normalize_name(sbname)
        tokens = [t for t in n.split() if len(t) > 1]
        # collect candidate sets but ignore overly common tokens
        token_sets = []
        for t in tokens:
            idxs = token_index.get(t, [])
            if len(idxs) > COMMON_TOKEN_SKIP:
                continue
            token_sets.append(set(idxs))
        candidate_idxs = set()
        if token_sets:
            # intersect high-signal tokens, else union
            if len(token_sets) > 1:
                candidate_idxs = set.intersection(*token_sets)
            else:
                candidate_idxs = token_sets[0]
        else:
            # fallback: union from least-common tokens
            sorted_tokens = sorted(tokens, key=lambda x: len(token_index.get(x, [])))
            for t in sorted_tokens:
                candidate_idxs.update(token_index.get(t, []))
                if len(candidate_idxs) >= MAX_TOTAL_CANDIDATES:
                    break

        if not candidate_idxs:
            # as a last resort, search across all fifa_norms but skip (very slow)
            # We avoid full scan to keep this operational on CPU machines
            continue

        # cap candidate list
        if len(candidate_idxs) > MAX_TOTAL_CANDIDATES:
            candidate_list = list(candidate_idxs)[:MAX_TOTAL_CANDIDATES]
        else:
            candidate_list = list(candidate_idxs)

        choices = [fifa_norms[i] for i in candidate_list]
        # try token_sort_ratio first, then token_set_ratio as fallback
        res = process.extractOne(n, choices, scorer=fuzz.token_sort_ratio, score_cutoff=REVIEW_LOW)
        best = res
        if not res:
            res2 = process.extractOne(n, choices, scorer=fuzz.token_set_ratio, score_cutoff=REVIEW_LOW)
            best = res2
        if best:
            best_match, sscore, local_idx = best
            global_idx = candidate_list[local_idx] if isinstance(local_idx, int) else None
            if global_idx is None:
                # scan for match
                for i in candidate_list:
                    if fifa_norms[i] == best_match:
                        global_idx = i
                        break
            if global_idx is not None:
                lrow = lookup.iloc[global_idx]
                fid = lrow.get('fifa_id')
                # accept or mark review
                if sscore >= AUTO_ACCEPT_SCORE:
                    new_accepted.append({'player_id_sb': row['player_id_sb'], 'player_name_sb': sbname, 'fifa_id': fid, 'score': int(sscore), 'method': 'full_fuzzy'})
                    review.at[idx, 'candidate_fifa_id'] = fid
                    review.at[idx, 'candidate_name'] = lrow.get('short_name')
                    review.at[idx, 'score'] = int(sscore)
                    review.at[idx, 'status'] = 'accepted_fuzzy'
                else:
                    review.at[idx, 'candidate_fifa_id'] = fid
                    review.at[idx, 'candidate_name'] = lrow.get('short_name')
                    review.at[idx, 'score'] = int(sscore)
                    review.at[idx, 'status'] = 'review'
        # progress log
        if processed % 500 == 0:
            print(f'Processed {processed} rows... new accepted so far: {len(new_accepted)}')

    # append new accepted rows to accepted DataFrame
    if new_accepted:
        new_df = pd.DataFrame(new_accepted)
        accepted = pd.concat([accepted, new_df], ignore_index=True)
        accepted.to_csv(ACCEPT_P, index=False)
        print(f'Appended {len(new_accepted)} new accepted mappings to {ACCEPT_P}')

    # write back review file
    review.to_csv(REVIEW_P, index=False)
    print('Updated review CSV written.')
    print('Done.')


if __name__ == '__main__':
    run_full_pass()
