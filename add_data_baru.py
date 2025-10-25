import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# ==========================================================
# KONSTANTA (DARI app.py)
# ==========================================================
INITIAL_ELO = 1500
K_FACTOR = 30  # Faktor K untuk Elo
WINDOW = 5     # Jendela untuk statistik 5 pertandingan terakhir

# ==========================================================
# FUNGSI HELPER (Disalin dari app.py)
# ==========================================================
def recent_stats_for_team(df_past, team, window=WINDOW):
    """
    Menghitung statistik 'window' (5) pertandingan terakhir untuk satu tim.
    Logika ini disalin langsung dari app.py Anda (fungsi recent_stats_for_team).
    PENTING: df_past HARUS berisi data SEBELUM pertandingan saat ini dan sudah diurutkan.
    """
    mask = (df_past['HomeTeam'] == team) | (df_past['AwayTeam'] == team)
    
    # Ambil semua game tim (df_past sudah diurutkan), ambil 'window' terakhir
    # Menggunakan tail() karena df_past berisi data SEBELUM pertandingan saat ini
    recent = df_past[mask].tail(window) 
    
    if recent.empty: # Cek jika recent kosong
        return {'AvgGoalsScored': 0, 'AvgGoalsConceded': 0, 'Wins': 0, 'Draws': 0, 'Losses': 0}
    
    # Fungsi helper untuk skor (relatif terhadap 'team')
    def gs(row): return row['FTHG'] if row['HomeTeam']==team else row['FTAG']
    def gc(row): return row['FTAG'] if row['HomeTeam']==team else row['FTHG']
    
    # --- PERBAIKAN: Pastikan kolom skor ada sebelum apply ---
    scored = pd.Series(dtype=float)
    conceded = pd.Series(dtype=float)
    if 'FTHG' in recent.columns and 'FTAG' in recent.columns:
        scored = recent.apply(gs, axis=1)
        conceded = recent.apply(gc, axis=1)
    
    # Fungsi helper untuk hasil (relatif terhadap 'team')
    def result(row):
        h,a = (row['FTHG'],row['FTAG']) if row['HomeTeam']==team else (row['FTAG'],row['FTHG'])
        return 'W' if h>a else 'D' if h==a else 'L'
    
    res = recent.apply(result, axis=1) if 'FTHG' in recent.columns and 'FTAG' in recent.columns else pd.Series(dtype=str)
    
    return {
        'AvgGoalsScored': float(scored.mean()) if not scored.empty else 0,
        'AvgGoalsConceded': float(conceded.mean()) if not conceded.empty else 0,
        'Wins': int((res=='W').sum()),
        'Draws': int((res=='D').sum()),
        'Losses': int((res=='L').sum())
    }

# ==========================================================
# FUNGSI UTAMA GENERATE FITUR
# ==========================================================

def generate_features_for_dataset(input_csv_path, output_csv_path):
    """
    Memproses seluruh file CSV dan menghasilkan fitur untuk setiap pertandingan
    berdasarkan logika dari app.py (update_elo_and_features), HANYA menggunakan Date.
    """
    
    print(f"Membaca dataset dari: {input_csv_path}...")
    try:
        # Baca CSV tanpa dtype khusus untuk Time
        df = pd.read_csv(input_csv_path)
    except FileNotFoundError:
        print(f"Error: File tidak ditemukan di {input_csv_path}")
        return
    except Exception as e:
        print(f"Error saat membaca CSV: {e}")
        return

    # --- 1. Persiapan & Pembersihan Data ---
    print("Membersihkan dan mengurutkan data...")
    
    # Konversi kolom skor ke numerik
    score_cols = ['FTHG', 'FTAG']
    for col in score_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            print(f"Peringatan: Kolom skor '{col}' tidak ditemukan di CSV.")
            if col == 'FTHG': df['FTHG'] = 0
            if col == 'FTAG': df['FTAG'] = 0

    # Buat kolom datetime HANYA dari 'Date' untuk pengurutan
    print("  Menggunakan 'Date' untuk pengurutan.")
    date_formats_to_try = ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y'] # Tambahkan format lain jika perlu
    parsed_successfully = False
    for fmt in date_formats_to_try:
        try:
            # Coba parse dengan format spesifik
            temp_dt = pd.to_datetime(df['Date'], format=fmt, errors='coerce')
            # Jika mayoritas berhasil, gunakan format ini
            if temp_dt.notna().sum() > len(df) / 2:
                 df['datetime'] = temp_dt
                 print(f"  Format tanggal terdeteksi: {fmt}")
                 parsed_successfully = True
                 break
        except Exception:
            continue # Coba format berikutnya

    if not parsed_successfully:
         print("  Tidak dapat mendeteksi format tanggal utama. Mencoba parsing otomatis...")
         # Coba parsing otomatis, prioritaskan dayfirst=True jika ambigu
         df['datetime'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True) 
         if df['datetime'].isna().all():
              print("Error: Gagal mem-parse kolom 'Date'. Pastikan format tanggal konsisten.")
              return

    # Hapus baris yang tanggalnya tidak valid dan urutkan
    original_rows = len(df)
    df.dropna(subset=['datetime'], inplace=True)
    if len(df) < original_rows:
        print(f"  Peringatan: {original_rows - len(df)} baris dihapus karena format tanggal tidak valid.")

    df.sort_values(by='datetime', inplace=True)
    df.reset_index(drop=True, inplace=True) # <-- Penting!

    print(f"Total {len(df)} pertandingan akan diproses...")

    # --- 2. Tentukan Kolom yang Akan Disimpan ---
    # Kolom asli yang ingin disimpan (TANPA Time)
    cols_to_keep = [
        'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
        'AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5' 
    ]
    
    # Filter 'cols_to_keep' hanya untuk kolom yang benar-benar ada di file
    final_cols_to_keep = [col for col in cols_to_keep if col in df.columns]

    # --- 3. Inisialisasi ---
    elo = {}
    all_feature_rows = [] # List untuk menampung semua baris baru (dalam bentuk dict)

    # --- 4. Iterasi Perhitungan Fitur ---
    # (Logika disalin dari 'update_elo_and_features' di app.py)
    for idx, row in df.iterrows():
        
        # Tampilkan progres
        if (idx + 1) % 500 == 0:
            print(f"  ...memproses pertandingan {idx + 1}/{len(df)}")
            
        home, away = row['HomeTeam'], row['AwayTeam']
        
        # Ambil data historis HANYA SEBELUM pertandingan ini
        df_past = df.iloc[:idx]

        # --- a. Hitung Elo ---
        h_elo_pre = elo.get(home, INITIAL_ELO)
        a_elo_pre = elo.get(away, INITIAL_ELO)
        
        E_h = 1 / (1 + 10 ** ((a_elo_pre - h_elo_pre) / 400))
        E_a = 1 - E_h
        
        # Periksa apakah FTHG/FTAG ada sebelum menghitung skor Elo
        S_h, S_a = 0.5, 0.5 # Default draw jika skor tidak ada
        if 'FTHG' in row and 'FTAG' in row:
            if row['FTHG'] > row['FTAG']: S_h, S_a = 1, 0
            elif row['FTHG'] < row['FTAG']: S_h, S_a = 0, 1

        h_elo_new = h_elo_pre + K_FACTOR * (S_h - E_h)
        a_elo_new = a_elo_pre + K_FACTOR * (S_a - E_a)
        
        # Update Elo di dictionary untuk pertandingan BERIKUTNYA
        elo[home] = h_elo_new
        elo[away] = a_elo_new
        
        # --- b. Hitung Statistik Terbaru ---
        home_stats = recent_stats_for_team(df_past, home, window=WINDOW)
        away_stats = recent_stats_for_team(df_past, away, window=WINDOW)
        
        # --- c. Hitung Statistik H2H ---
        hth_mask = ((df_past['HomeTeam'] == home) & (df_past['AwayTeam'] == away)) | \
                   ((df_past['HomeTeam'] == away) & (df_past['AwayTeam'] == home))
        
        # Ambil 'window' (5) H2H terakhir (df_past sudah diurutkan berdasarkan datetime)
        hth = df_past[hth_mask].tail(WINDOW)
        
        hth_home_wins=hth_away_wins=hth_draws=0
        home_goals=[]; away_goals=[]
        
        if not hth.empty:
            for _, r in hth.iterrows():
                # Pastikan skor H2H ada
                fthg_h2h = r.get('FTHG', 0)
                ftag_h2h = r.get('FTAG', 0)

                # Tentukan skor relatif terhadap 'home' (tim tuan rumah saat ini)
                if r['HomeTeam'] == home: 
                    h_g, a_g = fthg_h2h, ftag_h2h
                else: 
                    h_g, a_g = ftag_h2h, fthg_h2h
                
                home_goals.append(h_g); away_goals.append(a_g)

                if h_g > a_g: hth_home_wins += 1
                elif h_g < a_g: hth_away_wins += 1
                else: hth_draws += 1
        
        hth_avg_home_goals = float(np.mean(home_goals)) if home_goals else 0
        hth_avg_away_goals = float(np.mean(away_goals)) if away_goals else 0

        # --- d. Buat Baris Output ---
        # 1. Ambil kolom-kolom asli yang ingin disimpan
        new_row_data = {col: row.get(col, None) for col in final_cols_to_keep}
        
        # --- Tambahkan kolom datetime sementara untuk formatting nanti ---
        new_row_data['datetime_obj'] = row['datetime'] 

        # 2. Tambahkan 18 fitur baru
        new_row_data.update({
            'HomeTeamElo': h_elo_new,
            'AwayTeamElo': a_elo_new,
            'EloDifference': h_elo_new - a_elo_new,
            
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
            
            'HTH_HomeWins': hth_home_wins,
            'HTH_AwayWins': hth_away_wins,
            'HTH_Draws': hth_draws,
            'HTH_AvgHomeGoals': hth_avg_home_goals,
            'HTH_AvgAwayGoals': hth_avg_away_goals
        })
        
        all_feature_rows.append(new_row_data)

    print("✅ Pemrosesan selesai.")
    
    # --- 5. Buat DataFrame Final ---
    final_df = pd.DataFrame(all_feature_rows)
    
    # Tentukan urutan kolom final (masukkan datetime_obj sementara)
    final_columns_order = final_cols_to_keep + ['datetime_obj'] + [ # Tambahkan datetime_obj
        'HomeTeamElo', 'AwayTeamElo', 'EloDifference',
        'Home_AvgGoalsScored', 'Home_AvgGoalsConceded', 'Home_Wins', 'Home_Draws', 'Home_Losses',
        'Away_AvgGoalsScored', 'Away_AvgGoalsConceded', 'Away_Wins', 'Away_Draws', 'Away_Losses',
        'HTH_HomeWins', 'HTH_AwayWins', 'HTH_Draws',
        'HTH_AvgHomeGoals', 'HTH_AvgAwayGoals'
    ]
    
    # Filter kolom final hanya yang ada di DataFrame
    final_columns_order = [col for col in final_columns_order if col in final_df.columns]
    
    # Atur ulang urutan kolom
    final_df = final_df[final_columns_order]

    # --- PEMBULATAN ---
    print("Membulatkan nilai fitur ke 2 desimal...")
    cols_to_round = [
        'HomeTeamElo', 'AwayTeamElo', 'EloDifference',
        'Home_AvgGoalsScored', 'Home_AvgGoalsConceded',
        'Away_AvgGoalsScored', 'Away_AvgGoalsConceded',
        'HTH_AvgHomeGoals', 'HTH_AvgAwayGoals'
    ]
    odd_cols_original = ['AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5']
    cols_to_round.extend([col for col in odd_cols_original if col in final_df.columns])

    for col in cols_to_round:
        if col in final_df.columns:
             final_df[col] = pd.to_numeric(final_df[col], errors='coerce')
             final_df[col] = final_df[col].round(2)
    # --- AKHIR PEMBULATAN ---

    # --- FORMAT TANGGAL OUTPUT ---
    print("Memformat kolom tanggal ke YYYY-MM-DD HH:MM:SS...")
    if 'datetime_obj' in final_df.columns:
        # Format kolom datetime_obj ke string yang diinginkan
        final_df['Date'] = final_df['datetime_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
        # Hapus kolom datetime_obj sementara
        final_df.drop(columns=['datetime_obj'], inplace=True)
    elif 'Date' in final_df.columns:
         # Jika datetime_obj tidak ada (seharusnya tidak terjadi), coba format kolom Date asli
         final_df['Date'] = pd.to_datetime(final_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    # --- AKHIR FORMAT TANGGAL ---


    # Simpan ke CSV
    final_df.to_csv(output_csv_path, index=False)
    print(f"\n🎉 Berhasil! Dataset dengan fitur lengkap telah disimpan ke:\n{output_csv_path}")

# ==========================================================
# UNTUK MENJALANKAN SKRIP
# ==========================================================
if __name__ == '__main__':
    
    # --- GANTI NAMA FILE INI ---
    INPUT_FILE = 'datasetPrediksi/belanda/N.csv'
    OUTPUT_FILE = 'dataset/dataset_Eredivisie_1.csv'
    # ---------------------------

    if not os.path.exists(INPUT_FILE):
        print(f"Error: File input '{INPUT_FILE}' tidak ditemukan.")
        print("Harap ubah nama 'INPUT_FILE' di dalam skrip ini.")
    else:
        # Jalankan fungsi utama
        generate_features_for_dataset(INPUT_FILE, OUTPUT_FILE)