#!/usr/bin/env python3
"""Quick inspect of FIFA players parquet columns"""
# /// script
# dependencies = ["pandas", "pyarrow"]
# ///
import pandas as pd
p = 'data/cache/fifa_players.parquet'
df = pd.read_parquet(p)
print('Rows:', len(df))
print('Columns:', list(df.columns))
print('Sample head:')
print(df.head(3).to_dict(orient='records'))
