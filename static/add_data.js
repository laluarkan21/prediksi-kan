document.addEventListener('DOMContentLoaded', async () => {
    const leagueSelect = document.getElementById('leagueSelect');
    const csvFileInput = document.getElementById('csvFile');
    const dataTableBody = document.querySelector('#dataTable tbody');
    const saveBtn = document.getElementById('saveBtn');
    const toggleBtn = document.getElementById('toggleThemeBtn'); // Tombol toggle
    const body = document.body;

    let selectedLeague = '';
    let newMatches = [];

    // ===== Mode Gelap / Terang =====
    // Default mode gelap
    body.classList.add('dark-mode');

    toggleBtn.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
    });


    // 1. Ambil daftar liga
    async function loadLeagues() {
        const res = await fetch('/api/leagues');
        const data = await res.json();
        if (data.status === 'ok') {
            data.leagues.forEach(league => {
                const option = document.createElement('option');
                option.value = league;
                option.textContent = league;
                leagueSelect.appendChild(option);
            });
        }
    }

    await loadLeagues();

    leagueSelect.addEventListener('change', () => {
        selectedLeague = leagueSelect.value;
        dataTableBody.innerHTML = '';
        newMatches = [];
    });

    // 2. Proses CSV
    csvFileInput.addEventListener('change', async (e) => {
        if (!selectedLeague) {
            alert('Pilih liga terlebih dahulu!');
            csvFileInput.value = '';
            return;
        }

        const file = e.target.files[0];
        if (!file) return;

        const text = await file.text();
        const rows = text.split(/\r?\n/).filter(r => r.trim() !== '');
        const headers = rows[0].split(',');

        // Pastikan ada kolom HomeTeam dan AwayTeam
        if (!headers.includes('HomeTeam') || !headers.includes('AwayTeam')) {
            alert('CSV harus memiliki kolom HomeTeam dan AwayTeam!');
            return;
        }

        const csvData = rows.slice(1).map(r => {
            const vals = r.split(',');
            let obj = {};
            headers.forEach((h, i) => { obj[h] = vals[i]; });
            return obj;
        });

        // Ambil dataset liga saat ini dari server
        const res = await fetch(`/api/teams?league=${encodeURIComponent(selectedLeague)}`);
        const teamsData = await res.json();
        let existingTeams = teamsData.status === 'ok' ? teamsData.teams : [];

        // Filter data baru (belum ada)
        newMatches = csvData.filter(row => {
            return !existingTeams.includes(row.HomeTeam) || !existingTeams.includes(row.AwayTeam) || !row.Date || !row.FTHG;
        });

        // Ambil fitur otomatis untuk setiap match baru
        const featuresPromises = newMatches.map(async row => {
            const resp = await fetch('/api/features', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    league: selectedLeague,
                    home: row.HomeTeam,
                    away: row.AwayTeam
                })
            });
            const data = await resp.json();
            return { ...row, ...data.features };
        });

        newMatches = await Promise.all(featuresPromises);

        // Tampilkan di tabel
        dataTableBody.innerHTML = '';
        newMatches.forEach(match => {
            const tr = document.createElement('tr');
            const columns = [
                'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
                'AvgH', 'AvgD', 'AvgA', 'Avg>2.5', 'Avg<2.5',
                'HomeTeamElo','AwayTeamElo','EloDifference',
                'Home_AvgGoalsScored','Home_AvgGoalsConceded','Home_Wins','Home_Draws','Home_Losses',
                'Away_AvgGoalsScored','Away_AvgGoalsConceded','Away_Wins','Away_Draws','Away_Losses',
                'HTH_HomeWins','HTH_AwayWins','HTH_Draws','HTH_AvgHomeGoals','HTH_AvgAwayGoals'
            ];
            columns.forEach(col => {
                const td = document.createElement('td');
                td.textContent = match[col] !== undefined ? match[col] : '';
                tr.appendChild(td);
            });
            dataTableBody.appendChild(tr);
        });
    });

    // 3. Simpan data baru ke dataset
    saveBtn.addEventListener('click', async () => {
        if (!selectedLeague || newMatches.length === 0) {
            alert('Tidak ada data untuk disimpan!');
            return;
        }

        const password = prompt('Masukkan password admin:');
        if (!password) return;

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
            csvFileInput.value = '';
        } else {
            alert(`Gagal menyimpan: ${data.message}`);
        }
    });
});
