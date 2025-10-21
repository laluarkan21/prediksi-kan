import pandas as pd
import os

def select_and_save_columns(input_file_path, output_file_path):
    """
    Memuat dataset, hanya memilih kolom yang diperlukan, dan menyimpannya ke file baru.
    
    Args:
        input_file_path (str): Jalur lengkap ke file CSV input (dataset asli).
        output_file_path (str): Jalur lengkap untuk menyimpan file CSV output yang baru.
    """
    
    # 1. Tentukan Kolom yang Diperlukan
    REQUIRED_COLUMNS = [
        'Date',
        'HomeTeam',
        'AwayTeam',
        'FTHG',
        'FTAG',
        'FTR',
        'AvgH',
        'AvgD',
        'AvgA',
        'Avg>2.5',
        'Avg<2.5'
    ]
    
    # 2. Muat Dataset
    print(f"Mencoba memuat file: {input_file_path}...")
    try:
        # Baca file CSV
        df = pd.read_csv(input_file_path)
    except FileNotFoundError:
        print(f"🚨 ERROR: File tidak ditemukan di jalur: {input_file_path}")
        return
    except Exception as e:
        print(f"🚨 ERROR saat memuat file: {e}")
        return
        
    # 3. Validasi dan Pilih Kolom
    
    # Cek apakah semua kolom yang diperlukan ada di dataset
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    
    if missing_cols:
        print(f"⚠️ PERINGATAN: Kolom berikut tidak ditemukan di dataset dan akan dilewati: {missing_cols}")
        
        # Filter kolom yang benar-benar ada
        existing_cols = [col for col in REQUIRED_COLUMNS if col in df.columns]
        df_selected = df[existing_cols].copy()
    else:
        # Ambil kolom yang diperlukan
        df_selected = df[REQUIRED_COLUMNS].copy()

    print(f"Dataset dimuat. Jumlah baris: {len(df)}. Jumlah kolom yang dipilih: {len(df_selected.columns)}")

    # 4. Simpan ke File Baru
    
    # Pastikan direktori output ada
    output_dir = os.path.dirname(output_file_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        df_selected.to_csv(output_file_path, index=False)
        print(f"✅ Berhasil! Dataset baru telah disimpan ke: {output_file_path}")
    except Exception as e:
        print(f"🚨 ERROR saat menyimpan file: {e}")

# ==========================================================
# KONFIGURASI PENGGUNAAN
# ==========================================================

# ➡️ GANTI NILAI INI SESUAI DENGAN LOKASI FILE ANDA

# 1. Tentukan jalur file input (dataset asli Anda)
INPUT_FILE = 'add_dataset/SP1.csv' # Contoh: 'dataset_bundesliga.csv'

# 2. Tentukan jalur file output (tempat data baru akan disimpan)
OUTPUT_FILE = 'add_dataset/spanyol.csv' 

if __name__ == "__main__":
    # Ganti path ini dengan file CSV yang sebenarnya
    select_and_save_columns(INPUT_FILE, OUTPUT_FILE)