#!/usr/bin/env python3
"""Check player mapping statistics."""
# /// script
# dependencies = ["pandas", "pyarrow"]
# ///

import pandas as pd
from pathlib import Path

# Load data
player_map = pd.read_csv("data/mappings/player_map.csv")
player_map_review = pd.read_csv("data/mappings/player_map_review.csv")
starting_players = pd.read_parquet("data/cache/matches_starting_players.parquet")

print("\n=== Player Mapping Coverage ===")
print(f"Auto-accepted mappings (≥85 score): {len(player_map)}")
print(f"Review needed (75-84 score): {len(player_map_review)}")
print(f"Total unique StatsBomb players: {starting_players['player_name_sb'].nunique()}")
matched_appearances = starting_players['player_id_sb'].isin(player_map['player_id_sb']).sum()
print(f"\nPlayer appearances matched (using `player_id_sb` in accepted map): {matched_appearances} / {len(starting_players)} ({matched_appearances/len(starting_players)*100:.1f}%)")

if len(player_map) > 0:
    print(f"\nSample auto-accepted mappings:")
    print(player_map.head(10)[["player_name_sb", "fifa_id", "score"]])
    
if len(player_map_review) > 0:
    print(f"\nSample review-needed mappings:")
    print(player_map_review.head(10)[["player_name_sb", "candidate_fifa_id", "candidate_name", "score", "status"]])
