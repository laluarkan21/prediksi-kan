document.addEventListener('DOMContentLoaded', () => {
  // === Ambil elemen ===
  const leagueSel = document.getElementById('league-select');
  const teamSel = document.getElementById('team-select');
  const loadBtn = document.getElementById('load-stats');
  const container = document.getElementById('team-stats');

  // === 1. Ambil daftar liga ===
  async function loadLeagues() {
    const res = await fetch('/api/leagues');
    const data = await res.json();
    if (data.status === 'ok') {
      leagueSel.innerHTML = '<option value="">-- Pilih Liga --</option>';
      data.leagues.forEach(l => {
        leagueSel.innerHTML += `<option value="${l}">${l}</option>`;
      });
    }
  }

  // === 2. Ambil tim saat liga dipilih ===
  leagueSel.addEventListener('change', async () => {
    const league = leagueSel.value;
    if (!league) return;
    const res = await fetch(`/api/teams?league=${encodeURIComponent(league)}`);
    const data = await res.json();
    if (data.status === 'ok') {
      teamSel.innerHTML = '<option value="">-- Pilih Tim --</option>';
      data.teams.forEach(t => {
        teamSel.innerHTML += `<option value="${t}">${t}</option>`;
      });
    }
  });

  // === 3. Tampilkan statistik tim ===
  loadBtn.addEventListener('click', async () => {
    const league = leagueSel.value;
    const team = teamSel.value;
    if (!league || !team) {
      alert('Pilih liga dan tim terlebih dahulu!');
      return;
    }

    container.innerHTML = '<p>Sedang memuat data...</p>';

    const res = await fetch('/api/team_stats', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ league, team })
    });
    const data = await res.json();

    if (data.status === 'ok') {
      const s = data.stats;
      const recent = s.recent || {};

      container.innerHTML = `
        <div class="stats-card">
          <div class="stat-item"><strong>Last Elo</strong><div>${s.last_elo || '-'}</div></div>
          <div class="stat-item"><strong>Avg Goals Scored</strong><div>${recent.AvgGoalsScored || 0}</div></div>
          <div class="stat-item"><strong>Avg Goals Conceded</strong><div>${recent.AvgGoalsConceded || 0}</div></div>
          <div class="stat-item"><strong>Wins</strong><div>${recent.Wins || 0}</div></div>
          <div class="stat-item"><strong>Draws</strong><div>${recent.Draws || 0}</div></div>
          <div class="stat-item"><strong>Losses</strong><div>${recent.Losses || 0}</div></div>
        </div>
      `;
    } else {
      container.innerHTML = `<p style="color:red;">Gagal memuat statistik</p>`;
    }
  });

  loadLeagues();
});
