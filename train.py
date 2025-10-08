import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import warnings
from sklearn.exceptions import ConvergenceWarning

from data_loader import load_all_leagues_separately
from feature_engineering import create_features_and_labels

warnings.filterwarnings("ignore", category=ConvergenceWarning)

# --- LANGKAH UTAMA ---
leagues_raw_data = load_all_leagues_separately(folder_path='dataset')

if leagues_raw_data:
    leagues_processed_data = create_features_and_labels(leagues_raw_data)
    
    features = [
        'Avg_HT_GS', 'Avg_HT_GC', 'HT_Wins', 'HT_Draws', 'HT_Losses',
        'Avg_AT_GS', 'Avg_AT_GC', 'AT_Wins', 'AT_Draws', 'AT_Losses',
        'H2H_HT_Win_Rate', 'Norm_Prob_H', 'Norm_Prob_D', 'Norm_Prob_A',
        'Norm_Prob_Over', 'Norm_Prob_Under',
        'AHh', 'AvgAHH', 'AvgAHA'
    ]

    # DEBUG: Cetak jumlah fitur yang didefinisikan
    print(f"\n--- DEBUG: Daftar 'features' utama dibuat dengan {len(features)} item. ---")
    
    for liga_name, df_featured in leagues_processed_data.items():
        print(f"\n{'='*30}\nMEMULAI TRAINING LIGA: {liga_name.upper()}\n{'='*30}")
        
        liga_model_folder = os.path.join('models', liga_name)
        os.makedirs(liga_model_folder, exist_ok=True)
        
        # --- Model 1: Pemenang (H/D/A) ---
        print("\n1. Melatih model Pemenang (H/D/A)...")
        X_hda = df_featured[features]
        y_hda = df_featured['FTR'].map({'H': 2, 'D': 1, 'A': 0})
        # DEBUG: Cetak bentuk data X
        print(f"  DEBUG (HDA): DataFrame X dibuat dengan {X_hda.shape[1]} kolom.")
        
        X_train_hda, X_test_hda, y_train_hda, y_test_hda = train_test_split(X_hda, y_hda, test_size=0.2, random_state=42, stratify=y_hda)
        scaler_hda = StandardScaler().fit(X_train_hda)
        # DEBUG: Cetak jumlah fitur yang dipelajari scaler
        print(f"  DEBUG (HDA): Scaler dilatih dengan {len(scaler_hda.feature_names_in_)} fitur.")
        
        model_hda = MLPClassifier(activation='tanh', alpha=0.0001, hidden_layer_sizes=(150, 75), max_iter=1000, random_state=42, early_stopping=True)
        model_hda.fit(scaler_hda.transform(X_train_hda), y_train_hda)
        joblib.dump(model_hda, os.path.join(liga_model_folder, 'model_hda.joblib'))
        joblib.dump(scaler_hda, os.path.join(liga_model_folder, 'scaler_hda.joblib'))

        # --- Model 2: Over/Under 2.5 ---
        print("2. Melatih model Over/Under 2.5...")
        X_ou = df_featured[features]
        y_ou = df_featured['Over_2.5']
        print(f"  DEBUG (O/U): DataFrame X dibuat dengan {X_ou.shape[1]} kolom.")
        
        X_train_ou, X_test_ou, y_train_ou, y_test_ou = train_test_split(X_ou, y_ou, test_size=0.2, random_state=42, stratify=y_ou)
        scaler_ou = StandardScaler().fit(X_train_ou)
        print(f"  DEBUG (O/U): Scaler dilatih dengan {len(scaler_ou.feature_names_in_)} fitur.")
        
        model_ou = MLPClassifier(activation='relu', alpha=0.0001, hidden_layer_sizes=(128, 64), max_iter=1000, random_state=42, early_stopping=True)
        model_ou.fit(scaler_ou.transform(X_train_ou), y_train_ou)
        joblib.dump(model_ou, os.path.join(liga_model_folder, 'model_over_under.joblib'))
        joblib.dump(scaler_ou, os.path.join(liga_model_folder, 'scaler_over_under.joblib'))
        
        # --- Model 3: BTTS ---
        print("3. Melatih model BTTS...")
        X_btts = df_featured[features]
        y_btts = df_featured['BTTS']
        print(f"  DEBUG (BTTS): DataFrame X dibuat dengan {X_btts.shape[1]} kolom.")
        
        X_train_btts, X_test_btts, y_train_btts, y_test_btts = train_test_split(X_btts, y_btts, test_size=0.2, random_state=42, stratify=y_btts)
        scaler_btts = StandardScaler().fit(X_train_btts)
        print(f"  DEBUG (BTTS): Scaler dilatih dengan {len(scaler_btts.feature_names_in_)} fitur.")
        
        model_btts = MLPClassifier(activation='relu', alpha=0.001, hidden_layer_sizes=(100, 50, 25), max_iter=1000, random_state=42, early_stopping=True)
        model_btts.fit(scaler_btts.transform(X_train_btts), y_train_btts)
        joblib.dump(model_btts, os.path.join(liga_model_folder, 'model_btts.joblib'))
        joblib.dump(scaler_btts, os.path.join(liga_model_folder, 'scaler_btts.joblib'))
        
        # Simpan daftar fitur
        joblib.dump(features, os.path.join(liga_model_folder, 'features.joblib'))
        print(f"\nSemua model untuk liga {liga_name.upper()} telah disimpan.")

        # --- Menampilkan Laporan Performa ---
        print(f"\n--- LAPORAN KLASIFIKASI UNTUK {liga_name.upper()} ---")
        y_pred_hda = model_hda.predict(scaler_hda.transform(X_test_hda))
        print("\n--- TUGAS: PEMENANG (H/D/A) ---")
        print(f"Akurasi: {accuracy_score(y_test_hda, y_pred_hda):.3f}")
        print(classification_report(y_test_hda, y_pred_hda, target_names=['Away', 'Draw', 'Home'], zero_division=0))
        
        y_pred_ou = model_ou.predict(scaler_ou.transform(X_test_ou))
        print("\n--- TUGAS: OVER/UNDER 2.5 ---")
        print(f"Akurasi: {accuracy_score(y_test_ou, y_pred_ou):.3f}")
        print(classification_report(y_test_ou, y_pred_ou, target_names=['Under 2.5', 'Over 2.5'], zero_division=0))

        y_pred_btts = model_btts.predict(scaler_btts.transform(X_test_btts))
        print("\n--- TUGAS: BOTH TEAMS TO SCORE (BTTS) ---")
        print(f"Akurasi: {accuracy_score(y_test_btts, y_pred_btts):.3f}")
        print(classification_report(y_test_btts, y_pred_btts, target_names=['BTTS - No', 'BTTS - Yes'], zero_division=0))

print("\n--- SEMUA PROSES TRAINING SELESAI ---")