# ... (Semua import dan konfigurasi awal SAMA) ...
import os
import glob
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, g
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import secrets
from functools import wraps

# -------------------------
# KONFIGURASI APLIKASI
# -------------------------
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Konfigurasi Keamanan (WAJIB via Environment) ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL')

if not all([app.config['SECRET_KEY'], app.config['GOOGLE_CLIENT_ID'],
            app.config['GOOGLE_CLIENT_SECRET'], app.config['ADMIN_EMAIL']]):
    raise ValueError("Satu atau lebih environment variable (SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ADMIN_EMAIL) belum di-set.")

# --- Konfigurasi Database ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
oauth = OAuth(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -------------------------
# MODEL DATABASE
# -------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    league = db.Column(db.String(100), nullable=False)
    home_team = db.Column(db.String(100), nullable=False)
    away_team = db.Column(db.String(100), nullable=False)
    prediction_data = db.Column(db.JSON, nullable=False)
    user = db.relationship('User', backref=db.backref('histories', lazy=True, cascade="all, delete-orphan"))

# ... (Konfigurasi Sistem Lama, Authlib, Login/Logout, Utilitas SAMA) ...
# -------------------------
# KONFIGURASI SISTEM LAMA (TETAP SAMA)
# -------------------------
DATASET_DIR = 'dataset'
MODEL_DIR = 'models'
INITIAL_ELO = 1500
FEATURE_COLUMNS = [
    'AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5',
    'HomeTeamElo', 'AwayTeamElo', 'EloDifference',
    'Home_AvgGoalsScored', 'Home_AvgGoalsConceded', 'Home_Wins', 'Home_Draws', 'Home_Losses',
    'Away_AvgGoalsScored', 'Away_AvgGoalsConceded', 'Away_Wins', 'Away_Draws', 'Away_Losses',
    'HTH_HomeWins', 'HTH_AwayWins', 'HTH_Draws',
    'HTH_AvgHomeGoals', 'HTH_AvgAwayGoals'
]

# -------------------------
# KONFIGURASI AUTHLIB (BARU)
# -------------------------
oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ==========================================================
# --- LOGIN / LOGOUT (BARU) ---
# ==========================================================

@app.route('/login', methods=['GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home_page'))
    return render_template('login.html')

@app.route('/auth/google')
def auth_google():
    redirect_uri = url_for('auth_callback', _external=True)
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)


@app.route('/auth/callback')
def auth_callback():
    try:
        token = oauth.google.authorize_access_token()
        nonce = session.pop('nonce', None)
        if not nonce:
            raise Exception("Nonce tidak ditemukan di session. Coba login lagi.")

        user_info = oauth.google.parse_id_token(token, nonce=nonce)

    except Exception as e:
        flash(f"Login via Google gagal: {str(e)}", "danger")
        return redirect(url_for('login'))

    user = User.query.filter_by(google_id=user_info['sub']).first()

    if not user:
        user_role = 'user'
        if user_info['email'] == app.config['ADMIN_EMAIL']:
            user_role = 'admin'
        user = User(
            google_id=user_info['sub'],
            email=user_info['email'],
            name=user_info['name'],
            role=user_role
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)

    flash("Login berhasil!", "success")
    return redirect(url_for('home_page'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for('login'))


# ==========================================================
# UTILITAS (tidak diubah)
# ==========================================================
def pretty_league_name(file_name):
    name = file_name.replace('dataset_', '').replace('.csv', '')
    name = name.replace('_1', '')
    special_cases = {
        'seriea': 'Serie A',
        'laliga': 'La Liga',
        'premierleague': 'Premier League',
        'bundesliga': 'Bundesliga',
        'ligue1': 'Ligue 1'
    }
    key = name.lower().replace('_', '')
    return special_cases.get(key, name.replace('_', ' ').title())

def file_name_from_pretty(league_display):
    league_lower = league_display.lower().replace(' ', '')
    files = glob.glob(os.path.join(DATASET_DIR, '*.csv'))
    for f in files:
        fname = os.path.splitext(os.path.basename(f))[0].lower().replace('_', '')
        if league_lower in fname:
            return os.path.splitext(os.path.basename(f))[0]
    return league_lower

def list_leagues():
    files = glob.glob(os.path.join(DATASET_DIR, '*.csv'))
    return [pretty_league_name(os.path.splitext(os.path.basename(p))[0]) for p in files]

def load_league_dataset_by_name(league_display):
    league_lower = league_display.lower().replace(' ', '')
    files = glob.glob(os.path.join(DATASET_DIR, '*.csv'))
    matched_file = None
    for f in files:
        fname = os.path.splitext(os.path.basename(f))[0].lower().replace('_', '')
        if league_lower in fname:
            matched_file = f
            break
    if not matched_file:
        print("Available dataset files:", [os.path.basename(f) for f in files])
        raise FileNotFoundError(f"Dataset '{league_display}' tidak ditemukan di server.")
    df = pd.read_csv(matched_file)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df

# ==========================================================
# RIWAYAT PREDIKSI PER USER (Tetap menggunakan DB)
# ==========================================================
def add_prediction_to_history(prediction_dict):
    if not current_user.is_authenticated: # Hanya simpan jika login
        return
    try:
        new_history = PredictionHistory(
            user_id = current_user.id,
            league = prediction_dict.get('league'),
            home_team = prediction_dict.get('home_team'),
            away_team = prediction_dict.get('away_team'),
            prediction_data = prediction_dict.get('prediction')
        )
        db.session.add(new_history)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Gagal menyimpan riwayat ke DB: {e}")

@app.route('/api/history', methods=['GET'])
@login_required # <-- API ini tetap butuh login
def api_history():
    histories_query = PredictionHistory.query.filter_by(user_id=current_user.id)\
                                           .order_by(PredictionHistory.timestamp.desc())\
                                           .limit(20).all()
    histories_query.reverse()
    history_list = []
    for item in histories_query:
        history_list.append({
            'league': item.league,
            'home_team': item.home_team,
            'away_team': item.away_team,
            'prediction': item.prediction_data,
            'timestamp': item.timestamp.isoformat()
        })
    return jsonify({'status':'ok','history': history_list})

@app.route('/api/clear_history', methods=['POST'])
@login_required # <-- API ini tetap butuh login
def api_clear_history():
    try:
        PredictionHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'status':'ok','message':'Riwayat dibersihkan'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status':'error','message': f'Gagal membersihkan riwayat: {str(e)}'}), 500

# ==========================================================
# FITUR OTOMATIS & HITUNG STATISTIK (tidak diubah)
# ==========================================================
def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
def recent_stats_for_team(df, team, window=5):
    mask = (df['HomeTeam'] == team) | (df['AwayTeam'] == team)
    team_games = df[mask].sort_values('Date', ascending=False) if 'Date' in df.columns else df[mask]
    if team_games.empty:
        return {'AvgGoalsScored': 0, 'AvgGoalsConceded': 0, 'Wins': 0, 'Draws': 0, 'Losses': 0}
    recent = team_games.head(window)
    def gs(row): return row['FTHG'] if row['HomeTeam']==team else row['FTAG']
    def gc(row): return row['FTAG'] if row['HomeTeam']==team else row['FTHG']
    scored = recent.apply(gs, axis=1)
    conceded = recent.apply(gc, axis=1)
    def result(row):
        h,a = (row['FTHG'],row['FTAG']) if row['HomeTeam']==team else (row['FTAG'],row['FTHG'])
        return 'W' if h>a else 'D' if h==a else 'L'
    res = recent.apply(result, axis=1)
    return {
        'AvgGoalsScored': float(scored.mean()),
        'AvgGoalsConceded': float(conceded.mean()),
        'Wins': int((res=='W').sum()),
        'Draws': int((res=='D').sum()),
        'Losses': int((res=='L').sum())
    }
def h2h_stats(df, home_team, away_team, window=5):
    mask = ((df['HomeTeam']==home_team)&(df['AwayTeam']==away_team)) | ((df['HomeTeam']==away_team)&(df['AwayTeam']==home_team))
    hth = df[mask].sort_values('Date', ascending=False).head(window)
    hth_home_wins=hth_away_wins=hth_draws=0
    home_goals=[]; away_goals=[]
    for _, row in hth.iterrows():
        if row['HomeTeam']==home_team: h_goals,a_goals=row['FTHG'],row['FTAG']
        else: h_goals,a_goals=row['FTAG'],row['FTHG']
        home_goals.append(h_goals); away_goals.append(a_goals)
        if h_goals>a_goals: hth_home_wins+=1
        elif h_goals<a_goals: hth_away_wins+=1
        else: hth_draws+=1
    avg_home_goals = float(np.mean(home_goals)) if home_goals else 0
    avg_away_goals = float(np.mean(away_goals)) if away_goals else 0
    return {'HTH_HomeWins':hth_home_wins,'HTH_AwayWins':hth_away_wins,'HTH_Draws':hth_draws,
            'HTH_AvgHomeGoals':avg_home_goals,'HTH_AvgAwayGoals':avg_away_goals}
def compute_features_from_dataset(df, home_team, away_team, window=5):
    last_home_elo=last_away_elo=INITIAL_ELO
    if 'HomeTeamElo' in df.columns and 'AwayTeamElo' in df.columns:
        tmp_h=df[(df['HomeTeam']==home_team)|(df['AwayTeam']==home_team)]
        if not tmp_h.empty:
            row=tmp_h.sort_values('Date', ascending=False).iloc[0]
            last_home_elo=row['HomeTeamElo'] if row['HomeTeam']==home_team else row['AwayTeamElo']
        tmp_a=df[(df['HomeTeam']==away_team)|(df['AwayTeam']==away_team)]
        if not tmp_a.empty:
            row=tmp_a.sort_values('Date', ascending=False).iloc[0]
            last_away_elo=row['HomeTeamElo'] if row['HomeTeam']==away_team else row['AwayTeamElo']
    home_stats=recent_stats_for_team(df, home_team)
    away_stats=recent_stats_for_team(df, away_team)
    hth=h2h_stats(df, home_team, away_team, window)
    return {
        'AvgH':'','AvgD':'','AvgA':'','Avg>2.5':'','Avg<2.5':'',
        'HomeTeamElo':last_home_elo,'AwayTeamElo':last_away_elo,
        'EloDifference':last_home_elo-last_away_elo,
        'Home_AvgGoalsScored':home_stats['AvgGoalsScored'],
        'Home_AvgGoalsConceded':home_stats['AvgGoalsConceded'],
        'Home_Wins':home_stats['Wins'],'Home_Draws':home_stats['Draws'],'Home_Losses':home_stats['Losses'],
        'Away_AvgGoalsScored':away_stats['AvgGoalsScored'],
        'Away_AvgGoalsConceded':away_stats['AvgGoalsConceded'],
        'Away_Wins':away_stats['Wins'],'Away_Draws':away_stats['Draws'],'Away_Losses':away_stats['Losses'],
        'HTH_HomeWins':hth['HTH_HomeWins'],'HTH_AwayWins':hth['HTH_AwayWins'],'HTH_Draws':hth['HTH_Draws'],
        'HTH_AvgHomeGoals':hth['HTH_AvgHomeGoals'],'HTH_AvgAwayGoals':hth['HTH_AvgAwayGoals']
    }
def format_float_clean(number):
    """
    Membulatkan angka ke 2 desimal, lalu mengkonversinya menjadi string
    dan menghilangkan nol di akhir yang tidak perlu.
    Contoh: 2.200 -> '2.2', 3.0 -> '3', 1.234 -> '1.23'
    """
    if number is None or pd.isna(number) or str(number).strip() == '':
        return ""
    
    # Pastikan input adalah float, lalu bulatkan ke 2 desimal
    try:
        rounded_num = round(float(number), 2)
        # Menggunakan format :g untuk representasi desimal paling ringkas
        return f"{rounded_num:g}" 
    except (ValueError, TypeError):
        return str(number) # Kembalikan sebagai string jika bukan angka
        
def update_elo_and_features(df_existing, df_new, window=5, K=30, initial_elo=1500):
    # -----------------------------------------------------------------
    # 🟢 PERBAIKAN 1 (MENGATASI TypeError): Pastikan 'Date' bertipe datetime
    # -----------------------------------------------------------------
    if 'Date' in df_existing.columns:
        df_existing['Date'] = pd.to_datetime(df_existing['Date'], errors='coerce')
    if 'Date' in df_new.columns:
        df_new['Date'] = pd.to_datetime(df_new['Date'], errors='coerce')
    # -----------------------------------------------------------------

    # Penggabungan dan pengurutan (sekarang harusnya tidak error)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True).sort_values('Date').reset_index(drop=True)
    
    elo = {}
    new_rows = []
    
    for idx, row in df_combined.iterrows():
        home, away = row['HomeTeam'], row['AwayTeam']
        h_elo = elo.get(home, initial_elo)
        a_elo = elo.get(away, initial_elo)
        
        # Perhitungan Expected Score ELO
        E_h = 1/(1+10**((a_elo-h_elo)/400))
        E_a = 1-E_h
        
        # Hasil Akhir Pertandingan
        if row['FTHG']>row['FTAG']: S_h,S_a=1,0
        elif row['FTHG']<row['FTAG']: S_h,S_a=0,1
        else: S_h,S_a=0.5,0.5
        
        # Pembaruan ELO
        h_elo_new=h_elo+K*(S_h-E_h)
        a_elo_new=a_elo+K*(S_a-E_a)
        elo[home],elo[away]=h_elo_new,a_elo_new
        
        # Hitung Fitur Berdasarkan Data MASA LALU (sebelum pertandingan saat ini)
        df_past=df_combined.iloc[:idx]
        home_stats=recent_stats_for_team(df_past, home, window)
        away_stats=recent_stats_for_team(df_past, away, window)
        
        # Statistik Head-to-Head
        hth_mask=((df_past['HomeTeam']==home)&(df_past['AwayTeam']==away))|((df_past['HomeTeam']==away)&(df_past['AwayTeam']==home))
        hth=df_past[hth_mask].sort_values('Date', ascending=False).head(window)
        hth_home_wins=hth_away_wins=hth_draws=0
        
        if not hth.empty:
            for _, r in hth.iterrows():
                if r['HomeTeam']==home:
                    if r['FTHG']>r['FTAG']: hth_home_wins+=1
                    elif r['FTHG']<r['FTAG']: hth_away_wins+=1
                    else: hth_draws+=1
            hth_avg_home_goals=float(hth['FTHG'].mean())
            hth_avg_away_goals=float(hth['FTAG'].mean())
        else: hth_avg_home_goals=hth_avg_away_goals=0

        row_full = row.copy()

        # -----------------------------------------------------------------
        # 🟢 PERBAIKAN 2: Menyalin nilai Odds dari data CSV baru
        # -----------------------------------------------------------------
        odds_values = {}
        # Kolom odds yang harus disalin dari input CSV
        odds_cols = ['AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5']
        
        for col in odds_cols:
            # Cek apakah kolom ada di baris dan bukan NaN/None. Jika ada, salin nilainya.
            # Jika tidak ada, biarkan kosong (sesuai format yang diharapkan)
            if col in row and pd.notna(row[col]):
                odds_values[col] = row[col]
            else:
                odds_values[col] = ''
        # -----------------------------------------------------------------
        
        row_full.update({
            'HomeTeamElo':h_elo_new,'AwayTeamElo':a_elo_new,'EloDifference':h_elo_new-a_elo_new,
            'Home_AvgGoalsScored':home_stats['AvgGoalsScored'],'Home_AvgGoalsConceded':home_stats['AvgGoalsConceded'],
            'Home_Wins':home_stats['Wins'],'Home_Draws':home_stats['Draws'],'Home_Losses':home_stats['Losses'],
            'Away_AvgGoalsScored':away_stats['AvgGoalsScored'],'Away_AvgGoalsConceded':away_stats['AvgGoalsConceded'],
            'Away_Wins':away_stats['Wins'],'Away_Draws':away_stats['Draws'],'Away_Losses':away_stats['Losses'],
            'HTH_HomeWins':hth_home_wins,'HTH_AwayWins':hth_away_wins,'HTH_Draws':hth_draws,
            'HTH_AvgHomeGoals':hth_avg_home_goals,'HTH_AvgAwayGoals':hth_avg_away_goals,
            
        })

        # Hanya kembalikan baris yang BARU diunggah (idx >= len(df_existing))
        if idx >= len(df_existing):
            new_rows.append(row_full)
            
    return pd.DataFrame(new_rows)

# ==========================================================
# ROUTES HALAMAN PREDIKSI (DIUBAH - login tidak wajib)
# ==========================================================
@app.route('/')
def home_page():
    return render_template('home.html')

@app.route('/index')
# @login_required # <-- DIHAPUS
def index():
    leagues=list_leagues()
    return render_template('index.html', leagues=leagues)

@app.route('/api/leagues')
# Rute ini boleh publik
def api_leagues():
    files = glob.glob(os.path.join(DATASET_DIR, '*.csv'))
    leagues=[pretty_league_name(os.path.splitext(os.path.basename(f))[0]) for f in files]
    return jsonify({'status':'ok','leagues':leagues})

@app.route('/stats')
# Rute ini boleh publik
def stats_page():
    return render_template('stats.html')

@app.route('/api/team_stats', methods=['POST'])
# @login_required # <-- DIHAPUS
def api_team_stats():
    body=request.json or {}
    league=body.get('league')
    team=body.get('team')
    if not all([league,team]): return jsonify({'status':'error','message':'league and team required'}),400
    try: df=load_league_dataset_by_name(league)
    except FileNotFoundError as e: return jsonify({'status':'error','message':str(e)}),404
    stats=recent_stats_for_team(df, team)
    last_elo=None
    if 'HomeTeamElo' in df.columns and 'AwayTeamElo' in df.columns:
        tmp=df[(df['HomeTeam']==team)|(df['AwayTeam']==team)]
        if not tmp.empty:
            row=tmp.sort_values('Date', ascending=False).iloc[0]
            last_elo=row['HomeTeamElo'] if row['HomeTeam']==team else row['AwayTeamElo']
    return jsonify({'status':'ok','stats':{'recent':stats,'last_elo':last_elo}})

@app.route('/api/teams')
# @login_required # <-- DIHAPUS
def api_teams():
    league=request.args.get('league')
    if not league: return jsonify({'status':'error','message':'parameter league diperlukan'}),400
    try:
        df=load_league_dataset_by_name(league)
        teams=sorted(set(df['HomeTeam']).union(set(df['AwayTeam'])))
        return jsonify({'status':'ok','teams':teams})
    except FileNotFoundError as e:
        return jsonify({'status':'error','message':str(e)}),404

@app.route('/api/features', methods=['POST'])
# @login_required # <-- DIHAPUS
def api_features():
    body=request.json or {}
    league=body.get('league'); home=body.get('home'); away=body.get('away')
    if not all([league,home,away]): return jsonify({'status':'error','message':'league, home, away dibutuhkan'}),400
    df=load_league_dataset_by_name(league)
    feats=compute_features_from_dataset(df, home, away)
    return jsonify({'status':'ok','features':feats})

@app.route('/api/predict', methods=['POST'])
# @login_required # <-- DIHAPUS
def api_predict():
    try:
        body=request.json or {}
        league=body.get('league')
        features=body.get('features')
        home_team = body.get('home_team')
        away_team = body.get('away_team')

        if not all([league, features, home_team, away_team]):
            return jsonify({'status':'error','message':'Data liga, fitur, dan tim diperlukan'}),400

        league_dir=os.path.join(MODEL_DIR, league.lower().replace(' ','_'))
        model_hda=joblib.load(os.path.join(league_dir,'model_hda.pkl'))
        model_ou25=joblib.load(os.path.join(league_dir,'model_ou25.pkl'))
        model_btts=joblib.load(os.path.join(league_dir,'model_btts.pkl'))
        scaler=joblib.load(os.path.join(league_dir,'scaler.pkl'))
        le_ftr=joblib.load(os.path.join(league_dir,'le_ftr.pkl'))
        le_ou=joblib.load(os.path.join(league_dir,'le_ou.pkl'))
        le_btts=joblib.load(os.path.join(league_dir,'le_btts.pkl'))
        df_features=pd.DataFrame([features])[FEATURE_COLUMNS]
        X_scaled=scaler.transform(df_features)
        probs_hda=model_hda.predict_proba(X_scaled)[0]
        probs_ou=model_ou25.predict_proba(X_scaled)[0]
        probs_btts=model_btts.predict_proba(X_scaled)[0]
        probs_hda_dict={le_ftr.classes_[i]:float(probs_hda[i]) for i in range(len(probs_hda))}
        probs_ou_dict={le_ou.classes_[i]:float(probs_ou[i]) for i in range(len(probs_ou))}
        probs_btts_dict={le_btts.classes_[i]:float(probs_btts[i]) for i in range(len(probs_btts))}
        pred_hda=le_ftr.classes_[np.argmax(probs_hda)]
        pred_ou=le_ou.classes_[np.argmax(probs_ou)]
        pred_btts=le_btts.classes_[np.argmax(probs_btts)]
        result = {
            'HDA':{'label':pred_hda,'probs':probs_hda_dict},
            'OU25':{'label':pred_ou,'probs':probs_ou_dict},
            'BTTS':{'label':pred_btts,'probs':probs_btts_dict}
        }

        # Tetap panggil fungsi ini, tapi fungsi ini akan mengecek login
        add_prediction_to_history({
            'league': league,
            'home_team': home_team,
            'away_team': away_team,
            'prediction': result
        })

        return jsonify({'status':'ok','prediction':result})
    except Exception as e: return jsonify({'status':'error','message':str(e)}),400

# ==========================================================
# ROUTES HALAMAN ADD DATA (TETAP DIPROTEKSI)
# ==========================================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Hanya admin yang dapat mengakses halaman ini.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/add_data')
@login_required
@admin_required
def add_data_page():
    leagues=list_leagues()
    return render_template('add_data.html', leagues=leagues)

@app.route('/api/upload_csv', methods=['POST'])
@login_required
@admin_required
def api_upload_csv():
    league=request.form.get('league'); file=request.files.get('file')
    if not all([league,file]): return jsonify({'status':'error','message':'Liga dan file CSV diperlukan'}),400
    filename=secure_filename(file.filename)
    df_new=pd.read_csv(file)
    df_existing=load_league_dataset_by_name(league)
    mask_new=~df_new.apply(lambda r: ((df_existing['Date']==r['Date']) & (df_existing['HomeTeam']==r['HomeTeam']) & (df_existing['AwayTeam']==r['AwayTeam'])).any(), axis=1)
    df_new_only=df_new[mask_new].copy()
    if df_new_only.empty: return jsonify({'status':'ok','message':'Tidak ada pertandingan baru'}),200
    
    # 1. Hitung fitur ELO dan lainnya (Data masih berupa angka/float)
    df_new_full=update_elo_and_features(df_existing, df_new_only)

    # 2. Buat salinan DataFrame untuk pemformatan output JSON
    df_output = df_new_full.copy()
    
    # -----------------------------------------------------------------
    # 🟢 PERBAIKAN UTAMA: Pemformatan Tanggal ke YYYY-MM-DD HH:MM:SS
    # -----------------------------------------------------------------
    if 'Date' in df_output.columns:
        # Pastikan kolom Date bertipe datetime sebelum diformat
        df_output['Date'] = pd.to_datetime(df_output['Date'], errors='coerce')
        # Terapkan pemformatan string yang diinginkan
        df_output['Date'] = df_output['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 3. Pemformatan Angka (untuk menghilangkan nol di belakang, seperti 2.20 -> 2.2)
    cols_to_format = list(df_output.columns)
    cols_skip = ['HomeTeam', 'AwayTeam', 'FTR', 'HTR', 'Div', 'Date'] # Tambahkan 'Date' ke skip
    
    for col in cols_to_format:
        # Cek tipe data: harus numerik DAN BUKAN kolom yang dilewati
        if col not in cols_skip and pd.api.types.is_numeric_dtype(df_output[col]):
            df_output[col] = df_output[col].apply(format_float_clean)
            
    # 4. Mengembalikan data yang sudah diformat ke string
    return jsonify({'status':'ok','matches':df_output.to_dict(orient='records')})

@app.route('/api/save_new_matches', methods=['POST'])
@login_required
@admin_required
def api_save_new_matches():
    league=request.json.get('league'); matches=request.json.get('matches')
    df_existing=load_league_dataset_by_name(league)
    df_new=pd.DataFrame(matches)
    df_combined=pd.concat([df_existing, df_new], ignore_index=True)
    league_file=file_name_from_pretty(league)
    path=os.path.join(DATASET_DIR, f"{league_file}.csv")
    df_combined.to_csv(path, index=False)
    return jsonify({'status':'ok','message':'Pertandingan baru berhasil disimpan'})

# ==========================================================
# MAIN
# ==========================================================
if __name__ == '__main__':
    os.makedirs(DATASET_DIR, exist_ok=True)
    with app.app_context():
        db.create_all()
        print("Database telah dicek/dibuat.")
    # Gunakan host dan port sesuai Render (port bisa di-set via Render)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))