import pandas as pd
import os

# --- 1. Konfigurasi Nama File ---
# Ganti ini dengan nama file Anda yang sebenarnya
nama_file_1 = 'datasetPrediksi/belanda/N1-1.csv'
nama_file_2 = 'datasetPrediksi/belanda/N1-2.csv'
nama_file_3 = 'datasetPrediksi/belanda/N1.csv'
nama_file_output = 'datasetPrediksi/belanda/N.csv'

# --- Cek apakah file ada ---
if not os.path.exists(nama_file_1):
    print(f"Error: File '{nama_file_1}' tidak ditemukan.")
    exit()
if not os.path.exists(nama_file_2):
    print(f"Error: File '{nama_file_2}' tidak ditemukan.")
    exit()
if not os.path.exists(nama_file_3):
    print(f"Error: File '{nama_file_3}' tidak ditemukan.")
    exit()

print(f"Membaca file: {nama_file_1}...")
# Baca semua data sebagai string (teks) agar format aslinya tidak rusak
df1 = pd.read_csv(nama_file_1, dtype=str)

print(f"Membaca file: {nama_file_2}...")
df2 = pd.read_csv(nama_file_2, dtype=str)

print(f"Membaca file: {nama_file_3}...")
df3 = pd.read_csv(nama_file_3, dtype=str)

# --- 2. Menggabungkan Dua DataFrame ---
print("Menggabungkan kedua file...")
# ignore_index=True akan membuat ulang index dari 0, 1, 2, ...
df_combined = pd.concat([df1, df2, df3], ignore_index=True)

# --- 3. Membuat Kunci Urutan (Sort Key) ---
# Kita buat kolom sementara untuk pengurutan.
# Ini menggabungkan 'Date' dan 'Time' agar urutannya 100% akurat.
# Format '%d/%m/%Y %H:%M' sesuai data Anda (cth: 11/08/2023 19:00)
print("Membuat kunci pengurutan tanggal dan waktu...")
try:
    df_combined['__temp_sort_key__'] = pd.to_datetime(
        df_combined['Date'] + ' ' + df_combined['Time'], 
        format='%d/%m/%Y %H:%M',
        errors='coerce' # Jika ada tanggal/waktu yang salah, jadikan 'NaT'
    )
except KeyError:
    print("Kolom 'Time' tidak ditemukan. Mengurutkan hanya berdasarkan 'Date'.")
    df_combined['__temp_sort_key__'] = pd.to_datetime(
        df_combined['Date'], 
        format='%d/%m/%Y',
        errors='coerce'
    )

# Cek jika ada data yang gagal di-parse
if df_combined['__temp_sort_key__'].isna().any():
    print("Peringatan: Beberapa baris memiliki format tanggal/waktu yang salah dan mungkin tidak terurut dengan benar.")

# --- 4. Mengurutkan Berdasarkan Kunci ---
print("Mengurutkan data...")
# 'inplace=True' memodifikasi df_combined secara langsung
# 'na_position='last'' menempatkan baris yang error di bagian akhir
df_combined.sort_values(by='__temp_sort_key__', inplace=True, na_position='last')

# --- 5. Menghapus Kunci Urutan ---
# Hapus kolom sementara agar file output memiliki kolom yang sama persis
# dengan file input Anda.
df_combined.drop(columns=['__temp_sort_key__'], inplace=True)

# --- 6. Menyimpan ke File CSV Baru ---
# 'index=False' agar nomor baris dari pandas tidak ikut disimpan
df_combined.to_csv(nama_file_output, index=False)

print(f"\n✅ Berhasil! File gabungan telah disimpan sebagai: {nama_file_output}")