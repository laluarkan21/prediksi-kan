import pandas as pd
import joblib
import os
import numpy as np # BARU: Impor library NumPy

def predict_new_match_manual(manual_inputs, models, scalers, features):
    """
    Membuat prediksi menggunakan model yang sudah disimpan dan menyertakan persentase peluang.
    """
    feature_dict = manual_inputs.copy()
    prob_h = 1 / feature_dict.pop('odds_h'); prob_d = 1 / feature_dict.pop('odds_d'); prob_a = 1 / feature_dict.pop('odds_a')
    total_prob_hda = prob_h + prob_d + prob_a
    feature_dict['Norm_Prob_H'] = prob_h / total_prob_hda; feature_dict['Norm_Prob_D'] = prob_d / total_prob_hda; feature_dict['Norm_Prob_A'] = prob_a / total_prob_hda
    prob_over = 1 / feature_dict.pop('odds_over_2_5'); prob_under = 1 / feature_dict.pop('odds_under_2_5')
    total_prob_ou = prob_over + prob_under
    feature_dict['Norm_Prob_Over'] = prob_over / total_prob_ou; feature_dict['Norm_Prob_Under'] = prob_under / total_prob_ou

    feature_vector = pd.DataFrame([feature_dict])[features]
    feature_vector.fillna(0, inplace=True)

    # --- Prediksi Pemenang (H/D/A) ---
    X_scaled_hda = scalers['hda'].transform(feature_vector)
    pred_hda_proba = models['hda'].predict_proba(X_scaled_hda)[0]
    label_map_hda = {2: 'Home', 1: 'Draw', 0: 'Away'}
    pred_hda_index = np.argmax(pred_hda_proba)
    pred_hda_label = label_map_hda.get(pred_hda_index, 'Tidak Diketahui')
    pred_hda_confidence = pred_hda_proba[pred_hda_index]

    # --- Prediksi Over/Under 2.5 ---
    X_scaled_ou = scalers['ou'].transform(feature_vector)
    pred_ou_proba = models['ou'].predict_proba(X_scaled_ou)[0]
    pred_ou_label = 'Over 2.5' if pred_ou_proba[1] > 0.5 else 'Under 2.5'
    pred_ou_confidence = pred_ou_proba[1] if pred_ou_label == 'Over 2.5' else pred_ou_proba[0]

    # --- Prediksi BTTS ---
    X_scaled_btts = scalers['btts'].transform(feature_vector)
    pred_btts_proba = models['btts'].predict_proba(X_scaled_btts)[0]
    pred_btts_label = 'Yes' if pred_btts_proba[1] > 0.5 else 'No'
    pred_btts_confidence = pred_btts_proba[1] if pred_btts_label == 'Yes' else pred_btts_proba[0]

    return {
        "Pemenang (H/D/A)": f"{pred_hda_label} ({pred_hda_confidence:.0%})",
        "Over/Under 2.5": f"{pred_ou_label} ({pred_ou_confidence:.0%})",
        "BTTS": f"{pred_btts_label} ({pred_btts_confidence:.0%})"
    }

# ================================================================
# --- BAGIAN UTAMA PREDIKSI ---
# ================================================================
# (Sisa kode di bawah ini tidak berubah)

semua_prediksi = {
    'dataset_premier_league': {"pertandingan": "Man United vs Arsenal", "input": {'Avg_HT_GS': 1.8, 'Avg_HT_GC': 1.2, 'HT_Wins': 3, 'HT_Draws': 1, 'HT_Losses': 1, 'Avg_AT_GS': 2.4, 'Avg_AT_GC': 0.8, 'AT_Wins': 4, 'AT_Draws': 1, 'AT_Losses': 0, 'H2H_HT_Win_Rate': 0.4, 'AHh': 0.25, 'AvgAHH': 1.90, 'AvgAHA': 2.00, 'odds_h': 2.80, 'odds_d': 3.50, 'odds_a': 2.50, 'odds_over_2_5': 1.85, 'odds_under_2_5': 1.95}},
    'dataset_laliga': {"pertandingan": "Real Madrid vs Barcelona", "input": {'Avg_HT_GS': 2.8, 'Avg_HT_GC': 0.4, 'HT_Wins': 5, 'HT_Draws': 0, 'HT_Losses': 0, 'Avg_AT_GS': 2.2, 'Avg_AT_GC': 0.6, 'AT_Wins': 4, 'AT_Draws': 1, 'AT_Losses': 0, 'H2H_HT_Win_Rate': 0.6, 'AHh': -0.5, 'AvgAHH': 2.00, 'AvgAHA': 1.90, 'odds_h': 1.90, 'odds_d': 3.80, 'odds_a': 3.90, 'odds_over_2_5': 1.75, 'odds_under_2_5': 2.05}},
    'dataset_serieA': {"pertandingan": "Juventus vs Inter", "input": {'Avg_HT_GS': 1.2, 'Avg_HT_GC': 0.4, 'HT_Wins': 3, 'HT_Draws': 2, 'HT_Losses': 0, 'Avg_AT_GS': 1.8, 'Avg_AT_GC': 0.8, 'AT_Wins': 4, 'AT_Draws': 0, 'AT_Losses': 1, 'H2H_HT_Win_Rate': 0.5, 'AHh': 0, 'AvgAHH': 1.92, 'AvgAHA': 1.98, 'odds_h': 2.50, 'odds_d': 3.20, 'odds_a': 2.90, 'odds_over_2_5': 2.10, 'odds_under_2_5': 1.75}},
    'dataset_bundesliga': {"pertandingan": "Bayern Munich vs Dortmund", "input": {'Avg_HT_GS': 3.0, 'Avg_HT_GC': 1.0, 'HT_Wins': 4, 'HT_Draws': 0, 'HT_Losses': 1, 'Avg_AT_GS': 2.5, 'Avg_AT_GC': 1.5, 'AT_Wins': 3, 'AT_Draws': 1, 'AT_Losses': 1, 'H2H_HT_Win_Rate': 0.7, 'AHh': -1.25, 'AvgAHH': 1.95, 'AvgAHA': 1.95, 'odds_h': 1.50, 'odds_d': 4.50, 'odds_a': 6.00, 'odds_over_2_5': 1.55, 'odds_under_2_5': 2.40}},
    'dataset_legue1': {"pertandingan": "Paris SG vs Marseille", "input": {'Avg_HT_GS': 2.8, 'Avg_HT_GC': 0.8, 'HT_Wins': 4, 'HT_Draws': 1, 'HT_Losses': 0, 'Avg_AT_GS': 1.6, 'Avg_AT_GC': 0.6, 'AT_Wins': 3, 'AT_Draws': 2, 'AT_Losses': 0, 'H2H_HT_Win_Rate': 0.8, 'AHh': -1.5, 'AvgAHH': 1.90, 'AvgAHA': 2.00, 'odds_h': 1.40, 'odds_d': 5.00, 'odds_a': 7.50, 'odds_over_2_5': 1.60, 'odds_under_2_5': 2.30}}
}

models_folder = 'models'
if not os.path.exists(models_folder):
    print(f"Error: Folder '{models_folder}' tidak ditemukan. Harap jalankan 'train.py' terlebih dahulu.")
    exit()

available_leagues = [d for d in os.listdir(models_folder) if os.path.isdir(os.path.join(models_folder, d))]

for liga_name in available_leagues:
    if liga_name not in semua_prediksi: continue
    pred_data = semua_prediksi[liga_name]
    liga_model_folder = os.path.join(models_folder, liga_name)
    manual_inputs = pred_data['input']
    try:
        models = {'hda': joblib.load(os.path.join(liga_model_folder, 'model_hda.joblib')), 'ou': joblib.load(os.path.join(liga_model_folder, 'model_over_under.joblib')), 'btts': joblib.load(os.path.join(liga_model_folder, 'model_btts.joblib'))}
        scalers = {'hda': joblib.load(os.path.join(liga_model_folder, 'scaler_hda.joblib')), 'ou': joblib.load(os.path.join(liga_model_folder, 'scaler_over_under.joblib')), 'btts': joblib.load(os.path.join(liga_model_folder, 'scaler_btts.joblib'))}
        features = joblib.load(os.path.join(liga_model_folder, 'features.joblib'))
        hasil_prediksi = predict_new_match_manual(manual_inputs=manual_inputs.copy(), models=models, scalers=scalers, features=features)
        print(f"\n--- HASIL PREDIKSI UNTUK LIGA: {liga_name.replace('dataset_', '').replace('_', ' ').title()} ---")
        print(f"    Pertandingan: {pred_data['pertandingan']}")
        for pasar, prediksi in hasil_prediksi.items():
            print(f"    {pasar}: {prediksi}")
    except FileNotFoundError:
        print(f"\n--- Peringatan: Model untuk liga '{liga_name}' tidak lengkap. Melewatkan. ---")
        continue