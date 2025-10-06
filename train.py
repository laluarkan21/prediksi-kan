import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import warnings
from sklearn.exceptions import ConvergenceWarning

# Impor fungsi dari file lain
from data_loader import load_and_clean_data
from feature_engineering import feature_engineering_simplified

warnings.filterwarnings("ignore", category=ConvergenceWarning)

# --- LANGKAH UTAMA ---

# 1. Memuat dan Membersihkan Data
df = load_and_clean_data(file_path='dataset/dataset_pertandingan.csv')

if df is not None:
    # 2. Rekayasa Fitur
    df_featured = feature_engineering_simplified(df.copy())
    
    # 3. Hitung Probabilitas Odds
    df_featured['Prob_H'] = 1/df_featured['B365H'].replace(0,1e-6); df_featured['Prob_D'] = 1/df_featured['B365D'].replace(0,1e-6); df_featured['Prob_A'] = 1/df_featured['B365A'].replace(0,1e-6)
    total_prob = df_featured['Prob_H']+df_featured['Prob_D']+df_featured['Prob_A']; df_featured['Norm_Prob_H']=df_featured['Prob_H']/total_prob; df_featured['Norm_Prob_D']=df_featured['Prob_D']/total_prob; df_featured['Norm_Prob_A']=df_featured['Prob_A']/total_prob
    df_featured['Prob_Over'] = 1/df_featured['Avg>2.5'].replace(0,1e-6); df_featured['Prob_Under'] = 1/df_featured['Avg<2.5'].replace(0,1e-6)
    total_prob_ou = df_featured['Prob_Over']+df_featured['Prob_Under']; df_featured['Norm_Prob_Over']=df_featured['Prob_Over']/total_prob_ou; df_featured['Norm_Prob_Under']=df_featured['Prob_Under']/total_prob_ou
    df_featured.dropna(inplace=True)
    print(f"Jumlah baris data setelah feature engineering: {df_featured.shape[0]}")

    # 4. Membuat Target & Daftar Fitur
    df_featured['Over_2.5'] = ((df_featured['FTHG'] + df_featured['FTAG']) > 2.5).astype(int)
    features = [
        'Avg_HT_GS', 'Avg_HT_GC', 'HT_Wins', 'HT_Draws', 'HT_Losses',
        'Avg_AT_GS', 'Avg_AT_GC', 'AT_Wins', 'AT_Draws', 'AT_Losses',
        'H2H_HT_Win_Rate',
        'Norm_Prob_H', 'Norm_Prob_D', 'Norm_Prob_A',
        'Norm_Prob_Over', 'Norm_Prob_Under'
    ]

    # 5. Melatih, Mengevaluasi, dan Menyimpan Model
    print("\n--- MEMULAI PROSES TRAINING & EVALUASI ---")
    
    # Model Pemenang (H/A)
    df_binary = df_featured[df_featured['FTR'] != 'D'].copy()
    X_ha, y_ha = df_binary[features], df_binary['FTR'].map({'H': 1, 'A': 0})
    X_train_ha, X_test_ha, y_train_ha, y_test_ha = train_test_split(X_ha, y_ha, test_size=0.2, random_state=42, stratify=y_ha)
    scaler_ha = StandardScaler().fit(X_train_ha)
    X_train_ha_scaled = scaler_ha.transform(X_train_ha)
    X_test_ha_scaled = scaler_ha.transform(X_test_ha)
    model_ha = MLPClassifier(activation='tanh', alpha=0.0001, hidden_layer_sizes=(150, 75), max_iter=1000, random_state=42, early_stopping=True)
    model_ha.fit(X_train_ha_scaled, y_train_ha)
    
    # Model Over/Under 2.5
    X_ou, y_ou = df_featured[features], df_featured['Over_2.5']
    X_train_ou, X_test_ou, y_train_ou, y_test_ou = train_test_split(X_ou, y_ou, test_size=0.2, random_state=42, stratify=y_ou)
    scaler_ou = StandardScaler().fit(X_train_ou)
    X_train_ou_scaled = scaler_ou.transform(X_train_ou)
    X_test_ou_scaled = scaler_ou.transform(X_test_ou)
    model_ou = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    model_ou.fit(X_train_ou_scaled, y_train_ou)

    print("\n--- MODEL SELESAI DILATIH ---")

    # 6. Menyimpan model dan scaler ke folder 'models'
    os.makedirs('models', exist_ok=True)
    joblib.dump(model_ha, 'models/model_pemenang.joblib')
    joblib.dump(scaler_ha, 'models/scaler_pemenang.joblib')
    joblib.dump(model_ou, 'models/model_over_under.joblib')
    joblib.dump(scaler_ou, 'models/scaler_over_under.joblib')
    joblib.dump(features, 'models/features.joblib') # Simpan juga daftar fitur
    print("\nModel, scaler, dan daftar fitur telah disimpan di folder 'models/'.")

    # 7. Menampilkan Laporan Performa
    y_pred_ha = model_ha.predict(X_test_ha_scaled)
    print("\n--- LAPORAN: PEMENANG (HOME vs AWAY) ---")
    print(f"Akurasi: {accuracy_score(y_test_ha, y_pred_ha):.2f}")
    print(classification_report(y_test_ha, y_pred_ha, target_names=['Away', 'Home']))

    y_pred_ou = model_ou.predict(X_test_ou_scaled)
    print("\n--- LAPORAN: OVER/UNDER 2.5 GOL ---")
    print(f"Akurasi: {accuracy_score(y_test_ou, y_pred_ou):.2f}")
    print(classification_report(y_test_ou, y_pred_ou, target_names=['Under 2.5', 'Over 2.5']))