#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pandas", "pyarrow"]
# ///
"""Ingest StatsBomb open-data for Big-5 competitions and write a canonical matches table.

Output:
- data/cache/matches.parquet
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path("data") / "statsbom-opendata" / "data"
OUT = Path("data") / "cache"
OUT.mkdir(parents=True, exist_ok=True)

BIG5_KEYWORDS = ["Premier", "Premier League", "La Liga", "LaLiga", "Serie A", "Bundesliga", "1. Bundesliga", "Ligue 1"]
BIG5_COUNTRIES = ["England", "Spain", "Italy", "Germany", "France"]


def load_competitions():
    p = ROOT / "competitions.json"
    with p.open("r", encoding="utf-8") as f:
        comps = json.load(f)
    df = pd.DataFrame(comps)
    return df


def select_big5_competition_ids(comps: pd.DataFrame):
    mask = comps["country_name"].isin(BIG5_COUNTRIES)
    # also include by competition_name keywords
    for kw in BIG5_KEYWORDS:
        mask = mask | comps["competition_name"].str.contains(kw, case=False, na=False)
    # filter male senior competitions only
    mask = mask & (comps["competition_gender"] == "male") & (comps["competition_youth"] == False) & (comps["competition_international"] == False)
    selected = comps[mask]
    return selected


def read_matches_for_competition(comp_id: int):
    folder = ROOT / "matches" / str(comp_id)
    if not folder.exists():
        return []
    out = []
    for file in folder.glob("*.json"):
        with file.open("r", encoding="utf-8") as f:
            m = json.load(f)
        # Some files contain a list of matches
        entries = m if isinstance(m, list) else [m]
        for entry in entries:
            out.append({
                "match_id": entry.get("match_id"),
                "competition_id": entry.get("competition_id"),
                "season_name": entry.get("season_name"),
                "match_date": entry.get("match_date"),
                "home_team_id": entry.get("home_team" , {}).get("home_team_id") if isinstance(entry.get("home_team"), dict) else entry.get("home_team"),
                "home_team_name": entry.get("home_team", {}).get("home_team_name") if isinstance(entry.get("home_team"), dict) else None,
                "away_team_id": entry.get("away_team", {}).get("away_team_id") if isinstance(entry.get("away_team"), dict) else entry.get("away_team"),
                "away_team_name": entry.get("away_team", {}).get("away_team_name") if isinstance(entry.get("away_team"), dict) else None,
                "home_score": entry.get("home_score"),
                "away_score": entry.get("away_score"),
            })
    return out


def main():
    comps = load_competitions()
    selected = select_big5_competition_ids(comps)
    comp_ids = selected["competition_id"].unique().tolist()
    print("Selected competition ids:", comp_ids)

    all_matches = []
    for cid in comp_ids:
        ms = read_matches_for_competition(cid)
        all_matches.extend(ms)

    df = pd.DataFrame(all_matches)
    out_path = OUT / "matches.parquet"
    try:
        df.to_parquet(out_path, index=False)
        print("Wrote matches to", out_path)
    except Exception as e:
        # Fallback to CSV if parquet engine is missing in this environment
        out_csv = OUT / "matches.csv"
        df.to_csv(out_csv, index=False)
        print("Parquet write failed (fallback to CSV). Wrote matches to", out_csv)
        print("Error was:", e)


if __name__ == '__main__':
    main()
