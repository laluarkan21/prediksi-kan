import pandas as pd

def feature_engineering_simplified(df, window_size=5):
    """
    Membuat fitur-fitur ringkas berdasarkan data historis.
    """
    team_stats, h2h_stats, features = {}, {}, []
    for index, row in df.iterrows():
        ht, at = row['HomeTeam'], row['AwayTeam']
        h2h_key = tuple(sorted((ht, at)))
        ht_stats_df, at_stats_df = team_stats.get(ht, pd.DataFrame()), team_stats.get(at, pd.DataFrame())
        match_h2h = h2h_stats.get(h2h_key, pd.DataFrame())
        
        if len(ht_stats_df) >= 1:
            last_5_ht = ht_stats_df.tail(window_size)
            avg_ht_gs = last_5_ht['goals_scored'].mean()
            avg_ht_gc = last_5_ht['goals_conceded'].mean()
            ht_wins = (last_5_ht['result'] == 'W').sum()
            ht_draws = (last_5_ht['result'] == 'D').sum()
            ht_losses = (last_5_ht['result'] == 'L').sum()
        else:
            avg_ht_gs, avg_ht_gc, ht_wins, ht_draws, ht_losses = 0, 0, 0, 0, 0

        if len(at_stats_df) >= 1:
            last_5_at = at_stats_df.tail(window_size)
            avg_at_gs = last_5_at['goals_scored'].mean()
            avg_at_gc = last_5_at['goals_conceded'].mean()
            at_wins = (last_5_at['result'] == 'W').sum()
            at_draws = (last_5_at['result'] == 'D').sum()
            at_losses = (last_5_at['result'] == 'L').sum()
        else:
            avg_at_gs, avg_at_gc, at_wins, at_draws, at_losses = 0, 0, 0, 0, 0
            
        h2h_ht_wins_rate = 0 if match_h2h.empty else (match_h2h['winner'] == ht).mean()

        features.append([
            avg_ht_gs, avg_ht_gc, ht_wins, ht_draws, ht_losses,
            avg_at_gs, avg_at_gc, at_wins, at_draws, at_losses,
            h2h_ht_wins_rate
        ])
        
        if row['FTR'] == 'H': ht_res, at_res, winner = 'W', 'L', ht
        elif row['FTR'] == 'A': ht_res, at_res, winner = 'L', 'W', at
        else: ht_res, at_res, winner = 'D', 'D', 'D'
        
        team_stats[ht] = pd.concat([ht_stats_df, pd.DataFrame([{'goals_scored': row['FTHG'], 'goals_conceded': row['FTAG'], 'result': ht_res}])]).reset_index(drop=True)
        team_stats[at] = pd.concat([at_stats_df, pd.DataFrame([{'goals_scored': row['FTAG'], 'goals_conceded': row['FTHG'], 'result': at_res}])]).reset_index(drop=True)
        h2h_stats[h2h_key] = pd.concat([match_h2h, pd.DataFrame([{'winner': winner}])]).reset_index(drop=True)

    feature_df = pd.DataFrame(features, columns=['Avg_HT_GS', 'Avg_HT_GC', 'HT_Wins', 'HT_Draws', 'HT_Losses', 'Avg_AT_GS', 'Avg_AT_GC', 'AT_Wins', 'AT_Draws', 'AT_Losses', 'H2H_HT_Win_Rate'])
    return pd.concat([df, feature_df], axis=1)