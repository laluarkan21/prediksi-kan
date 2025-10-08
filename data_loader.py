import pandas as pd
import os

# Fungsi "penerjemah tanggal cerdas" untuk menangani format yang berbeda-beda
def parse_mixed_date(date_str):
    """Mencoba beberapa format tanggal umum satu per satu."""
    if not isinstance(date_str, str):
        return pd.NaT
    # Coba format DD/MM/YYYY (misal: 24/08/2019)
    try:
        return pd.to_datetime(date_str, format='%d/%m/%Y')
    except ValueError:
        # Jika gagal, coba format DD/MM/YY (misal: 24/08/19)
        try:
            return pd.to_datetime(date_str, format='%d/%m/%y')
        except ValueError:
            # Jika masih gagal, biarkan pandas menebak secara otomatis
            return pd.to_datetime(date_str, errors='coerce', dayfirst=True)

def load_all_leagues_separately(folder_path='dataset'):
    """
    Memuat semua file CSV dengan fungsi parsing tanggal yang tangguh.
    """
    league_data = {}
    
    try:
        csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        if not csv_files:
            print(f"Error: Tidak ada file .csv yang ditemukan di folder '{folder_path}'")
            return None
    except FileNotFoundError:
        print(f"Error: Folder '{folder_path}' tidak ditemukan.")
        return None

    print(f"Ditemukan {len(csv_files)} file dataset: {', '.join(csv_files)}")

    for csv_file in csv_files:
        file_path = os.path.join(folder_path, csv_file)
        
        try:
            df = pd.read_csv(file_path, engine='python', on_bad_lines='warn')
        except Exception as e:
            print(f"Gagal membaca {csv_file}. Error: {e}")
            continue

        liga_name = os.path.splitext(csv_file)[0]
        
        numeric_cols = [
            'FTHG', 'FTAG', 'HS', 'AS', 'B365H', 'B365D', 'B365A', 'Avg>2.5', 'Avg<2.5',
            'AHh', 'AvgAHH', 'AvgAHA', 'BbAHh', 'BbAvAHH', 'BbAvAHA'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df.fillna(0, inplace=True)
        
        # Gunakan fungsi parsing cerdas
        df['Date'] = df['Date'].apply(parse_mixed_date)
        
        df.dropna(subset=['Date'], inplace=True)
        df = df.sort_values('Date').reset_index(drop=True)

        # Menyeragamkan nama kolom handicap
        rename_map = {'BbAHh': 'AHh', 'BbAvAHH': 'AvgAHH', 'BbAvAHA': 'AvgAHA'}
        df.rename(columns=rename_map, inplace=True)
        df = df.loc[:, ~df.columns.duplicated()]
        for col in ['AHh', 'AvgAHH', 'AvgAHA']:
            if col not in df.columns:
                df[col] = 0
        
        league_data[liga_name] = df
        print(f"  - Berhasil memuat {df.shape[0]} baris untuk liga '{liga_name}'.")
        
    return league_data