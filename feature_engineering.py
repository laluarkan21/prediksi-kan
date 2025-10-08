import pandas as pd

def feature_engineering_simplified(df, window_size=5):
    """
    Membuat fitur-fitur ringkas berdasarkan data historis.
    """
    team_stats, h2h_stats, features = {}, {}, []
    original_indices = []

    for index, row in df.iterrows():
        original_indices.append(index) # Simpan index asli untuk penggabungan nanti
        ht, at = row['HomeTeam'], row['AwayTeam']
        h2h_key = tuple(sorted((ht, at)))
        ht_stats_df = team_stats.get(ht, pd.DataFrame())
        at_stats_df = team_stats.get(at, pd.DataFrame())
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

    # PERBAIKAN FINAL: Buat DataFrame HANYA dari fitur baru, lalu gabungkan dengan aman.
    feature_df = pd.DataFrame(
        features, 
        index=original_indices, 
        columns=['Avg_HT_GS', 'Avg_HT_GC', 'HT_Wins', 'HT_Draws', 'HT_Losses', 'Avg_AT_GS', 'Avg_AT_GC', 'AT_Wins', 'AT_Draws', 'AT_Losses', 'H2H_HT_Win_Rate']
    )
    
    # Menggabungkan dataframe asli dengan dataframe fitur baru berdasarkan index
    return df.join(feature_df)

def create_features_and_labels(league_data):
    """
    Fungsi utama untuk menjalankan rekayasa fitur dan membuat label.
    """
    print("Memulai proses rekayasa fitur untuk semua liga...")
    processed_data = {}
    for liga_name, df in league_data.items():
        df_featured = feature_engineering_simplified(df.copy())
        
        # (Sisa kode di bawah ini tidak perlu diubah)
        if 'B365H' in df_featured.columns:
            df_featured['Prob_H'] = 1/df_featured['B365H'].replace(0,1e-6)
            df_featured['Prob_D'] = 1/df_featured['B365D'].replace(0,1e-6)
            df_featured['Prob_A'] = 1/df_featured['B365A'].replace(0,1e-6)
            total_prob = df_featured['Prob_H']+df_featured['Prob_D']+df_featured['Prob_A']
            df_featured['Norm_Prob_H'] = df_featured['Prob_H']/total_prob
            df_featured['Norm_Prob_D'] = df_featured['Prob_D']/total_prob
            df_featured['Norm_Prob_A'] = df_featured['Prob_A']/total_prob
        else:
            df_featured['Norm_Prob_H'], df_featured['Norm_Prob_D'], df_featured['Norm_Prob_A'] = 0, 0, 0
        
        over_col = 'Avg>2.5' if 'Avg>2.5' in df_featured.columns else 'BbAv>2.5'
        under_col = 'Avg<2.5' if 'Avg<2.5' in df_featured.columns else 'BbAv<2.5'

        if over_col in df_featured.columns and under_col in df_featured.columns:
            df_featured['Prob_Over'] = 1/df_featured[over_col].replace(0,1e-6)
            df_featured['Prob_Under'] = 1/df_featured[under_col].replace(0,1e-6)
            total_prob_ou = df_featured['Prob_Over']+df_featured['Prob_Under']
            df_featured['Norm_Prob_Over'] = df_featured['Prob_Over']/total_prob_ou
            df_featured['Norm_Prob_Under'] = df_featured['Prob_Under']/total_prob_ou
        else:
            df_featured['Norm_Prob_Over'], df_featured['Norm_Prob_Under'] = 0, 0
        
        df_featured['Over_2.5'] = ((df_featured['FTHG'] + df_featured['FTAG']) > 2.5).astype(int)
        df_featured['BTTS'] = ((df_featured['FTHG'] > 0) & (df_featured['FTAG'] > 0)).astype(int)
        
        df_featured.dropna(inplace=True)
        processed_data[liga_name] = df_featured
        print(f"  - Selesai memproses {df_featured.shape[0]} baris untuk liga '{liga_name}'.")

    return processed_data