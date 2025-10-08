import os
import pandas as pd

# 1. Tentukan path ke folder tempat Anda menyimpan semua file CSV
# Ganti 'path/ke/folder/anda' dengan lokasi folder yang benar.
folder_path = 'dataset/serie A'

# 2. TULIS NAMA FILE YANG INGIN ANDA GABUNGKAN DI SINI
# Cukup tambahkan atau hapus nama file di dalam list di bawah ini.
# Pastikan nama filenya sama persis, termasuk ekstensi .csv
files_to_merge = [
    'italy-serie-a-2019-to-2020.csv',
    'italy-serie-a-2018-to-2019.csv',
    'italy-serie-a-2017-to-2018.csv',
    # Tambahkan nama file lain di baris baru jika perlu
]

# --- Jangan ubah kode di bawah ini ---

# Cek apakah folder ada
if not os.path.isdir(folder_path):
    print(f"Error: Folder tidak ditemukan di '{folder_path}'")
    print("Pastikan Anda sudah mengganti 'path/ke/folder/anda' dengan benar.")
else:
    print(f"Memproses {len(files_to_merge)} file yang dipilih...")

    # Buat list kosong untuk menampung data
    all_dataframes = []

    # Baca setiap file yang ada di dalam list files_to_merge
    for file_name in files_to_merge:
        file_path = os.path.join(folder_path, file_name)

        # Cek apakah file benar-benar ada sebelum dibaca
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, low_memory=False)
                all_dataframes.append(df)
                print(f"  - Berhasil membaca: {file_name}")
            except Exception as e:
                print(f"  - Gagal membaca {file_name}. Error: {e}")
        else:
            print(f"  - Peringatan: File '{file_name}' tidak ditemukan di folder.")

    # Gabungkan semua data menjadi satu
    if all_dataframes:
        merged_df = pd.concat(all_dataframes, ignore_index=True)

        # Simpan hasil gabungan ke file CSV baru
        output_filename = 'dataset_serieA.csv'
        merged_df.to_csv(output_filename, index=False)

        print(f"\n✅ Sukses! File yang dipilih telah digabungkan ke dalam '{output_filename}'")
        print(f"Total baris data gabungan: {len(merged_df)}")
    else:
        print("\nTidak ada file yang berhasil dibaca. Proses dibatalkan.")