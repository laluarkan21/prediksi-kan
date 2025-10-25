document.addEventListener('DOMContentLoaded', () => {
    // --- Definisikan semua elemen HTML di awal ---
    const leagueEl = document.getElementById('League');
    const homeEl = document.getElementById('HomeTeam');
    const awayEl = document.getElementById('AwayTeam');
    const featureSection = document.getElementById('feature-section');
    const predictBtn = document.getElementById('PredictBtn');
    const resultEl = document.getElementById('result');
    const loadingSpinner = document.getElementById('loading-spinner');

    let currentFeatures = null;

    // [BARU] Inisialisasi Choices.js untuk setiap dropdown
    // Kita simpan instance-nya agar bisa kita panggil API-nya nanti
    const leagueChoice = new Choices(leagueEl, {
        searchEnabled: false,
        itemSelectText: 'Tekan untuk memilih',
        shouldSort: false, // Biarkan urutan liga dari server
        allowHTML: false,
        appendLocation: 'origin',
    });

    const homeChoice = new Choices(homeEl, {
        searchEnabled: true,
        itemSelectText: 'Tekan untuk memilih',
        shouldSort: true, // Urutkan nama tim berdasarkan abjad
        allowHTML: false,
        appendLocation: 'origin',
        searchPlaceholderValue: 'Ketik untuk mencari tim...'
    });

    const awayChoice = new Choices(awayEl, {
        searchEnabled: true,
        itemSelectText: 'Tekan untuk memilih',
        shouldSort: true, // Urutkan nama tim berdasarkan abjad
        allowHTML: false,
        appendLocation: 'origin',
        searchPlaceholderValue: 'Ketik untuk mencari tim...'
    });
    
    // ===================== LOAD LEAGUES =====================
    async function loadLeagues() {
    try {
        const res = await fetch('/api/leagues');
        const j = await res.json();

        // [PERBAIKAN] Mulai dengan array KOSONG.
        // Placeholder ("Pilih liga...") akan diambil dari HTML.
        const choices = []; 

        if (j.status === 'ok' && Array.isArray(j.leagues)) {
            // Hanya tambahkan nama liga yang sebenarnya
            j.leagues.forEach(l => {
                choices.push({ value: l, label: l });
            });

            // [PERBAIKAN] Gunakan .setChoices() hanya dengan daftar liga
            // Argumen 'true' akan menghapus placeholder awal dari HTML
            leagueChoice.setChoices(choices, 'value', 'label', true);

            // [PERBAIKAN] Set nilai kembali ke string kosong
            // untuk menampilkan placeholder HTML.
            leagueChoice.setValue(['']); 
        } else {
             // Jika gagal, set pilihan error dan tampilkan placeholder
             leagueChoice.setChoices([
                 { value: '', label: '(Gagal memuat liga)' }
             ], 'value', 'label', true);
             leagueChoice.setValue(['']);
        }
    } catch {
        // Tangani error fetch
        leagueChoice.setChoices([
            { value: '', label: '(Error koneksi)', disabled: true }
        ], 'value', 'label', true);
        leagueChoice.setValue(['']); // Tampilkan placeholder HTML
    }
}

    // ===================== LOAD TEAMS (VERSI PERBAIKAN) =====================
    // ===================== LOAD TEAMS (VERSI PERBAIKAN) =====================
async function loadTeamsForLeague(league) {
    try {
        const res = await fetch(`/api/teams?league=${encodeURIComponent(league)}`);
        const j = await res.json();

        // [PERBAIKAN] Mulai dengan array KOSONG.
        const teamChoices = [];

        if (j.status === 'ok' && Array.isArray(j.teams)) {

            // Hanya tambahkan nama tim yang sebenarnya ke array
            j.teams.forEach(t => {
                teamChoices.push({ value: t, label: t });
            });

            // 1. Set pilihan tim BARU (ini mungkin otomatis memilih yang pertama)
            homeChoice.setChoices(teamChoices, 'value', 'label', true);
            awayChoice.setChoices(teamChoices, 'value', 'label', true);

            // 2. PAKSA KEMBALI ke placeholder (nilai "") SETELAH setChoices
            homeChoice.setValue(['']); // Pastikan ini ada SETELAH setChoices
            awayChoice.setValue(['']); // Pastikan ini ada SETELAH setChoices

            // 3. Aktifkan dropdown
            homeChoice.enable();
            awayChoice.enable();

            console.log("Teams loaded. Set values to placeholder."); // DEBUG
        
        } else {
             // Jika gagal memuat tim, pastikan tetap disabled dan placeholder
             console.log("Failed to load teams. Disabling and setting placeholder."); // DEBUG
             homeChoice.disable();
             awayChoice.disable();
             homeChoice.clearStore(); // Hapus pilihan lama
             awayChoice.clearStore();
             homeChoice.setValue(['']); // Set ke placeholder
             awayChoice.setValue(['']);
        }
    } catch {
        alert('Gagal memuat tim (catch block)');
        // Pastikan dropdown tetap ter-disable jika error fetch
        homeChoice.disable();
        awayChoice.disable();
        homeChoice.clearStore();
        awayChoice.clearStore();
        homeChoice.setValue(['']);
        awayChoice.setValue(['']);
    }
}

    // ===================== FETCH FEATURES =====================
    // ... (Tidak ada perubahan di fungsi ini)
    async function fetchAndStoreFeatures(league, home, away) {
        const res = await fetch('/api/features', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ league, home, away })
        });
        const j = await res.json();
        if (j.status === 'ok') {
            currentFeatures = j.features;
            fillFeatureInputsWithTotals(j.features);
        } else {
            throw new Error(j.message || 'Fitur gagal dimuat');
        }
    }

    // ===================== TAMPILKAN FITUR DI INPUT =====================
    // ... (Tidak ada perubahan di fungsi ini)
    function fillFeatureInputsWithTotals(features) {
        const displayData = { ...features };
        const home_matches = features.Home_Wins + features.Home_Draws + features.Home_Losses;
        const away_matches = features.Away_Wins + features.Away_Draws + features.Away_Losses;
        const hth_matches = features.HTH_HomeWins + features.HTH_AwayWins + features.HTH_Draws;
        const home_count = home_matches > 0 ? home_matches : 5;
        const away_count = away_matches > 0 ? away_matches : 5;
        const hth_count = hth_matches > 0 ? hth_matches : 5;

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
                // --- PERBAIKAN DIMULAI DI SINI ---
                if (key === 'EloDifference' && typeof val === 'number') {
                    // Jika kunci adalah 'EloDifference' dan nilainya angka, format ke 2 desimal
                    el.value = val.toFixed(2);
                } else {
                    // Untuk semua fitur lain, tampilkan nilai asli
                    el.value = val;
                }
                // --- PERBAIKAN SELESAI DI SINI ---
            }
        }

        ['AvgH', 'AvgD', 'AvgA', 'AvgOver25', 'AvgUnder25'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        featureSection.classList.remove('hidden');
    }

    // ===================== AMBIL INPUT UNTUK PREDIKSI =====================
    // ... (Tidak ada perubahan di fungsi ini)
    function getFeaturesForPrediction() {
        if (!currentFeatures) {
            throw new Error('Fitur pertandingan belum dimuat. Silakan pilih tim terlebih dahulu.');
        }
        const featuresForPrediction = { ...currentFeatures };
        featuresForPrediction.AvgH = parseFloat(document.getElementById('AvgH').value) || 0;
        featuresForPrediction.AvgD = parseFloat(document.getElementById('AvgD').value) || 0;
        featuresForPrediction.AvgA = parseFloat(document.getElementById('AvgA').value) || 0;
        featuresForPrediction['Avg>2.5'] = parseFloat(document.getElementById('AvgOver25').value) || 0;
        featuresForPrediction['Avg<2.5'] = parseFloat(document.getElementById('AvgUnder25').value) || 0;
        return featuresForPrediction;
    }

    // ===================== TAMPILKAN HASIL =====================
    // ... (Tidak ada perubahan di fungsi ini)
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
            ${renderProbBlock('🤝 Both Team To Score', p.BTTS?.probs)}
          </div>
        `;
        animateBars();
    }
    // ... (Tidak ada perubahan di fungsi getGradientColor)
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
    // ... (Tidak ada perubahan di fungsi renderProbBlock)
    function renderProbBlock(title, probs) {
        if (!probs) return '';
        let html = `<div class="prob-group"><h4>${title}</h4>`;
        for (const [label, val] of Object.entries(probs)) {
            const percent = (val * 100).toFixed(1);
            const gradient = getGradientColor(percent);
            html += `
            <div class="prob-item">
                <span>${label}</span>
                <div class="prob-bar"><div class="bar" style="width:${percent}%; background:${gradient}"></div></div>
                <span>${percent}%</span>
            </div>`;
        }
        html += `</div>`;
        return html;
    }
    // ... (Tidak ada perubahan di fungsi animateBars)
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

    // ===================== EVENT LISTENERS (VERSI PERBAIKAN) =====================
    leagueEl.addEventListener('change', e => {
    const league = e.target.value;
    if (!league) return;

    // Reset dan disable dropdown tim
    homeChoice.disable();
    awayChoice.disable();
    
    // Hapus semua pilihan yang ada
    homeChoice.clearStore();
    awayChoice.clearStore();

    // Set nilai ke placeholder HTML
    homeChoice.setValue(['']);
    awayChoice.setValue(['']);

    // Panggil fungsi loadTeams
    loadTeamsForLeague(league);

    // Sembunyikan bagian lain
    featureSection.classList.add('hidden');
    resultEl.classList.add('hidden');
    currentFeatures = null;
});

    // ... (Tidak ada perubahan di event listener [homeEl, awayEl]) ...
    [homeEl, awayEl].forEach(sel => {
    // Gunakan 'choice' event dari Choices.js, BUKAN 'change' dari <select>
    // Ini mungkin lebih andal
    const choiceInstance = (sel.id === 'HomeTeam') ? homeChoice : awayChoice;

    choiceInstance.passedElement.element.addEventListener('choice', async (event) => {
        // Selalu sembunyikan fitur & reset state di awal
        featureSection.classList.add('hidden');
        resultEl.classList.add('hidden');
        currentFeatures = null; // Reset fitur

        // [PERUBAHAN UTAMA] Ambil nilai langsung dari instance Choices.js
        // .getValue(true) mengembalikan nilai (string), bukan objek
        const leagueValue = leagueChoice.getValue(true);
        const homeValue = homeChoice.getValue(true);
        const awayValue = awayChoice.getValue(true);

        console.log(`Choice Event Triggered. Checking conditions - League: "${leagueValue}", Home: "${homeValue}", Away: "${awayValue}"`);

        // Gunakan nilai dari API Choices.js untuk pengecekan
        if (leagueValue && leagueValue !== '' &&
            homeValue && homeValue !== '' &&
            awayValue && awayValue !== '' &&
            homeValue !== awayValue) {

            console.log("Conditions MET (using Choices API). Attempting to fetch features...");
            try {
                if (loadingSpinner) loadingSpinner.classList.remove('hidden');
                // Kirim nilai yang didapat dari API Choices.js ke backend
                await fetchAndStoreFeatures(leagueValue, homeValue, awayValue);

            } catch (err) {
                console.error('Error fetching features:', err);
                alert('Gagal memuat fitur otomatis: ' + err.message);
                featureSection.classList.add('hidden');
            } finally {
                 if (loadingSpinner) loadingSpinner.classList.add('hidden');
            }
        } else {
             console.log("Conditions NOT MET (using Choices API). Features remain hidden.");
        }
    });

    // Tambahkan listener untuk 'change' juga sebagai fallback/safety net
    // untuk menyembunyikan fitur jika nilai kembali ke placeholder (value="")
    sel.addEventListener('change', () => {
        const homeVal = homeChoice.getValue(true);
        const awayVal = awayChoice.getValue(true);
        if (!homeVal || homeVal === '' || !awayVal || awayVal === '') {
             featureSection.classList.add('hidden');
             resultEl.classList.add('hidden');
             currentFeatures = null;
        }
    });
});

    // ===================== PREDICT BUTTON =====================
    // ... (Tidak ada perubahan di fungsi ini)
    predictBtn.addEventListener('click', async () => {
        predictBtn.disabled = true;
        if (loadingSpinner) loadingSpinner.classList.remove('hidden');
        resultEl.classList.add('hidden');

        try {
            const features = getFeaturesForPrediction();
            const res = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    league: leagueEl.value,
                    features: features,
                    home_team: homeEl.value,
                    away_team: awayEl.value
                })
            });
            const json = await res.json();

            if (json.status === 'ok' && json.prediction) {
                const history = JSON.parse(localStorage.getItem('pred_history') || '[]');
                const entry = {
                    match: `${homeEl.value} vs ${awayEl.value}`,
                    timestamp: new Date().toLocaleString(),
                    HDA: { label: json.prediction.HDA?.label || '-' },
                    OU25: { label: json.prediction.OU25?.label || '-' },
                    BTTS: { label: json.prediction.BTTS?.label || '-' }
                };
                history.push(entry);
                localStorage.setItem('pred_history', JSON.stringify(history));
            }

            showPredictionResult(json);
        } catch (err) {
            alert('Terjadi kesalahan saat prediksi: ' + err.message);
            console.error(err);
        } finally {
            predictBtn.disabled = false;
            if (loadingSpinner) loadingSpinner.classList.add('hidden');
        }
    });

    loadLeagues();
});