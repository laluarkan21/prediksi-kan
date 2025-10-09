document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('prediction-form');
    const predictButton = document.getElementById('predict-button');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('results-container');

    form.addEventListener('submit', async function (event) {
        event.preventDefault();

        loader.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        predictButton.disabled = true;
        predictButton.querySelector('span').textContent = 'Memproses...';

        const inputs = {
            liga: document.getElementById('liga').value,

            // Statistik Home Team (5 laga terakhir)
            ht_gs: document.getElementById('ht_gs').value,
            ht_gc: document.getElementById('ht_gc').value,
            ht_w: document.getElementById('ht_w').value,
            ht_d: document.getElementById('ht_d').value,
            ht_l: document.getElementById('ht_l').value,

            // Statistik Away Team (5 laga terakhir)
            at_gs: document.getElementById('at_gs').value,
            at_gc: document.getElementById('at_gc').value,
            at_w: document.getElementById('at_w').value,
            at_d: document.getElementById('at_d').value,
            at_l: document.getElementById('at_l').value,

            // Tambahan data lain
            h2h_wins: document.getElementById('h2h_wins').value,
            ahh: document.getElementById('ahh').value,
            avg_ahh: document.getElementById('avg_ahh').value,
            avg_aha: document.getElementById('avg_aha').value,
            odds_h: document.getElementById('odds_h').value,
            odds_d: document.getElementById('odds_d').value,
            odds_a: document.getElementById('odds_a').value,
            odds_over_2_5: document.getElementById('odds_over_2_5').value,
            odds_under_2_5: document.getElementById('odds_under_2_5').value,
        };

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(inputs),
            });
            const results = await response.json();

            setTimeout(() => {
                loader.classList.add('hidden');
                if (results.error) {
                    alert('Terjadi error: ' + results.error);
                } else {
                    document.getElementById('hda-result').textContent = results.prediksi_hda;
                    document.getElementById('ou-result').textContent = results.prediksi_ou;
                    document.getElementById('btts-result').textContent = results.prediksi_btts;
                    resultsContainer.classList.remove('hidden');
                }
                predictButton.disabled = false;
                predictButton.querySelector('span').textContent = 'Dapatkan Prediksi';
            }, 500);

        } catch (error) {
            alert('Gagal terhubung ke server. Pastikan server app.py sudah berjalan.');
            loader.classList.add('hidden');
            predictButton.disabled = false;
            predictButton.querySelector('span').textContent = 'Dapatkan Prediksi';
        }
    });
});
