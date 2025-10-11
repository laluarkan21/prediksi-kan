import pandas as pd
import numpy as np
import warnings
import os
import joblib
import glob
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score

# Impor model spesifik yang terpilih sebagai yang terbaik
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

# ==============================================================================
# KONFIGURASI
# ==============================================================================
DATASET_DIR = 'dataset'
MODEL_DIR = 'models' 

warnings.filterwarnings('ignore')

# --- DIUBAH: HTH_AvgTotalGoals dihapus dari daftar fitur ---
FEATURE_COLUMNS = [
    'AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5',
    'HomeTeamElo', 'AwayTeamElo', 'EloDifference',
    'Home_AvgGoalsScored', 'Home_AvgGoalsConceded', 'Home_Wins', 'Home_Draws', 'Home_Losses',
    'Away_AvgGoalsScored', 'Away_AvgGoalsConceded', 'Away_Wins', 'Away_Draws', 'Away_Losses',
    'HTH_HomeWins', 'HTH_AwayWins', 'HTH_Draws',
    'HTH_AvgHomeGoals', 'HTH_AvgAwayGoals'
]

# ==============================================================================
# FUNGSI UTAMA UNTUK MELATIH DAN MENGGEVALUASI SEMUA LIGA
# ==============================================================================
def train_and_evaluate_all_leagues():
    print("🚀 Memulai proses training dan evaluasi untuk semua liga...")
    
    dataset_paths = glob.glob(os.path.join(DATASET_DIR, '*.csv'))
    all_results = [] # Untuk menyimpan semua hasil akurasi

    if not dataset_paths:
        print(f"❌ ERROR: Tidak ada file dataset .csv yang ditemukan di folder '{DATASET_DIR}'.")
        return

    # Pastikan direktori model ada
    os.makedirs(MODEL_DIR, exist_ok=True)

    for path in dataset_paths:
        try:
            filename = os.path.basename(path)
            # Logika untuk mendapatkan nama liga: Asumsi format: <prefix>_<league>_<suffix>.csv
            parts = filename.split('_')
            league_name = '_'.join(parts[1:-1]) if len(parts) > 2 else parts[1].replace('.csv', '')
            
            print(f"\n{'='*20} PROCESSING LEAGUE: {league_name.upper()} {'='*20}")

            league_model_dir = os.path.join(MODEL_DIR, league_name)
            os.makedirs(league_model_dir, exist_ok=True)

            data = pd.read_csv(path)
            print(f"✅ Berhasil memuat file: {filename}")

            data['TotalGoals'] = data['FTHG'] + data['FTAG']
            data['OverUnder2.5'] = np.where(data['TotalGoals'] > 2.5, 'Over', 'Under')
            data['BTTS'] = np.where((data['FTHG'] > 0) & (data['FTAG'] > 0), 'Yes', 'No')

            if not all(col in data.columns for col in FEATURE_COLUMNS):
                print(f"⚠️  WARNING: Tidak semua fitur ditemukan di {filename}. Melewati liga ini.")
                continue

            X = data[FEATURE_COLUMNS]
            y_ftr = data['FTR']
            y_ou = data['OverUnder2.5']
            y_btts = data['BTTS']

            if X.isnull().sum().sum() > 0:
                # Mengisi nilai NaN dengan rata-rata kolom
                X = X.fillna(X.mean())

            WINDOW = 5
            X = X.iloc[WINDOW:]
            y_ftr = y_ftr.iloc[WINDOW:]
            y_ou = y_ou.iloc[WINDOW:]
            y_btts = y_btts.iloc[WINDOW:]
            
            # Memisahkan data menjadi set Latih dan Uji (80% / 20%)
            X_train, X_test, y_ftr_train, y_ftr_test = train_test_split(X, y_ftr, test_size=0.2, shuffle=False)
            _, _, y_ou_train, y_ou_test = train_test_split(X, y_ou, test_size=0.2, shuffle=False)
            _, _, y_btts_train, y_btts_test = train_test_split(X, y_btts, test_size=0.2, shuffle=False)
            print("✅ Data berhasil dipisah menjadi data latih (80%) dan uji (20%).")

            # Preprocessing pada data latih
            scaler_eval = StandardScaler()
            X_train_scaled = scaler_eval.fit_transform(X_train)
            X_test_scaled = scaler_eval.transform(X_test)

            le_ftr_eval, le_ou_eval, le_btts_eval = LabelEncoder(), LabelEncoder(), LabelEncoder()
            y_ftr_train_encoded = le_ftr_eval.fit_transform(y_ftr_train)
            y_ou_train_encoded = le_ou_eval.fit_transform(y_ou_train)
            y_btts_train_encoded = le_btts_eval.fit_transform(y_btts_train)

            print("\n--- Mengevaluasi Model pada Data Uji ---")
            
            # Model H/D/A -> Random Forest
            model_hda = RandomForestClassifier(n_estimators=300, min_samples_split=5, min_samples_leaf=4, max_features='log2', max_depth=20, criterion='gini', random_state=42, n_jobs=-1)
            model_hda.fit(X_train_scaled, y_ftr_train_encoded)
            y_pred_hda = model_hda.predict(X_test_scaled)
            acc_hda = accuracy_score(le_ftr_eval.transform(y_ftr_test), y_pred_hda)
            print(f"   - Akurasi H/D/A (Random Forest): {acc_hda:.2%}")
            
            # Model BTTS -> Support Vector Machine
            param_grid_svm = {'C': [0.1, 1, 10], 'gamma': ['scale', 'auto']}
            search_btts = GridSearchCV(SVC(random_state=42, probability=True), param_grid_svm, cv=3, n_jobs=-1)
            search_btts.fit(X_train_scaled, y_btts_train_encoded)
            model_btts = search_btts.best_estimator_
            y_pred_btts = model_btts.predict(X_test_scaled)
            acc_btts = accuracy_score(le_btts_eval.transform(y_btts_test), y_pred_btts)
            print(f"   - Akurasi BTTS (SVM): {acc_btts:.2%}")

            # Model O/U 2.5 -> Random Forest
            model_ou25 = RandomForestClassifier(n_estimators=300, min_samples_split=5, min_samples_leaf=4, max_features='log2', max_depth=20, criterion='gini', random_state=42, n_jobs=-1)
            model_ou25.fit(X_train_scaled, y_ou_train_encoded)
            y_pred_ou25 = model_ou25.predict(X_test_scaled)
            acc_ou25 = accuracy_score(le_ou_eval.transform(y_ou_test), y_pred_ou25)
            print(f"   - Akurasi O/U 2.5 (Random Forest): {acc_ou25:.2%}")

            # Simpan hasil akurasi
            all_results.append({'Liga': league_name.upper(), 'H/D/A (RF)': acc_hda, 'BTTS (SVM)': acc_btts, 'O/U 2.5 (RF)': acc_ou25})

            # Melatih ulang model pada KESELURUHAN DATA untuk disimpan
            print("\n--- Melatih Ulang Model pada Keseluruhan Data ---")
            scaler_final = StandardScaler()
            X_scaled_final = scaler_final.fit_transform(X)

            le_ftr_final, le_ou_final, le_btts_final = LabelEncoder(), LabelEncoder(), LabelEncoder()
            y_ftr_encoded_final = le_ftr_final.fit_transform(y_ftr)
            y_ou_encoded_final = le_ou_final.fit_transform(y_ou)
            y_btts_encoded_final = le_btts_final.fit_transform(y_btts)

            model_hda.fit(X_scaled_final, y_ftr_encoded_final)
            # Gunakan best_estimator_ dari GridSearchCV sebelumnya
            search_btts.best_estimator_.fit(X_scaled_final, y_btts_encoded_final) 
            model_ou25.fit(X_scaled_final, y_ou_encoded_final)
            print("✅ Model final berhasil dilatih ulang.")

            # Menyimpan model dan artifak yang sudah dilatih ulang
            joblib.dump(model_hda, os.path.join(league_model_dir, 'model_hda.pkl'))
            joblib.dump(search_btts.best_estimator_, os.path.join(league_model_dir, 'model_btts.pkl'))
            joblib.dump(model_ou25, os.path.join(league_model_dir, 'model_ou25.pkl'))
            joblib.dump(scaler_final, os.path.join(league_model_dir, 'scaler.pkl'))
            joblib.dump(le_ftr_final, os.path.join(league_model_dir, 'le_ftr.pkl'))
            joblib.dump(le_ou_final, os.path.join(league_model_dir, 'le_ou.pkl'))
            joblib.dump(le_btts_final, os.path.join(league_model_dir, 'le_btts.pkl'))

            print(f"✨ Model final untuk {league_name.upper()} telah disimpan di '{league_model_dir}'.")

        except Exception as e:
            print(f"❌ GAGAL memproses {filename}. Error: {e}")
            continue

    # Menampilkan tabel perbandingan akurasi akhir
    if all_results:
        print(f"\n\n{'='*25} PERBANDINGAN AKURASI AKHIR {'='*25}")
        results_df = pd.DataFrame(all_results).set_index('Liga')
        print(results_df.to_string(formatters={
            'H/D/A (RF)': '{:.2%}'.format,
            'BTTS (SVM)': '{:.2%}'.format,
            'O/U 2.5 (RF)': '{:.2%}'.format
        }))

    print(f"\n\n✨✨✨ Proses Selesai! Semua model telah dievaluasi, dilatih ulang, dan disimpan.")


if __name__ == '__main__':
    train_and_evaluate_all_leagues()
