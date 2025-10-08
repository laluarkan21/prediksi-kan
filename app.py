from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import numpy as np
import os

app = Flask(__name__)

# --- Memuat Semua Model Saat Server Dijalankan ---
models, scalers, features_dict = {}, {}, {}
models_folder = 'models'
if os.path.exists(models_folder):
    for liga_name in os.listdir(models_folder):
        liga_path = os.path.join(models_folder, liga_name)
        if os.path.isdir(liga_path):
            try:
                # Memuat semua 4 model untuk setiap liga
                models[liga_name] = {
                    'hda': joblib.load(os.path.join(liga_path, 'model_hda.joblib')),
                    'ou': joblib.load(os.path.join(liga_path, 'model_over_under.joblib')),
                    'btts': joblib.load(os.path.join(liga_path, 'model_btts.joblib')),
                    'ha': joblib.load(os.path.join(liga_path, 'model_hda.joblib'))
                }
                scalers[liga_name] = {
                    'hda': joblib.load(os.path.join(liga_path, 'scaler_hda.joblib')),
                    'ou': joblib.load(os.path.join(liga_path, 'scaler_over_under.joblib')),
                    'btts': joblib.load(os.path.join(liga_path, 'scaler_btts.joblib')),
                    'ha': joblib.load(os.path.join(liga_path, 'scaler_hda.joblib'))
                }
                features_dict[liga_name] = joblib.load(os.path.join(liga_path, 'features.joblib'))
                print(f"Model untuk liga '{liga_name}' berhasil dimuat.")
            except FileNotFoundError:
                print(f"Peringatan: Folder model '{liga_name}' tidak lengkap atau nama file model salah.")
else:
    print("Error: Folder 'models' tidak ditemukan. Jalankan 'train.py' terlebih dahulu.")

@app.route('/')
def home():
    available_leagues = sorted(list(models.keys()))
    return render_template('index.html', leagues=available_leagues)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    liga_name = data.get('liga')

    if not liga_name or liga_name not in models:
        return jsonify({'error': 'Liga tidak valid atau model tidak ditemukan.'}), 400

    try:
        # --- KALKULASI FITUR DI BACKEND ---
        ht_scores, at_scores = data.get('ht_scores', []), data.get('at_scores', [])
        ht_gs,ht_gc,ht_w,ht_d,ht_l = 0,0,0,0,0
        for score in ht_scores:
            s=[int(p) for p in score.split('-')]; ht_gs+=s[0]; ht_gc+=s[1]
            if s[0]>s[1]: ht_w+=1
            elif s[0]==s[1]: ht_d+=1
            else: ht_l+=1
        
        at_gs,at_gc,at_w,at_d,at_l = 0,0,0,0,0
        for score in at_scores:
            s=[int(p) for p in score.split('-')]; at_gs+=s[0]; at_gc+=s[1]
            if s[0]>s[1]: at_w+=1
            elif s[0]==s[1]: at_d+=1
            else: at_l+=1
        
        # PERBAIKAN: Hitung rasio H2H dari input jumlah kemenangan
        h2h_wins = int(data.get('h2h_wins', 0))
        h2h_win_rate = h2h_wins / 5.0 # Diasumsikan selalu dari 5 pertandingan

        num_matches=5.0
        manual_inputs = {
            'Avg_HT_GS': ht_gs/num_matches, 'Avg_HT_GC': ht_gc/num_matches, 'HT_Wins': ht_w, 'HT_Draws': ht_d, 'HT_Losses': ht_l,
            'Avg_AT_GS': at_gs/num_matches, 'Avg_AT_GC': at_gc/num_matches, 'AT_Wins': at_w, 'AT_Draws': at_d, 'AT_Losses': at_l,
            'H2H_HT_Win_Rate': h2h_win_rate,
            'AHh': float(data.get('ahh', 0)), 'AvgAHH': float(data.get('avg_ahh', 0)), 'AvgAHA': float(data.get('avg_aha', 0))
        }
        
        odds_h,odds_d,odds_a=float(data['odds_h']),float(data['odds_d']),float(data['odds_a'])
        prob_h,prob_d,prob_a=1/odds_h,1/odds_d,1/odds_a
        total_prob_hda=prob_h+prob_d+prob_a
        manual_inputs['Norm_Prob_H'],manual_inputs['Norm_Prob_D'],manual_inputs['Norm_Prob_A']=prob_h/total_prob_hda,prob_d/total_prob_hda,prob_a/total_prob_hda
        
        odds_over,odds_under=float(data['odds_over_2_5']),float(data['odds_under_2_5'])
        prob_over,prob_under=1/odds_over,1/odds_under
        total_prob_ou=prob_over+prob_under
        manual_inputs['Norm_Prob_Over'],manual_inputs['Norm_Prob_Under']=prob_over/total_prob_ou,prob_under/total_prob_ou
        
        features = features_dict[liga_name]
        feature_vector = pd.DataFrame([manual_inputs])[features]
        feature_vector.fillna(0, inplace=True)

        # Prediksi H/D/A
        X_scaled_hda = scalers[liga_name]['hda'].transform(feature_vector)
        pred_hda_proba = models[liga_name]['hda'].predict_proba(X_scaled_hda)[0]
        label_map_hda = {2: 'Home', 1: 'Draw', 0: 'Away'}
        pred_hda_idx = np.argmax(pred_hda_proba)
        pred_hda_label = label_map_hda.get(pred_hda_idx, 'N/A')
        pred_hda_confidence = pred_hda_proba[pred_hda_idx]

        # Prediksi O/U
        X_scaled_ou = scalers[liga_name]['ou'].transform(feature_vector)
        pred_ou_proba = models[liga_name]['ou'].predict_proba(X_scaled_ou)[0]
        pred_ou_label = 'Over 2.5' if pred_ou_proba[1] > 0.5 else 'Under 2.5'
        pred_ou_confidence = pred_ou_proba[1] if pred_ou_label == 'Over 2.5' else pred_ou_proba[0]

        # Prediksi BTTS
        X_scaled_btts = scalers[liga_name]['btts'].transform(feature_vector)
        pred_btts_proba = models[liga_name]['btts'].predict_proba(X_scaled_btts)[0]
        pred_btts_label = 'Yes' if pred_btts_proba[1] > 0.5 else 'No'
        pred_btts_confidence = pred_btts_proba[1] if pred_btts_label == 'Yes' else pred_btts_proba[0]
        
        return jsonify({
            "prediksi_hda": f"{pred_hda_label} ({pred_hda_confidence:.0%})",
            "prediksi_ou": f"{pred_ou_label} ({pred_ou_confidence:.0%})",
            "prediksi_btts": f"{pred_btts_label} ({pred_btts_confidence:.0%})"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=False, host='0.0.0.0', port=port)

