import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib # BARU: Impor library untuk menyimpan model
import warnings
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

# --- Langkah 1, 2, & 3: Tidak ada perubahan ---
try:
    df = pd.read_csv('dataset/dataset_pertandingan.csv')
except FileNotFoundError:
    print("Error: File 'dataset/dataset_pertandingan.csv' tidak ditemukan.")
    exit()
numeric_cols = ['FTHG', 'FTAG', 'B365H', 'B365D', 'B365A', 'Avg>2.5', 'Avg<2.5']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
df.fillna(0, inplace=True)
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
df.dropna(subset=['Date'], inplace=True)
df = df.sort_values('Date').reset_index(drop=True)
print(f"Jumlah baris data awal: {df.shape[0]}")

def feature_engineering_simplified(df, window_size=5):
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
        features.append([avg_ht_gs, avg_ht_gc, ht_wins, ht_draws, ht_losses, avg_at_gs, avg_at_gc, at_wins, at_draws, at_losses, h2h_ht_wins_rate])
        if row['FTR'] == 'H': ht_res, at_res, winner = 'W', 'L', ht
        elif row['FTR'] == 'A': ht_res, at_res, winner = 'L', 'W', at
        else: ht_res, at_res, winner = 'D', 'D', 'D'
        team_stats[ht] = pd.concat([ht_stats_df, pd.DataFrame([{'goals_scored': row['FTHG'], 'goals_conceded': row['FTAG'], 'result': ht_res}])]).reset_index(drop=True)
        team_stats[at] = pd.concat([at_stats_df, pd.DataFrame([{'goals_scored': row['FTAG'], 'goals_conceded': row['FTHG'], 'result': at_res}])]).reset_index(drop=True)
        h2h_stats[h2h_key] = pd.concat([match_h2h, pd.DataFrame([{'winner': winner}])]).reset_index(drop=True)
    feature_df = pd.DataFrame(features, columns=['Avg_HT_GS', 'Avg_HT_GC', 'HT_Wins', 'HT_Draws', 'HT_Losses', 'Avg_AT_GS', 'Avg_AT_GC', 'AT_Wins', 'AT_Draws', 'AT_Losses', 'H2H_HT_Win_Rate'])
    return pd.concat([df, feature_df], axis=1)

df_featured = feature_engineering_simplified(df.copy())
df_featured['Prob_H'] = 1/df_featured['B365H'].replace(0,1e-6); df_featured['Prob_D'] = 1/df_featured['B365D'].replace(0,1e-6); df_featured['Prob_A'] = 1/df_featured['B365A'].replace(0,1e-6)
total_prob = df_featured['Prob_H']+df_featured['Prob_D']+df_featured['Prob_A']; df_featured['Norm_Prob_H']=df_featured['Prob_H']/total_prob; df_featured['Norm_Prob_D']=df_featured['Prob_D']/total_prob; df_featured['Norm_Prob_A']=df_featured['Prob_A']/total_prob
df_featured['Prob_Over'] = 1/df_featured['Avg>2.5'].replace(0,1e-6); df_featured['Prob_Under'] = 1/df_featured['Avg<2.5'].replace(0,1e-6)
total_prob_ou = df_featured['Prob_Over']+df_featured['Prob_Under']; df_featured['Norm_Prob_Over']=df_featured['Prob_Over']/total_prob_ou; df_featured['Norm_Prob_Under']=df_featured['Prob_Under']/total_prob_ou
df_featured.dropna(inplace=True)
print(f"Jumlah baris data setelah feature engineering: {df_featured.shape[0]}")

df_featured['Over_2.5'] = ((df_featured['FTHG'] + df_featured['FTAG']) > 2.5).astype(int)
features = ['Avg_HT_GS', 'Avg_HT_GC', 'HT_Wins', 'HT_Draws', 'HT_Losses', 'Avg_AT_GS', 'Avg_AT_GC', 'AT_Wins', 'AT_Draws', 'AT_Losses', 'H2H_HT_Win_Rate', 'Norm_Prob_H', 'Norm_Prob_D', 'Norm_Prob_A', 'Norm_Prob_Over', 'Norm_Prob_Under']

# --- Langkah 4: Melatih, Mengevaluasi, dan MENYIMPAN Model ---
print("\n--- MEMPROSES PREDIKSI 80/20 DENGAN FITUR RINGKAS ---")

# 4.1: Model Pemenang (H/A) - Juara: Neural Network
df_binary = df_featured[df_featured['FTR'] != 'D'].copy()
X_ha, y_ha = df_binary[features], df_binary['FTR'].map({'H': 1, 'A': 0})
X_train_ha, X_test_ha, y_train_ha, y_test_ha = train_test_split(X_ha, y_ha, test_size=0.2, random_state=42, stratify=y_ha)
scaler_ha = StandardScaler().fit(X_train_ha)
X_train_ha_scaled = scaler_ha.transform(X_train_ha)
X_test_ha_scaled = scaler_ha.transform(X_test_ha)
model_ha = MLPClassifier(activation='tanh', alpha=0.0001, hidden_layer_sizes=(150, 75), max_iter=1000, random_state=42, early_stopping=True)
model_ha.fit(X_train_ha_scaled, y_train_ha)

# BARU: Simpan model dan scaler untuk Pemenang
joblib.dump(model_ha, 'model_pemenang.joblib')
joblib.dump(scaler_ha, 'scaler_pemenang.joblib')
print("\nModel & Scaler untuk Pemenang (H/A) telah disimpan.")

y_pred_ha = model_ha.predict(X_test_ha_scaled)
print("\n--- LAPORAN: PEMENANG (HOME vs AWAY) ---")
print(f"Akurasi: {accuracy_score(y_test_ha, y_pred_ha):.2f}")
print(classification_report(y_test_ha, y_pred_ha, target_names=['Away', 'Home']))

# 4.2: Model Over/Under 2.5 - Juara: Logistic Regression
X_ou, y_ou = df_featured[features], df_featured['Over_2.5']
X_train_ou, X_test_ou, y_train_ou, y_test_ou = train_test_split(X_ou, y_ou, test_size=0.2, random_state=42, stratify=y_ou)
scaler_ou = StandardScaler().fit(X_train_ou)
X_train_ou_scaled = scaler_ou.transform(X_train_ou)
X_test_ou_scaled = scaler_ou.transform(X_test_ou)
model_ou = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
model_ou.fit(X_train_ou_scaled, y_train_ou)

# BARU: Simpan model dan scaler untuk Over/Under
joblib.dump(model_ou, 'model_over_under.joblib')
joblib.dump(scaler_ou, 'scaler_over_under.joblib')
print("\nModel & Scaler untuk Over/Under 2.5 telah disimpan.")

y_pred_ou = model_ou.predict(X_test_ou_scaled)
print("\n--- LAPORAN: OVER/UNDER 2.5 GOL ---")
print(f"Akurasi: {accuracy_score(y_test_ou, y_pred_ou):.2f}")
print(classification_report(y_test_ou, y_pred_ou, target_names=['Under 2.5', 'Over 2.5']))


# --- (BARU) Langkah 5: Contoh Cara Memuat & Menggunakan Model yang Disimpan ---
# Bagian ini bisa Anda jadikan skrip terpisah (misal: predict.py)
# Untuk menjalankannya, hapus tanda komentar di bawah ini.

# print("\n\n--- CONTOH PENGGUNAAN MODEL YANG TELAH DISIMPAN ---")

# # 1. Muat kembali model dan scaler dari file
# loaded_model_ha = joblib.load('model_pemenang.joblib')
# loaded_scaler_ha = joblib.load('scaler_pemenang.joblib')
# loaded_model_ou = joblib.load('model_over_under.joblib')
# loaded_scaler_ou = joblib.load('scaler_over_under.joblib')
# print("Model dan scaler berhasil dimuat.")

# # 2. Siapkan data baru (contoh, bisa diganti dengan input manual)
# # Data ini harus memiliki semua kolom fitur, bahkan jika nilainya 0
# new_match_features = {
#     'Avg_HT_GS': 2.5, 'Avg_HT_GC': 0.5, 'HT_Wins': 5, 'HT_Draws': 0, 'HT_Losses': 0,
#     'Avg_AT_GS': 1.5, 'Avg_AT_GC': 1.2, 'AT_Wins': 2, 'AT_Draws': 2, 'AT_Losses': 1,
#     'H2H_HT_Win_Rate': 0.7,
#     'Norm_Prob_H': 0.55, 'Norm_Prob_D': 0.25, 'Norm_Prob_A': 0.20,
#     'Norm_Prob_Over': 0.60, 'Norm_Prob_Under': 0.40
# }
# new_match_df = pd.DataFrame([new_match_features])

# # 3. Lakukan scaling pada data baru
# new_match_scaled_ha = loaded_scaler_ha.transform(new_match_df)
# new_match_scaled_ou = loaded_scaler_ou.transform(new_match_df)

# # 4. Buat prediksi
# pred_ha_loaded = loaded_model_ha.predict(new_match_scaled_ha)
# pred_ou_loaded = loaded_model_ou.predict(new_match_scaled_ou)

# # 5. Tampilkan hasil
# print("\nPrediksi dari model yang dimuat:")
# print(f"Pemenang (H/A): {'Home' if pred_ha_loaded[0] == 1 else 'Away'}")
# print(f"Over/Under 2.5: {'Over 2.5' if pred_ou_loaded[0] == 1 else 'Under 2.5'}")