import pandas as pd
import joblib

def predict_new_match_manual(manual_inputs, models, scalers, features):
    """
    Membuat prediksi menggunakan model yang sudah disimpan.
    """
    # Hitung probabilitas odds
    prob_h, prob_d, prob_a = 1/manual_inputs['odds_h'], 1/manual_inputs['odds_d'], 1/manual_inputs['odds_a']
    total_prob_hda = prob_h + prob_d + prob_a
    manual_inputs['Norm_Prob_H'], manual_inputs['Norm_Prob_D'], manual_inputs['Norm_Prob_A'] = prob_h/total_prob_hda, prob_d/total_prob_hda, prob_a/total_prob_hda
    prob_over = 1 / manual_inputs['odds_over_2_5']
    prob_under = 1 / manual_inputs['odds_under_2_5']
    total_prob_ou = prob_over + prob_under
    manual_inputs['Norm_Prob_Over'] = prob_over / total_prob_ou
    manual_inputs['Norm_Prob_Under'] = prob_under / total_prob_ou
    
    feature_vector = pd.DataFrame([manual_inputs])[features]
    
    # Lakukan scaling dan prediksi
    X_scaled_ha = scalers['ha'].transform(feature_vector)
    pred_ha = 'Home' if models['ha'].predict(X_scaled_ha)[0] == 1 else 'Away'
    
    X_scaled_ou = scalers['ou'].transform(feature_vector)
    pred_ou = 'Over 2.5' if models['ou'].predict(X_scaled_ou)[0] == 1 else 'Under 2.5'
    
    return {"Pemenang (H/A)": pred_ha, "Over/Under 2.5": pred_ou}

# --- BAGIAN UTAMA PREDIKSI ---

# 1. Muat model, scaler, dan daftar fitur yang sudah disimpan
try:
    models = {
        'ha': joblib.load('models/model_pemenang.joblib'),
        'ou': joblib.load('models/model_over_under.joblib')
    }
    scalers = {
        'ha': joblib.load('models/scaler_pemenang.joblib'),
        'ou': joblib.load('models/scaler_over_under.joblib')
    }
    features = joblib.load('models/features.joblib')
    print("Model, scaler, dan fitur berhasil dimuat.")
except FileNotFoundError:
    print("Error: File model tidak ditemukan. Harap jalankan 'train.py' terlebih dahulu.")
    exit()

# 2. Siapkan input manual untuk pertandingan baru
# Ganti nilai-nilai di bawah ini sesuai pertandingan yang ingin diprediksi
manual_inputs = {
    # Statistik Tim Tuan Rumah (5 laga terakhir)
    'Avg_HT_GS': 2.2, 'Avg_HT_GC': 0.6, 'HT_Wins': 4, 'HT_Draws': 1, 'HT_Losses': 0,
    # Statistik Tim Tamu (5 laga terakhir)
    'Avg_AT_GS': 1.8, 'Avg_AT_GC': 1.0, 'AT_Wins': 3, 'AT_Draws': 1, 'AT_Losses': 1,
    # H2H (Persentase kemenangan tim tuan rumah)
    'H2H_HT_Win_Rate': 0.5, # 50%
    # Odds Pertandingan
    'odds_h': 1.70, 'odds_d': 3.90, 'odds_a': 4.75,
    'odds_over_2_5': 1.85, 'odds_under_2_5': 1.95
}

# 3. Panggil fungsi dan tampilkan hasil prediksi
hasil_prediksi = predict_new_match_manual(
    manual_inputs=manual_inputs,
    models=models,
    scalers=scalers,
    features=features
)

print(f"\n--- HASIL PREDIKSI MANUAL ---")
for pasar, prediksi in hasil_prediksi.items():
    print(f"{pasar}: {prediksi}")