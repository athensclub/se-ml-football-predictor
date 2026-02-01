#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pandas", "rapidfuzz", "pyarrow"]
# ///
"""Extract starting XIs from StatsBomb and produce mapping candidates to FIFA players.

Outputs:
- data/cache/matches_starting_players.parquet (long format)
- data/mappings/player_map_review.csv
- data/mappings/player_map.csv (auto-accepted mappings)
"""
from pathlib import Path
import json
import pandas as pd
from rapidfuzz import process, fuzz
import unicodedata

ROOT = Path("data") / "statsbom-opendata" / "data"
OUT = Path("data") / "cache"
MAPDIR = Path("data") / "mappings"
OUT.mkdir(parents=True, exist_ok=True)
MAPDIR.mkdir(parents=True, exist_ok=True)

LINEUPS = ROOT / "lineups"

FIFA_PARQ = Path("data") / "cache" / "fifa_players.parquet"
MATCHES_PARQ = Path("data") / "cache" / "matches.parquet"

# thresholds
AUTO_ACCEPT = 90
REVIEW_LOW = 70


def normalize_name(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join([c for c in s if not unicodedata.combining(c)])
    s = s.replace("'", "").replace("\"", "").replace('.', '')
    s = ' '.join(s.split())
    return s


def extract_starting_players(match_id: int):
    p = LINEUPS / f"{match_id}.json"
    if not p.exists():
        return []
    with p.open('r', encoding='utf-8') as f:
        data = json.load(f)
    out = []
    # data is a list of team objects
    for team in data:
        team_id = team.get('team_id')
        team_name = team.get('team_name')
        for pl in team.get('lineup', []):
            player_id = pl.get('player_id')
            player_name = pl.get('player_name')
            jersey = pl.get('jersey_number')
            # player country if available
            country_name = None
            if pl.get('country') and isinstance(pl.get('country'), dict):
                country_name = pl.get('country').get('name')
            # find position entry with start_reason containing 'Starting'
            positions = pl.get('positions', [])
            start_positions = [pos for pos in positions if pos.get('start_reason') and 'Starting' in pos.get('start_reason')]
            if start_positions:
                pos = start_positions[0]
                position = pos.get('position')
                position_id = pos.get('position_id')
                is_start = True
            else:
                # skip non-starting players
                continue
            out.append({
                'match_id': match_id,
                'team_id': team_id,
                'team_name': team_name,
                'player_id_sb': player_id,
                'player_name_sb': player_name,
                'jersey': jersey,
                'position': position,
                'position_id': position_id,
                'player_country': country_name,
            })
    return out


def build_fifa_lookup():
    # Support both parquet and csv fallback
    if FIFA_PARQ.exists():
        df = pd.read_parquet(FIFA_PARQ)
    else:
        csvp = FIFA_PARQ.with_suffix('.csv')
        if csvp.exists():
            df = pd.read_csv(csvp)
        else:
            raise FileNotFoundError("FIFA players cache not found. Run scripts/ingest_fifa.py first.")
    # create a combined name field
    df['name_candidates'] = df.get('short_name', '').fillna('') + ' || ' + df.get('long_name', '').fillna('')
    # use list comprehension for faster normalized mapping
    df['normalized'] = [normalize_name(x) for x in df['name_candidates'].fillna('')]
    # We'll store mapping of normalized name -> sofifa_id and original name
    if 'sofifa_id' in df.columns:
        lookup = df[['sofifa_id','short_name','long_name']].copy()
    else:
        lookup = df[['short_name','long_name']].copy()
        lookup['sofifa_id'] = lookup.index.astype(str)
    lookup['normalized'] = df['normalized']
    # build normalized -> row mapping for fast exact lookup
    norm_map = {row['normalized']: (row.get('sofifa_id'), row.get('short_name')) for _, row in lookup.iterrows()}
    return df, lookup, norm_map


def match_player_name(name: str, fifa_df, fifa_lookup, fifa_norm_map):
    n = normalize_name(name)
    # exact match using dict lookup (fast)
    if n in fifa_norm_map:
        sofifa, short_name = fifa_norm_map[n]
        return sofifa, short_name, 100, 'exact'
    # For speed in the first pass, we only do exact normalized matches.
    # Fuzzy matching will be added later with careful narrowing.
    return None, None, 0, 'no-fuzzy'


def main():
    # load matches
    # load matches (parquet or csv fallback)
    if MATCHES_PARQ.exists():
        matches = pd.read_parquet(MATCHES_PARQ)
    else:
        csvp = MATCHES_PARQ.with_suffix('.csv')
        if csvp.exists():
            matches = pd.read_csv(csvp)
        else:
            raise FileNotFoundError('matches cache not found. Run scripts/ingest_statsbomb.py first')
    print(f"Loaded {len(matches)} matches")
    rows = []
    match_ids = matches['match_id'].dropna().astype(int).unique().tolist()
    for mid in match_ids:
        players = extract_starting_players(int(mid))
        for p in players:
            rows.append(p)
    players_df = pd.DataFrame(rows)
    out_players = OUT / 'matches_starting_players.parquet'
    try:
        players_df.to_parquet(out_players, index=False)
        print('Wrote starting players:', out_players)
    except Exception as e:
        out_csv = OUT / 'matches_starting_players.csv'
        players_df.to_csv(out_csv, index=False)
        print('Parquet write failed (fallback to CSV). Wrote starting players to', out_csv)
        print('Error was:', e)

    # build unique sb players
    if players_df.empty:
        print('No starting players found, exiting')
        return
    unique_players = players_df[['player_id_sb','player_name_sb']].drop_duplicates().reset_index(drop=True)

    # Build a fast normalized map only for StatsBomb player names (avoid scanning full FIFA unnecessarily)
    sb_norms = set(unique_players['player_name_sb'].apply(normalize_name).tolist())
    fifa_norm_map = {}
    # try to load fifa CSV (fallback if parquet not available); use chunked read to avoid heavy memory/CPU
    if FIFA_PARQ.exists():
        fifa_df_full = pd.read_parquet(FIFA_PARQ)
        name_candidates = (fifa_df_full.get('short_name', '').fillna('') + ' || ' + fifa_df_full.get('long_name', '').fillna('')).astype(str).tolist()
        norms = [normalize_name(x) for x in name_candidates]
        for i, norm in enumerate(norms):
            if norm in sb_norms and norm not in fifa_norm_map:
                row = fifa_df_full.iloc[i]
                sofifa_id = row.get('sofifa_id') if 'sofifa_id' in row.index else str(i)
                fifa_norm_map[norm] = (sofifa_id, row.get('short_name'))
    else:
        csvp = FIFA_PARQ.with_suffix('.csv')
        if not csvp.exists():
            raise FileNotFoundError('FIFA CSV not found. Run scripts/ingest_fifa.py first')
        # read first chunk only as a fast initial pass (you can re-run later for full coverage)
        reader = pd.read_csv(csvp, chunksize=2000)
        try:
            chunk = next(reader)
        except StopIteration:
            chunk = None
        if chunk is not None:
            name_candidates = (chunk.get('short_name', '').fillna('') + ' || ' + chunk.get('long_name', '').fillna('')).astype(str).tolist()
            norms = [normalize_name(x) for x in name_candidates]
            for i, norm in enumerate(norms):
                if norm in sb_norms and norm not in fifa_norm_map:
                    row = chunk.iloc[i]
                    sofifa_id = row.get('sofifa_id') if 'sofifa_id' in row.index else None
                    fifa_norm_map[norm] = (sofifa_id, row.get('short_name'))
        # Note: This is an initial pass for speed. Run a full pass later if you want higher coverage.

    # Build token index for the subset of FIFA names relevant to SB names (quick fuzzy)
    # Use the norms list we computed above if available
    fifa_norms = globals().get('norms', [])
    fifa_shortnames = []
    fifa_sofifa = []
    fifa_lookup = None
    if 'fifa_df_full' in globals():
        fifa_shortnames = list(fifa_df_full.get('short_name', '').fillna('').astype(str).tolist())
        fifa_sofifa = list(fifa_df_full.get('sofifa_id', [None] * len(fifa_shortnames)))
        fifa_lookup = fifa_df_full[['sofifa_id', 'short_name']].copy() if 'sofifa_id' in fifa_df_full.columns else fifa_df_full[['short_name']].copy()
    elif 'chunk' in globals() and chunk is not None:
        fifa_shortnames = list(chunk.get('short_name', '').fillna('').astype(str).tolist())
        fifa_sofifa = list(chunk.get('sofifa_id', [None] * len(fifa_shortnames)))
        fifa_lookup = chunk[['sofifa_id', 'short_name']].copy() if 'sofifa_id' in chunk.columns else chunk[['short_name']].copy()

    # tokens present in SB names
    sb_tokens = set()
    for name in unique_players['player_name_sb'].astype(str):
        for t in normalize_name(name).split():
            if len(t) > 1:
                sb_tokens.add(t)
    token_index = {}
    for idx, val in enumerate(fifa_norms):
        toks = [t for t in val.split() if len(t) > 1]
        for t in toks:
            if t in sb_tokens:
                token_index.setdefault(t, []).append(idx)

    review_rows = []
    accepted = []
    for _, r in unique_players.iterrows():
        sbid = r['player_id_sb']
        sbname = r['player_name_sb']
        sbcountry = r.get('player_country') if 'player_country' in r.index else None
        sofifa, cand_name, score, method = match_player_name(sbname, None, None, fifa_norm_map)
        status = 'unmatched'
        if score >= AUTO_ACCEPT:
            status = 'accepted'
            accepted.append({'player_id_sb': sbid, 'player_name_sb': sbname, 'sofifa_id': sofifa, 'score': score, 'method': method})
        else:
            # quick fuzzy: only when exact miss
            n = normalize_name(sbname)
            tokens = [t for t in n.split() if len(t) > 1]
            candidate_idxs = set()
            for t in tokens:
                candidate_idxs.update(token_index.get(t, []))
            # limit search size
            if candidate_idxs and len(candidate_idxs) <= 1000:
                choices = [fifa_norms[i] for i in candidate_idxs]
                res = process.extractOne(n, choices, scorer=fuzz.token_sort_ratio)
                if res:
                    best_match, sscore, local_idx = res
                    # convert local_idx in choices -> global idx
                    # find global index by searching first occurrence
                    # fallback to scanning candidate_idxs
                    global_idx = None
                    for i in candidate_idxs:
                        if fifa_norms[i] == best_match:
                            global_idx = i
                            break
                    if global_idx is not None:
                        row = fifa_lookup.iloc[global_idx]
                        sofifa2 = row.get('sofifa_id') if 'sofifa_id' in row.index else None
                        cand_name2 = row.get('short_name')
                        if sscore >= 85:
                            status = 'accepted_fuzzy'
                            accepted.append({'player_id_sb': sbid, 'player_name_sb': sbname, 'sofifa_id': sofifa2, 'score': int(sscore), 'method': 'fuzzy'})
                        elif sscore >= 75:
                            status = 'review'
                            sofifa = sofifa2
                            cand_name = cand_name2
                            score = int(sscore)
            # end fuzzy
        review_rows.append({
            'player_id_sb': sbid,
            'player_name_sb': sbname,
            'candidate_sofifa_id': sofifa,
            'candidate_name': cand_name,
            'score': score,
            'method': method,
            'status': status
        })

    review_df = pd.DataFrame(review_rows)
    review_path = MAPDIR / 'player_map_review.csv'
    review_df.to_csv(review_path, index=False)
    print('Wrote review CSV:', review_path)

    accepted_df = pd.DataFrame(accepted)
    map_path = MAPDIR / 'player_map.csv'
    accepted_df.to_csv(map_path, index=False)
    print('Wrote accepted mappings:', map_path)


if __name__ == '__main__':
    main()
