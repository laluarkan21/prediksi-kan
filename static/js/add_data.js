document.addEventListener('DOMContentLoaded', async () => {
    // --- Inisialisasi DOM Elements ---
    const leagueSelect = document.getElementById('leagueSelect');
    const csvFileInput = document.getElementById('csvFile');
    const dataTableBody = document.querySelector('#dataTable tbody');
    const saveBtn = document.getElementById('saveBtn');
    const toggleBtn = document.getElementById('toggleThemeBtn'); // Tombol toggle
    const body = document.body;

    let selectedLeague = '';
    let newMatches = [];

    // --- Inisialisasi Firebase (Wajib ada jika menggunakan Canvas) ---
    // const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
    // const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};
    // const app = firebaseConfig ? initializeApp(firebaseConfig) : null;
    // const db = app ? getFirestore(app) : null;
    // const auth = app ? getAuth(app) : null;

    // --- Fungsi Helper ---
    function autoScrollTable() {
        const tableContainer = document.querySelector('.table-container');
        if (tableContainer) {
            tableContainer.scrollTop = tableContainer.scrollHeight;
        }
    }
    
    // ===== Mode Gelap / Terang =====
    // Default mode gelap
    body.classList.add('dark-mode');

    toggleBtn.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
    });


    // 1. Ambil daftar liga
    async function loadLeagues() {
        try {
            const res = await fetch('/api/leagues');
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const data = await res.json();
            
            if (data.status === 'ok') {
                data.leagues.forEach(league => {
                    const option = document.createElement('option');
                    option.value = league;
                    option.textContent = league;
                    leagueSelect.appendChild(option);
                });
            } else {
                console.error("Gagal memuat liga:", data.message);
            }
        } catch (error) {
            console.error('Fetch error during league load:', error);
            // Tambahkan opsi default jika gagal
            const option = document.createElement('option');
            option.textContent = 'Gagal memuat liga';
            option.disabled = true;
            leagueSelect.appendChild(option);
        }
    }

    await loadLeagues();

    leagueSelect.addEventListener('change', () => {
        selectedLeague = leagueSelect.value;
        dataTableBody.innerHTML = '';
        newMatches = [];
    });

    // 2. Proses CSV (Mengirim file langsung ke backend)
    csvFileInput.addEventListener('change', async (e) => {
        if (!selectedLeague) {
            alert('Pilih liga terlebih dahulu!');
            csvFileInput.value = '';
            return;
        }

        const file = e.target.files[0];
        if (!file) return;

        // Tampilkan indikator loading
        saveBtn.textContent = 'Memproses Data...';
        saveBtn.disabled = true;
        dataTableBody.innerHTML = '<tr><td colspan="30" class="text-center py-4">Memproses dan menghitung fitur otomatis di server...</td></tr>';
        
        // Buat FormData untuk mengirim file
        const formData = new FormData();
        formData.append('league', selectedLeague);
        formData.append('file', file);
        
        try {
            // Panggil API upload_csv
            const res = await fetch('/api/upload_csv', {
                method: 'POST',
                body: formData // Kirim file
            });

            const data = await res.json();
            
            // Bersihkan tampilan loading
            dataTableBody.innerHTML = '';
            newMatches = [];

            if (data.status === 'ok') {
                newMatches = data.matches || []; // Backend mengembalikan list matches baru
                
                if (newMatches.length === 0) {
                    // Gunakan elemen UI daripada alert/prompt
                    alert(data.message || 'Tidak ada pertandingan baru yang ditemukan.'); 
                    dataTableBody.innerHTML = '<tr><td colspan="30" class="text-center py-4">Tidak ada pertandingan baru yang ditemukan.</td></tr>';
                }
                
                // Tampilkan di tabel
                const columns = [
                    'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
                    'AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5',
                    'HomeTeamElo','AwayTeamElo','EloDifference',
                    'Home_AvgGoalsScored','Home_AvgGoalsConceded','Home_Wins','Home_Draws','Home_Losses',
                    'Away_AvgGoalsScored','Away_AvgGoalsConceded','Away_Wins','Away_Draws','Away_Losses',
                    'HTH_HomeWins','HTH_AwayWins','HTH_Draws','HTH_AvgHomeGoals','HTH_AvgAwayGoals'
                ];
                
                // Daftar kolom yang harus diformat sebagai Odds (minimal 2 desimal)
                const oddColumns = ['AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5'];
                // Daftar kolom yang harus diformat sebagai Skor/Hitungan (bilangan bulat)
                const scoreColumns = ['FTHG', 'FTAG', 'Home_Wins', 'Home_Draws', 'Home_Losses', 'Away_Wins', 'Away_Draws', 'Away_Losses', 'HTH_HomeWins', 'HTH_AwayWins', 'HTH_Draws'];

                newMatches.forEach(match => {
                    const tr = document.createElement('tr');
                    columns.forEach(col => {
                        const td = document.createElement('td');
                        const val = match[col] !== undefined ? match[col] : '';
                        
                        let displayValue = val;
                        
                        if (col === 'Date' && typeof val === 'string') {
                            // Perbaikan Format Tanggal: Tangani format YYYY-MM-DD
                            try {
                                const dateObj = new Date(val);
                                if (!isNaN(dateObj.getTime())) {
                                    // Menggunakan format DD/MM/YYYY untuk tampilan
                                    displayValue = dateObj.toLocaleDateString('en-GB', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '-');
                                } else {
                                    // Jika tidak dapat diparsing sebagai tanggal, biarkan nilai asli
                                    displayValue = val; 
                                }
                            } catch (e) {
                                displayValue = val;
                            }

                        } else if (typeof val === 'number' || (typeof val === 'string' && !isNaN(parseFloat(val)))) {
                            const num = typeof val === 'number' ? val : parseFloat(val);

                            if (scoreColumns.includes(col)) {
                                // Kolom Skor/Hitungan: Selalu tampilkan sebagai bilangan bulat
                                displayValue = Math.round(num).toString();
                            } else if (oddColumns.includes(col)) {
                                // Kolom Odds: Tampilkan dengan 2 desimal
                                displayValue = num.toFixed(2);
                            } else {
                                // Kolom lain (seperti Elo, AvgGoals): Tampilkan dengan 3 desimal
                                // dan hilangkan nol di belakang hanya jika benar-benar bilangan bulat
                                if (Number.isInteger(num)) {
                                    displayValue = num.toString();
                                } else {
                                    displayValue = num.toFixed(3);
                                }
                            }
                        }
                        
                        td.textContent = displayValue;
                        tr.appendChild(td);
                    });
                    dataTableBody.appendChild(tr);
                });
                
                if (newMatches.length > 0) {
                    alert(`Ditemukan ${newMatches.length} pertandingan baru siap disimpan.`);
                    autoScrollTable();
                }

            } else {
                alert(`Gagal memproses file: ${data.message}`);
            }

        } catch (error) {
            console.error('Fetch error:', error);
            alert('Terjadi kesalahan koneksi atau server.');
        } finally {
            saveBtn.textContent = '💾 Simpan Data';
            saveBtn.disabled = false;
        }
    });

    // 3. Simpan data baru ke dataset
    saveBtn.addEventListener('click', async () => {
        if (!selectedLeague || newMatches.length === 0) {
            alert('Tidak ada data untuk disimpan!');
            return;
        }

        const password = prompt('Masukkan password admin:');
        if (!password) {
            alert('Penyimpanan dibatalkan.');
            return;
        }

        // Tampilkan loading
        saveBtn.textContent = 'Menyimpan...';
        saveBtn.disabled = true;

        try {
            const res = await fetch('/api/save_new_matches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ league: selectedLeague, password, matches: newMatches })
            });

            const data = await res.json();
            if (data.status === 'ok') {
                alert('Data baru berhasil disimpan!');
                dataTableBody.innerHTML = '';
                newMatches = [];
                csvFileInput.value = ''; // Reset input file
            } else {
                alert(`Gagal menyimpan: ${data.message}`);
            }
        } catch (error) {
            console.error('Save error:', error);
            alert('Terjadi kesalahan koneksi saat menyimpan data.');
        } finally {
            saveBtn.textContent = '💾 Simpan Data';
            saveBtn.disabled = false;
        }
    });
}); // <--- Ini adalah penutup yang hilang/tidak terpakai dari kode asli
