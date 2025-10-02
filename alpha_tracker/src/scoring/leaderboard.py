import pandas as pd

def write_leaderboard_to_db(conn, df: pd.DataFrame):
    df.to_sql('leaderboard', conn, if_exists='replace', index=False)
