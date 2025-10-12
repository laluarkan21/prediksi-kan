document.addEventListener('DOMContentLoaded', () => {
    // --- Definisikan semua elemen HTML di awal ---
    const leagueEl = document.getElementById('League');
    const homeEl = document.getElementById('HomeTeam');
    const awayEl = document.getElementById('AwayTeam');
    const featureSection = document.getElementById('feature-section');
    const predictBtn = document.getElementById('PredictBtn');
    const resultEl = document.getElementById('result');
    // Tambahkan elemen spinner jika ada di HTML Anda
    const loadingSpinner = document.getElementById('loading-spinner');

    // ==========================================================
    // VARIABEL KUNCI: Menyimpan data asli (rata-rata) dari server.
    // Ini memperbaiki bug "hanya bisa sekali" dan membuat prediksi efisien.
    // ==========================================================
    let currentFeatures = null;

    // ===================== LOAD LEAGUES =====================
    async function loadLeagues() {
        try {
            const res = await fetch('/api/leagues');
            const j = await res.json();
            leagueEl.innerHTML = '<option value="">Pilih liga...</option>';
            if (j.status === 'ok' && Array.isArray(j.leagues)) {
                j.leagues.forEach(l => {
                    const opt = document.createElement('option');
                    opt.value = l;
                    opt.textContent = l;
                    leagueEl.appendChild(opt);
                });
            }
        } catch {
            leagueEl.innerHTML += '<option>(Gagal memuat liga)</option>';
        }
    }

    // ===================== LOAD TEAMS =====================
    async function loadTeamsForLeague(league) {
        try {
            const res = await fetch(`/api/teams?league=${encodeURIComponent(league)}`);
            const j = await res.json();
            if (j.status === 'ok' && Array.isArray(j.teams)) {
                homeEl.innerHTML = '<option value="">Pilih tim kandang...</option>';
                awayEl.innerHTML = '<option value="">Pilih tim tandang...</option>';
                j.teams.forEach(t => {
                    const opt1 = document.createElement('option');
                    const opt2 = document.createElement('option');
                    opt1.value = opt2.value = t;
                    opt1.textContent = opt2.textContent = t;
                    homeEl.appendChild(opt1);
                    awayEl.appendChild(opt2);
                });
                homeEl.disabled = false;
                awayEl.disabled = false;
            }
        } catch {
            alert('Gagal memuat tim');
        }
    }

    // ===================== FETCH FEATURES =====================
    async function fetchAndStoreFeatures(league, home, away) {
        const res = await fetch('/api/features', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ league, home, away })
        });
        const j = await res.json();
        if (j.status === 'ok') {
            // 1. Simpan data asli (rata-rata) ke variabel global
            currentFeatures = j.features;
            // 2. Tampilkan data sebagai total di form
            fillFeatureInputsWithTotals(j.features);
        } else {
            throw new Error(j.message || 'Fitur gagal dimuat');
        }
    }

    // ======================================================================
    // FUNGSI INI MENGHITUNG TOTAL HANYA UNTUK TAMPILAN
    // ======================================================================
    function fillFeatureInputsWithTotals(features) {
        const displayData = { ...features };

        const home_matches = features.Home_Wins + features.Home_Draws + features.Home_Losses;
        const away_matches = features.Away_Wins + features.Away_Draws + features.Away_Losses;
        const hth_matches = features.HTH_HomeWins + features.HTH_AwayWins + features.HTH_Draws;
        
        const home_count = home_matches > 0 ? home_matches : 5;
        const away_count = away_matches > 0 ? away_matches : 5;
        const hth_count = hth_matches > 0 ? hth_matches : 5;

        // Ubah rata-rata menjadi total untuk ditampilkan
        displayData.Home_AvgGoalsScored = Math.round(features.Home_AvgGoalsScored * home_count);
        displayData.Home_AvgGoalsConceded = Math.round(features.Home_AvgGoalsConceded * home_count);
        displayData.Away_AvgGoalsScored = Math.round(features.Away_AvgGoalsScored * away_count);
        displayData.Away_AvgGoalsConceded = Math.round(features.Away_AvgGoalsConceded * away_count);
        displayData.HTH_AvgHomeGoals = Math.round(features.HTH_AvgHomeGoals * hth_count);
        displayData.HTH_AvgAwayGoals = Math.round(features.HTH_AvgAwayGoals * hth_count);

        const featureIdMap = { 'Avg>2.5': 'AvgOver25', 'Avg<2.5': 'AvgUnder25' };

        for (const [key, val] of Object.entries(displayData)) {
            const elementId = featureIdMap[key] || key;
            const el = document.getElementById(elementId);
            if (el) {
                el.value = val;
            }
        }

        // Kosongkan input odds agar bisa diisi manual
        ['AvgH', 'AvgD', 'AvgA', 'AvgOver25', 'AvgUnder25'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        featureSection.classList.remove('hidden');
    }

    // ================================================================
    // FUNGSI INI MENGAMBIL DATA BERSIH DAN MENAMBAHKAN ODDS MANUAL
    // ================================================================
    function getFeaturesForPrediction() {
        if (!currentFeatures) {
            throw new Error('Fitur pertandingan belum dimuat. Silakan pilih tim terlebih dahulu.');
        }

        // Mulai dengan data asli (rata-rata) yang bersih
        const featuresForPrediction = { ...currentFeatures };

        // Timpa nilai odds dengan input manual dari pengguna
        featuresForPrediction.AvgH = parseFloat(document.getElementById('AvgH').value) || 0;
        featuresForPrediction.AvgD = parseFloat(document.getElementById('AvgD').value) || 0;
        featuresForPrediction.AvgA = parseFloat(document.getElementById('AvgA').value) || 0;
        
        // FIX: Gunakan ID yang benar ('AvgOver25') untuk mengambil nilai
        featuresForPrediction['Avg>2.5'] = parseFloat(document.getElementById('AvgOver25').value) || 0;
        featuresForPrediction['Avg<2.5'] = parseFloat(document.getElementById('AvgUnder25').value) || 0;

        return featuresForPrediction;
    }

    // ===================== FUNGSI TAMPILAN (Tidak Berubah) =====================
    function showPredictionResult(json) {
        if (!json || json.status !== 'ok' || !json.prediction) {
            resultEl.classList.remove('hidden');
            resultEl.innerHTML = `<div>❌ Gagal menampilkan hasil prediksi: ${json.message || ''}</div>`;
            return;
        }
        const p = json.prediction;
        resultEl.classList.remove('hidden');
        resultEl.innerHTML = `
      <div class="result-title">📊 Hasil Prediksi</div>
      <div id="main-result">
        🏠 (Home/Draw/Away): <b>${p.HDA?.label || '-'}</b><br>
        ⚽ Over/Under 2.5: <b>${p.OU25?.label || '-'}</b><br>
        🤝 BTTS: <b>${p.BTTS?.label || '-'}</b>
      </div>
      <div id="prob-bars" class="prob-section">
        ${renderProbBlock('🏠 (Home / Draw / Away)', p.HDA?.probs)}
        ${renderProbBlock('⚽ Over / Under 2.5', p.OU25?.probs)}
        ${renderProbBlock('🤝 BTTS', p.BTTS?.probs)}
      </div>
    `;
        animateBars();
    }

    function getGradientColor(percent) {
        let r, g, b = 0;
        if (percent < 50) {
            r = 255;
            g = Math.round(5.1 * percent);
        } else {
            g = 255;
            r = Math.round(510 - 5.1 * percent);
        }
        return `linear-gradient(90deg, rgb(${r},${g},0) 0%, rgb(${r},${g},0) ${percent}%)`;
    }

    function renderProbBlock(title, probs) {
        if (!probs) return '';
        let html = `<div class="prob-group"><h4>${title}</h4>`;
        for (const [label, val] of Object.entries(probs)) {
            const percent = (val * 100).toFixed(1);
            const gradient = getGradientColor(percent);
            html += `
        <div class="prob-item">
            <span>${label}</span>
            <div class="prob-bar">
            <div class="bar" style="width:${percent}%; background:${gradient}"></div>
            </div>
            <span>${percent}%</span>
        </div>
        `;
        }
        html += `</div>`;
        return html;
    }

    function animateBars() {
        document.querySelectorAll('.bar').forEach(bar => {
            const percent = bar.style.width.replace('%', '');
            bar.style.width = '0%';
            setTimeout(() => {
                bar.style.transition = 'width 1s ease';
                bar.style.width = `${percent}%`;
            }, 50);
        });
    }

    // ===================== EVENT LISTENERS =====================
    leagueEl.addEventListener('change', e => {
        const league = e.target.value;
        if (!league) return;
        loadTeamsForLeague(league);
        featureSection.classList.add('hidden');
        resultEl.classList.add('hidden');
        currentFeatures = null; // Reset data saat ganti liga
    });

    [homeEl, awayEl].forEach(sel => {
        sel.addEventListener('change', async () => {
            const league = leagueEl.value;
            const home = homeEl.value;
            const away = awayEl.value;
            if (!league || !home || !away || home === away) return;
            try {
                await fetchAndStoreFeatures(league, home, away);
            } catch (err) {
                alert('Gagal memuat fitur otomatis: ' + err.message);
            }
        });
    });

    predictBtn.addEventListener('click', async () => {
        // Logika untuk loading spinner
        predictBtn.disabled = true;
        if (loadingSpinner) loadingSpinner.classList.remove('hidden');
        resultEl.classList.add('hidden');

        try {
            const features = getFeaturesForPrediction();
            const res = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ league: leagueEl.value, features })
            });
            const json = await res.json();
            showPredictionResult(json);
        } catch (err) {
            alert('Terjadi kesalahan saat prediksi: ' + err.message);
            console.error(err);
        } finally {
            // Sembunyikan spinner dan aktifkan kembali tombol
            predictBtn.disabled = false;
            if (loadingSpinner) loadingSpinner.classList.add('hidden');
        }
    });

    // Inisialisasi
    loadLeagues();
});