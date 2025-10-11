import os
import glob
import joblib
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# -------------------------
# KONFIGURASI
# -------------------------
DATASET_DIR = 'dataset'
MODEL_DIR = 'models'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'arkan')
INITIAL_ELO = 1500

FEATURE_COLUMNS = [
    'AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5',
    'HomeTeamElo', 'AwayTeamElo', 'EloDifference',
    'Home_AvgGoalsScored', 'Home_AvgGoalsConceded', 'Home_Wins', 'Home_Draws', 'Home_Losses',
    'Away_AvgGoalsScored', 'Away_AvgGoalsConceded', 'Away_Wins', 'Away_Draws', 'Away_Losses',
    'HTH_HomeWins', 'HTH_AwayWins', 'HTH_Draws',
    'HTH_AvgHomeGoals', 'HTH_AvgAwayGoals'
]

app = Flask(__name__, template_folder='templates', static_folder='static')


# ==========================================================
# UTILITAS
# ==========================================================
def pretty_league_name(file_name):
    name = file_name.replace('dataset_', '').replace('.csv', '')
    name = name.replace('_1', '').replace('_', ' ').title()
    return name

def file_name_from_pretty(league_display):
    base = league_display.lower().replace(' ', '_')
    return f"dataset_{base}_1"

def list_leagues():
    files = glob.glob(os.path.join(DATASET_DIR, '*.csv'))
    leagues = [pretty_league_name(os.path.splitext(os.path.basename(p))[0]) for p in files]
    return leagues

def load_league_dataset_by_name(league_display):
    league_file = file_name_from_pretty(league_display)
    path = os.path.join(DATASET_DIR, f"{league_file}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset '{league_display}' tidak ditemukan.")
    df = pd.read_csv(path)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df

# ==========================================================
# FITUR OTOMATIS
# ==========================================================
def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def recent_stats_for_team(df, team, window=5):
    mask = (df['HomeTeam'] == team) | (df['AwayTeam'] == team)
    team_games = df[mask].sort_values('Date', ascending=False) if 'Date' in df.columns else df[mask]
    if team_games.empty:
        return {'AvgGoalsScored': 0, 'AvgGoalsConceded': 0, 'Wins': 0, 'Draws': 0, 'Losses': 0}
    recent = team_games.head(window)

    def gs(row): return row['FTHG'] if row['HomeTeam'] == team else row['FTAG']
    def gc(row): return row['FTAG'] if row['HomeTeam'] == team else row['FTHG']

    scored = recent.apply(gs, axis=1)
    conceded = recent.apply(gc, axis=1)

    def result(row):
        if row['HomeTeam'] == team:
            h, a = row['FTHG'], row['FTAG']
        else:
            h, a = row['FTAG'], row['FTHG']
        if h > a:
            return 'W'
        elif h == a:
            return 'D'
        else:
            return 'L'

    res = recent.apply(result, axis=1)
    return {
        'AvgGoalsScored': float(scored.mean()),
        'AvgGoalsConceded': float(conceded.mean()),
        'Wins': int((res == 'W').sum()),
        'Draws': int((res == 'D').sum()),
        'Losses': int((res == 'L').sum())
    }

# ==========================================================
# HITUNG H2H STATISTICS DARI DATA MENTAH
# ==========================================================
def h2h_stats(df, home_team, away_team, window=5):
    """
    Mengambil statistik H2H dari dataset mentah:
    - Mengambil 5 match terakhir antara home_team dan away_team
    - Jika home_team di posisi home -> ambil FTHG
      Jika home_team di posisi away -> ambil FTAG
    - Menghitung:
        HTH_HomeWins, HTH_AwayWins, HTH_Draws,
        HTH_AvgHomeGoals, HTH_AvgAwayGoals
    """
    # Filter match antara kedua tim
    mask = ((df['HomeTeam'] == home_team) & (df['AwayTeam'] == away_team)) | \
           ((df['HomeTeam'] == away_team) & (df['AwayTeam'] == home_team))
    
    hth = df[mask].sort_values('Date', ascending=False).head(window)
    
    hth_home_wins = 0
    hth_away_wins = 0
    hth_draws = 0
    home_goals = []
    away_goals = []

    for _, row in hth.iterrows():
        if row['HomeTeam'] == home_team:
            h_goals = row['FTHG']
            a_goals = row['FTAG']
        else:
            h_goals = row['FTAG']
            a_goals = row['FTHG']

        home_goals.append(h_goals)
        away_goals.append(a_goals)

        # Hitung hasil
        if h_goals > a_goals:
            hth_home_wins += 1
        elif h_goals < a_goals:
            hth_away_wins += 1
        else:
            hth_draws += 1

    avg_home_goals = float(np.mean(home_goals)) if home_goals else 0
    avg_away_goals = float(np.mean(away_goals)) if away_goals else 0

    return {
        'HTH_HomeWins': hth_home_wins,
        'HTH_AwayWins': hth_away_wins,
        'HTH_Draws': hth_draws,
        'HTH_AvgHomeGoals': avg_home_goals,
        'HTH_AvgAwayGoals': avg_away_goals
    }




def compute_features_from_dataset(df, home_team, away_team, window=5):
    last_home_elo, last_away_elo = INITIAL_ELO, INITIAL_ELO
    if 'HomeTeamElo' in df.columns and 'AwayTeamElo' in df.columns:
        tmp_h = df[(df['HomeTeam'] == home_team) | (df['AwayTeam'] == home_team)]
        if not tmp_h.empty:
            row = tmp_h.sort_values('Date', ascending=False).iloc[0]
            last_home_elo = row['HomeTeamElo'] if row['HomeTeam'] == home_team else row['AwayTeamElo']

        tmp_a = df[(df['HomeTeam'] == away_team) | (df['AwayTeam'] == away_team)]
        if not tmp_a.empty:
            row = tmp_a.sort_values('Date', ascending=False).iloc[0]
            last_away_elo = row['HomeTeamElo'] if row['HomeTeam'] == away_team else row['AwayTeamElo']

    home_stats = recent_stats_for_team(df, home_team)
    away_stats = recent_stats_for_team(df, away_team)

    # Ambil H2H stats 5 match terakhir
    hth = h2h_stats(df, home_team, away_team, window=5) or {}

    return {
        'AvgH': '', 'AvgD': '', 'AvgA': '', 'Avg>2.5': '', 'Avg<2.5': '',
        'HomeTeamElo': last_home_elo,
        'AwayTeamElo': last_away_elo,
        'EloDifference': last_home_elo - last_away_elo,
        'Home_AvgGoalsScored': home_stats['AvgGoalsScored'],
        'Home_AvgGoalsConceded': home_stats['AvgGoalsConceded'],
        'Home_Wins': home_stats['Wins'],
        'Home_Draws': home_stats['Draws'],
        'Home_Losses': home_stats['Losses'],
        'Away_AvgGoalsScored': away_stats['AvgGoalsScored'],
        'Away_AvgGoalsConceded': away_stats['AvgGoalsConceded'],
        'Away_Wins': away_stats['Wins'],
        'Away_Draws': away_stats['Draws'],
        'Away_Losses': away_stats['Losses'],
        'HTH_HomeWins': hth['HTH_HomeWins'],
        'HTH_AwayWins': hth['HTH_AwayWins'],
        'HTH_Draws': hth['HTH_Draws'],
        'HTH_AvgHomeGoals': hth['HTH_AvgHomeGoals'],
        'HTH_AvgAwayGoals': hth['HTH_AvgAwayGoals']
    }

# ==========================================================
# FITUR ADD DATA & HITUNG ELO
# ==========================================================
def update_elo_and_features(df_existing, df_new, window=5, K=30, initial_elo=1500):
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined = df_combined.sort_values('Date').reset_index(drop=True)
    elo = {}
    new_rows = []

    for idx, row in df_combined.iterrows():
        home, away = row['HomeTeam'], row['AwayTeam']
        h_elo = elo.get(home, initial_elo)
        a_elo = elo.get(away, initial_elo)

        # Expected score
        E_h = 1 / (1 + 10 ** ((a_elo - h_elo) / 400))
        E_a = 1 - E_h

        # Hasil pertandingan
        if row['FTHG'] > row['FTAG']: S_h, S_a = 1, 0
        elif row['FTHG'] < row['FTAG']: S_h, S_a = 0, 1
        else: S_h, S_a = 0.5, 0.5

        # Update Elo
        h_elo_new = h_elo + K * (S_h - E_h)
        a_elo_new = a_elo + K * (S_a - E_a)
        elo[home], elo[away] = h_elo_new, a_elo_new

        # Statistik tim
        df_past = df_combined.iloc[:idx]
        home_stats = recent_stats_for_team(df_past, home, window)
        away_stats = recent_stats_for_team(df_past, away, window)

        # H2H
        hth_mask = ((df_past['HomeTeam'] == home) & (df_past['AwayTeam'] == away)) | \
                   ((df_past['HomeTeam'] == away) & (df_past['AwayTeam'] == home))
        hth = df_past[hth_mask].sort_values('Date', ascending=False).head(window)
        hth_home_wins = hth_away_wins = hth_draws = 0
        if not hth.empty:
            for _, r in hth.iterrows():
                if r['HomeTeam'] == home:
                    if r['FTHG'] > r['FTAG']: hth_home_wins += 1
                    elif r['FTHG'] < r['FTAG']: hth_away_wins += 1
                    else: hth_draws += 1
            hth_avg_home_goals = float(hth['FTHG'].mean())
            hth_avg_away_goals = float(hth['FTAG'].mean())
        else:
            hth_avg_home_goals = hth_avg_away_goals = 0

        row_full = row.copy()
        row_full['HomeTeamElo'] = h_elo_new
        row_full['AwayTeamElo'] = a_elo_new
        row_full['EloDifference'] = h_elo_new - a_elo_new
        row_full['Home_AvgGoalsScored'] = home_stats['AvgGoalsScored']
        row_full['Home_AvgGoalsConceded'] = home_stats['AvgGoalsConceded']
        row_full['Home_Wins'] = home_stats['Wins']
        row_full['Home_Draws'] = home_stats['Draws']
        row_full['Home_Losses'] = home_stats['Losses']
        row_full['Away_AvgGoalsScored'] = away_stats['AvgGoalsScored']
        row_full['Away_AvgGoalsConceded'] = away_stats['AvgGoalsConceded']
        row_full['Away_Wins'] = away_stats['Wins']
        row_full['Away_Draws'] = away_stats['Draws']
        row_full['Away_Losses'] = away_stats['Losses']
        row_full['HTH_HomeWins'] = hth_home_wins
        row_full['HTH_AwayWins'] = hth_away_wins
        row_full['HTH_Draws'] = hth_draws
        row_full['HTH_AvgHomeGoals'] = hth_avg_home_goals
        row_full['HTH_AvgAwayGoals'] = hth_avg_away_goals
        row_full['AvgH'] = ''
        row_full['AvgD'] = ''
        row_full['AvgA'] = ''
        row_full['Avg>2.5'] = ''
        row_full['Avg<2.5'] = ''

        if idx >= len(df_existing):
            new_rows.append(row_full)

    return pd.DataFrame(new_rows)

# ==========================================================
# ROUTES HALAMAN PREDIKSI (tetap sama)
# ==========================================================
@app.route('/')
def index():
    leagues = list_leagues()
    return render_template('index.html', leagues=leagues)

@app.route('/api/leagues')
def api_leagues():
    return jsonify({'status': 'ok', 'leagues': list_leagues()})

@app.route('/api/teams')
def api_teams():
    league = request.args.get('league')
    if not league:
        return jsonify({'status': 'error', 'message': 'parameter league diperlukan'}), 400
    df = load_league_dataset_by_name(league)
    teams = sorted(set(df['HomeTeam']).union(set(df['AwayTeam'])))
    return jsonify({'status': 'ok', 'teams': teams})

@app.route('/api/features', methods=['POST'])
def api_features():
    body = request.json or {}
    league = body.get('league')
    home = body.get('home')
    away = body.get('away')
    if not all([league, home, away]):
        return jsonify({'status': 'error', 'message': 'league, home, away dibutuhkan'}), 400
    df = load_league_dataset_by_name(league)
    feats = compute_features_from_dataset(df, home, away)
    return jsonify({'status': 'ok', 'features': feats})

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        body = request.json or {}
        league = body.get('league')
        features = body.get('features')

        if not all([league, features]):
            return jsonify({'status': 'error', 'message': 'Data liga dan fitur diperlukan'}), 400

        league_dir = os.path.join(MODEL_DIR, league.lower().replace(' ', '_'))
        model_hda = joblib.load(os.path.join(league_dir, 'model_hda.pkl'))
        model_ou25 = joblib.load(os.path.join(league_dir, 'model_ou25.pkl'))
        model_btts = joblib.load(os.path.join(league_dir, 'model_btts.pkl'))
        scaler = joblib.load(os.path.join(league_dir, 'scaler.pkl'))
        le_ftr = joblib.load(os.path.join(league_dir, 'le_ftr.pkl'))
        le_ou = joblib.load(os.path.join(league_dir, 'le_ou.pkl'))
        le_btts = joblib.load(os.path.join(league_dir, 'le_btts.pkl'))

        df_features = pd.DataFrame([features])
        df_features = df_features[FEATURE_COLUMNS]
        X_scaled = scaler.transform(df_features)

        probs_hda = model_hda.predict_proba(X_scaled)[0]
        probs_ou = model_ou25.predict_proba(X_scaled)[0]
        probs_btts = model_btts.predict_proba(X_scaled)[0]

        # Gunakan classes_ dari LabelEncoder agar mapping benar
        probs_hda_dict = {le_ftr.classes_[i]: float(probs_hda[i]) for i in range(len(probs_hda))}
        probs_ou_dict  = {le_ou.classes_[i]: float(probs_ou[i]) for i in range(len(probs_ou))}
        probs_btts_dict = {le_btts.classes_[i]: float(probs_btts[i]) for i in range(len(probs_btts))}

        pred_hda = le_ftr.classes_[np.argmax(probs_hda)]
        pred_ou  = le_ou.classes_[np.argmax(probs_ou)]
        pred_btts = le_btts.classes_[np.argmax(probs_btts)]

        return jsonify({
            'status': 'ok',
            'prediction': {
                'HDA': {'label': pred_hda, 'probs': probs_hda_dict},
                'OU25': {'label': pred_ou, 'probs': probs_ou_dict},
                'BTTS': {'label': pred_btts, 'probs': probs_btts_dict}
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


# ==========================================================
# ROUTES HALAMAN ADD DATA
# ==========================================================
@app.route('/add_data')
def add_data_page():
    leagues = list_leagues()
    return render_template('add_data.html', leagues=leagues)

@app.route('/api/upload_csv', methods=['POST'])
def api_upload_csv():
    league = request.form.get('league')
    file = request.files.get('file')
    if not all([league, file]):
        return jsonify({'status':'error','message':'Liga dan file CSV diperlukan'}), 400

    filename = secure_filename(file.filename)
    df_new = pd.read_csv(file)
    df_existing = load_league_dataset_by_name(league)

    # Filter hanya pertandingan baru
    mask_new = ~df_new.apply(lambda r: ((df_existing['Date'] == r['Date']) &
                                        (df_existing['HomeTeam'] == r['HomeTeam']) &
                                        (df_existing['AwayTeam'] == r['AwayTeam'])).any(), axis=1)
    df_new_only = df_new[mask_new].copy()

    if df_new_only.empty:
        return jsonify({'status':'ok','message':'Tidak ada pertandingan baru'}), 200

    # Hitung Elo & fitur
    df_new_full = update_elo_and_features(df_existing, df_new_only)

    return jsonify({'status':'ok','matches': df_new_full.to_dict(orient='records')})

@app.route('/api/save_new_matches', methods=['POST'])
def api_save_new_matches():
    league = request.json.get('league')
    matches = request.json.get('matches')
    password = request.json.get('password')
    if password != ADMIN_PASSWORD:
        return jsonify({'status':'error','message':'Password salah'}), 403

    df_existing = load_league_dataset_by_name(league)
    df_new = pd.DataFrame(matches)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    league_file = file_name_from_pretty(league)
    path = os.path.join(DATASET_DIR, f"{league_file}.csv")
    df_combined.to_csv(path, index=False)

    return jsonify({'status':'ok','message':'Pertandingan baru berhasil disimpan'})

# ==========================================================
# MAIN
# ==========================================================
if __name__ == '__main__':
    os.makedirs(DATASET_DIR, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=8000)
