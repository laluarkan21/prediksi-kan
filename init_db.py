# init_db.py
import os
# Pastikan Anda mengimpor app dan db dari file app.py Anda
from app import app, db

# Blok ini akan dijalankan satu kali saat deployment untuk membuat tabel
with app.app_context():
    # db.create_all() akan membuat tabel jika belum ada
    db.create_all()
    print("Database tables created/checked successfully.")