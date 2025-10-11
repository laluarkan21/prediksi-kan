document.addEventListener('DOMContentLoaded', () => {
  const leagueEl = document.getElementById('League');
  const homeEl = document.getElementById('HomeTeam');
  const awayEl = document.getElementById('AwayTeam');
  const featureSection = document.getElementById('feature-section');
  const predictBtn = document.getElementById('PredictBtn');
  const resultEl = document.getElementById('result');

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
  async function fetchFeatures(league, home, away) {
    const res = await fetch('/api/features', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ league, home, away })
    });
    const j = await res.json();
    if (j.status === 'ok') {
      fillFeatureInputs(j.features);
      return j.features;
    }
    throw new Error('Fitur gagal dimuat');
  }

  // ===================== FILL INPUT FIELD DENGAN DATA =====================
  function fillFeatureInputs(features) {
    // Buat salinan untuk menampilkan di input
    const displayFeatures = { ...features };

    // ==========================
    // Hitung jumlah match sebenarnya
    // ==========================
    const home_matches = features.Home_Wins + features.Home_Draws + features.Home_Losses;
    const away_matches = features.Away_Wins + features.Away_Draws + features.Away_Losses;
    const hth_matches = features.HTH_HomeWins + features.HTH_AwayWins + features.HTH_Draws;

    const home_count = home_matches > 0 ? home_matches : 5;
    const away_count = away_matches > 0 ? away_matches : 5;
    const hth_count = hth_matches > 0 ? hth_matches : 5;

    // ==========================
    // Ubah input yang ingin ditampilkan sebagai jumlah berdasarkan match_count
    // ==========================
    displayFeatures.Home_AvgGoalsScored = Math.round(features.Home_AvgGoalsScored * home_count);
    displayFeatures.Home_AvgGoalsConceded = Math.round(features.Home_AvgGoalsConceded * home_count);
    displayFeatures.Away_AvgGoalsScored = Math.round(features.Away_AvgGoalsScored * away_count);
    displayFeatures.Away_AvgGoalsConceded = Math.round(features.Away_AvgGoalsConceded * away_count);

    displayFeatures.HTH_AvgHomeGoals = Math.round(features.HTH_AvgHomeGoals * hth_count);
    displayFeatures.HTH_AvgAwayGoals = Math.round(features.HTH_AvgAwayGoals * hth_count);

    // ==========================
    // Masukkan nilai ke input
    // ==========================
    for (const [key, val] of Object.entries(displayFeatures)) {
        const el = document.getElementById(key);
        if (el) {
            el.value = val;  // Menampilkan jumlah di input
        }
    }

    // Odds tetap dikosongkan agar user bisa isi manual
    ['AvgH','AvgD','AvgA','AvgOver25','AvgUnder25'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });

    featureSection.classList.remove('hidden');
}




  // ===================== TAMPILKAN HASIL PREDIKSI =====================
  function showPredictionResult(json) {
    if (!json || json.status !== 'ok' || !json.prediction) {
      resultEl.classList.remove('hidden');
      resultEl.innerHTML = '<div>❌ Gagal menampilkan hasil prediksi.</div>';
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
        ${renderProbBlock('🏠 (Home / Draw / Away)', p.HDA?.probs, 'hda')}
        ${renderProbBlock('⚽ Over / Under 2.5', p.OU25?.probs, 'ou')}
        ${renderProbBlock('🤝 BTTS', p.BTTS?.probs, 'btts')}
      </div>
    `;
    animateBars();
  }

  function getGradientColor(percent) {
    // percent: 0-100
    // 0% = merah, 50% = kuning, 100% = hijau
    let r, g, b = 0;

    if (percent < 50) {
        r = 255;
        g = Math.round(5.1 * percent); // 0 → 255
    } else {
        g = 255;
        r = Math.round(510 - 5.1 * percent); // 255 → 0
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
    const percent = bar.style.width.replace('%','');
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
  });

  [homeEl, awayEl].forEach(sel => {
    sel.addEventListener('change', async () => {
      const league = leagueEl.value;
      const home = homeEl.value;
      const away = awayEl.value;
      if (!league || !home || !away || home === away) return;
      try {
        await fetchFeatures(league, home, away);
      } catch {
        alert('Gagal memuat fitur otomatis');
      }
    });
  });

  async function getFeaturesForPrediction() {
    const league = leagueEl.value;
    const home = homeEl.value;
    const away = awayEl.value;

    const res = await fetch('/api/features', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ league, home, away })
    });
    const data = await res.json();
    if (data.status !== 'ok') throw new Error('Gagal ambil fitur');

    const feats = data.features;

    // Ambil input odds user dari form
    feats.AvgH = parseFloat(document.getElementById('AvgH').value) || 0;
    feats.AvgD = parseFloat(document.getElementById('AvgD').value) || 0;
    feats.AvgA = parseFloat(document.getElementById('AvgA').value) || 0;
    feats['Avg>2.5'] = parseFloat(document.getElementById('AvgOver25').value) || 0;
    feats['Avg<2.5'] = parseFloat(document.getElementById('AvgUnder25').value) || 0;

    return feats;
    }

    // Event predict
    predictBtn.addEventListener('click', async () => {
    try {
        const features = await getFeaturesForPrediction();
        const res = await fetch('/api/predict', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ league: leagueEl.value, features })
        });
        const json = await res.json();
        showPredictionResult(json);
    } catch (err) {
        alert('Terjadi kesalahan saat prediksi: ' + err.message);
        console.error(err);
    }
    });

  loadLeagues();
});
