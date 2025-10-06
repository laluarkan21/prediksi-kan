from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import numpy as np

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# Muat model dan scaler saat server pertama kali dijalankan
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
    print("Model dan scaler berhasil dimuat.")
except FileNotFoundError:
    print("Error: File model/scaler tidak ditemukan. Harap jalankan 'train.py' terlebih dahulu.")
    models, scalers, features = None, None, None

# Rute untuk halaman utama
@app.route('/')
def home():
    return render_template('index.html')

# Rute untuk menerima data dan memberikan prediksi
@app.route('/predict', methods=['POST'])
def predict():
    if not models:
        return jsonify({'error': 'Model tidak dimuat!'}), 500

    # Ambil data JSON yang dikirim dari frontend
    manual_inputs = request.get_json()

    # Lakukan kalkulasi seperti di fungsi predict_new_match_manual
    try:
        # Hitung probabilitas odds HDA
        prob_h = 1 / float(manual_inputs['odds_h'])
        prob_d = 1 / float(manual_inputs['odds_d'])
        prob_a = 1 / float(manual_inputs['odds_a'])
        total_prob_hda = prob_h + prob_d + prob_a
        manual_inputs['Norm_Prob_H'] = prob_h / total_prob_hda
        manual_inputs['Norm_Prob_D'] = prob_d / total_prob_hda
        manual_inputs['Norm_Prob_A'] = prob_a / total_prob_hda
        
        # Hitung probabilitas odds O/U
        prob_over = 1 / float(manual_inputs['odds_over_2_5'])
        prob_under = 1 / float(manual_inputs['odds_under_2_5'])
        total_prob_ou = prob_over + prob_under
        manual_inputs['Norm_Prob_Over'] = prob_over / total_prob_ou
        manual_inputs['Norm_Prob_Under'] = prob_under / total_prob_ou
        
        # Buat DataFrame satu baris
        feature_vector = pd.DataFrame([manual_inputs])[features]
        feature_vector.fillna(0, inplace=True)

        # Lakukan scaling dan prediksi
        X_scaled_ha = scalers['ha'].transform(feature_vector)
        pred_ha = 'Home' if models['ha'].predict(X_scaled_ha)[0] == 1 else 'Away'
        
        X_scaled_ou = scalers['ou'].transform(feature_vector)
        pred_ou = 'Over 2.5' if models['ou'].predict(X_scaled_ou)[0] == 1 else 'Under 2.5'

        # Kembalikan hasil dalam format JSON
        return jsonify({
            "prediksi_pemenang": pred_ha,
            "prediksi_ou": pred_ou
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Jalankan server
if __name__ == '__main__':
    # Ambil port dari Koyeb, atau 5000 jika dijalankan lokal
    port = int(os.environ.get('PORT', 8000)) 
    # Jalankan dengan host '0.0.0.0' dan debug=False
    app.run(debug=False, host='0.0.0.0', port=port)