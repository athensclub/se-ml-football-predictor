#!/usr/bin/env python3
"""Check how many matches have all starting players mapped to FIFA ids."""
# /// script
# dependencies = ["pandas", "pyarrow"]
# ///
import pandas as pd

sp = pd.read_parquet('data/cache/matches_starting_players.parquet')
print('Rows:', len(sp))
print('Columns:', list(sp.columns))

# total match ids
match_ids = sp['match_id'].dropna().astype(int).unique()
print('Total matches:', len(match_ids))

# If fifa_id present, use it; otherwise map using player_map.csv
if 'fifa_id' in sp.columns:
    full_matches = sp.groupby('match_id')['fifa_id'].apply(lambda s: s.notna().all())
    count_full = full_matches.sum()
    print('Matches with all starting players having non-null fifa_id:', int(count_full))
else:
    pm = pd.read_csv('data/mappings/player_map.csv', dtype={'player_id_sb': int})
    pm_map = dict(zip(pm['player_id_sb'].astype(int), pm['fifa_id']))
    sp2 = sp.copy()
    sp2['fifa_id'] = sp2['player_id_sb'].map(pm_map)
    # consider fifa_id as non-null if value present and not nan
    full_matches = sp2.groupby('match_id')['fifa_id'].apply(lambda s: s.notna().all())
    count_full = full_matches.sum()
    print('Matches with all starting players mapped via player_map.csv:', int(count_full))
    # also compute per-team completeness
    teams_full = sp2.groupby(['match_id','team_id'])['fifa_id'].apply(lambda s: s.notna().all()).reset_index(name='all_matched')
    both_teams = teams_full.groupby('match_id')['all_matched'].all().sum()
    print('Matches where BOTH teams have all players matched:', int(both_teams))
    print('Percentage of matches fully matched:', float(both_teams) / len(match_ids) * 100)

# show sample match ids that are fully matched
fully = full_matches[full_matches==True].index.tolist()
print('Example fully matched match_ids (first 10):', fully[:10])
