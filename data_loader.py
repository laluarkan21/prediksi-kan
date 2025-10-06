import pandas as pd

def load_and_clean_data(file_path='dataset/dataset_pertandingan.csv'):
    """
    Memuat data dari file CSV, membersihkan tipe data, dan mengisinya.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' tidak ditemukan.")
        return None

    numeric_cols = [
        'FTHG', 'FTAG', 'HS', 'AS', 'B365H', 'B365D', 'B365A', 'Avg>2.5', 'Avg<2.5'
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df.fillna(0, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    df = df.sort_values('Date').reset_index(drop=True)
    
    print(f"Jumlah baris data awal yang dimuat dan dibersihkan: {df.shape[0]}")
    return df