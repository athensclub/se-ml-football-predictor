#!/usr/bin/env python3
"""Simulate match-level coverage when promoting review candidates at various score thresholds."""
# /// script
# dependencies = ["pandas", "pyarrow"]
# ///
import pandas as pd

sp = pd.read_parquet('data/cache/matches_starting_players.parquet')
accepted = pd.read_csv('data/mappings/player_map.csv', dtype={'player_id_sb': int, 'fifa_id': object})
review = pd.read_csv('data/mappings/player_map_review.csv', dtype={'player_id_sb': int, 'candidate_fifa_id': object, 'score': float})

# build accepted mapping set
accepted_map = dict(zip(accepted['player_id_sb'].astype(int), accepted['fifa_id']))

thresholds = [90,85,80,75,70,65,60]
results = []
for t in thresholds:
    # start with accepted
    mapping = accepted_map.copy()
    # take review rows with score >= t and candidate_fifa_id non-null
    cand = review.loc[review['score'].fillna(0) >= t]
    for _, r in cand.iterrows():
        if pd.notna(r['candidate_fifa_id']):
            mapping[int(r['player_id_sb'])] = r['candidate_fifa_id']
    # map onto starting players
    sp2 = sp.copy()
    sp2['fifa_id'] = sp2['player_id_sb'].map(mapping)
    # per team in match, check all players mapped
    team_ok = sp2.groupby(['match_id','team_id'])['fifa_id'].apply(lambda s: s.notna().all()).reset_index(name='all_mapped')
    both_teams = team_ok.groupby('match_id')['all_mapped'].all()
    count_both = both_teams.sum()
    pct = count_both / sp['match_id'].nunique() * 100
    results.append({'threshold': t, 'fully_matched_matches': int(count_both), 'pct': pct, 'added_mappings': len(set(cand['player_id_sb']) - set(accepted['player_id_sb']))})

print('Threshold, FullyMatched, Percent, NewMappingsAdded')
for r in results:
    print(f"{r['threshold']}, {r['fully_matched_matches']}, {r['pct']:.2f}%, {r['added_mappings']}")
