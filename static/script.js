document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('prediction-form');
    const predictButton = document.getElementById('predict-button');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('results-container');

    // (Logika dark mode dihapus karena tema default sekarang gelap)

    // Event listener untuk form prediksi
    form.addEventListener('submit', async function (event) {
        event.preventDefault();

        // Tampilkan loader, sembunyikan hasil, nonaktifkan tombol
        loader.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        predictButton.disabled = true;
        predictButton.textContent = 'Memproses...';

        const inputs = {
            'Avg_HT_GS': parseFloat(document.getElementById('Avg_HT_GS').value),
            'Avg_HT_GC': parseFloat(document.getElementById('Avg_HT_GC').value),
            'HT_Wins': parseInt(document.getElementById('HT_Wins').value),
            'HT_Draws': parseInt(document.getElementById('HT_Draws').value),
            'HT_Losses': parseInt(document.getElementById('HT_Losses').value),
            'Avg_AT_GS': parseFloat(document.getElementById('Avg_AT_GS').value),
            'Avg_AT_GC': parseFloat(document.getElementById('Avg_AT_GC').value),
            'AT_Wins': parseInt(document.getElementById('AT_Wins').value),
            'AT_Draws': parseInt(document.getElementById('AT_Draws').value),
            'AT_Losses': parseInt(document.getElementById('AT_Losses').value),
            'H2H_HT_Win_Rate': parseFloat(document.getElementById('H2H_HT_Win_Rate').value),
            'odds_h': parseFloat(document.getElementById('odds_h').value),
            'odds_d': parseFloat(document.getElementById('odds_d').value),
            'odds_a': parseFloat(document.getElementById('odds_a').value),
            'odds_over_2_5': parseFloat(document.getElementById('odds_over_2_5').value),
            'odds_under_2_5': parseFloat(document.getElementById('odds_under_2_5').value),
            'HT_Consistency': 0, 'HT_Concede_Rate': 0,
            'AT_Consistency': 0, 'AT_Concede_Rate': 0,
        };

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(inputs),
            });

            const results = await response.json();
            
            if (results.error) {
                alert('Terjadi error: ' + results.error);
            } else {
                document.getElementById('winner-result').textContent = results.prediksi_pemenang;
                document.getElementById('ou-result').textContent = results.prediksi_ou;
                resultsContainer.classList.remove('hidden');
            }
        } catch (error) {
            alert('Gagal terhubung ke server. Pastikan server app.py sudah berjalan.');
        } finally {
            // Sembunyikan loader, aktifkan kembali tombol
            loader.classList.add('hidden');
            predictButton.disabled = false;
            predictButton.textContent = 'Dapatkan Prediksi';
        }
    });
});