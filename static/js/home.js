document.addEventListener('DOMContentLoaded', () => {
    
    // --- [1] SCRIPT UNTUK FLASH MESSAGE ---
    const flashMessages = document.querySelectorAll('.flash-msg');
    flashMessages.forEach(msg => {
        // Setelah 2 detik (2000 ms), tambahkan class 'fade-out'
        setTimeout(() => {
            msg.classList.add('fade-out');
            // Setelah transisi selesai (0.5s), hapus elemennya
            setTimeout(() => {
                msg.remove();
            }, 500); // 500ms = 0.5s (durasi transisi di CSS)
        }, 2000); // 2000ms = 2 detik
    });

    
    // --- [2] SCRIPT UNTUK NAVBAR TOGGLE (DIHAPUS) ---
    /*
    Bagian ini dihapus karena logikanya sudah ada di file navbar.html Anda.
    */

    
    // --- [3] SCRIPT UNTUK RIWAYAT PREDIKSI ---
    const historyList = document.getElementById('history-list');
    const clearBtn = document.getElementById('clear-history');

    async function renderHistory() {
        if (!historyList) return;
        const res = await fetch('/api/history');
        const data = await res.json();
        if (data.status !== 'ok') {
            historyList.textContent = '(Belum ada riwayat)';
            return;
        }
        const h = data.history;
        if (!h.length) {
            historyList.textContent = '(Belum ada riwayat)';
            return;
        }
        historyList.innerHTML = '';
        h.slice().reverse().forEach(item => {
            const el = document.createElement('div');
            el.className = 'hist-item';
            
            const timestamp = item.timestamp 
                ? new Date(item.timestamp).toLocaleString() 
                : '(Waktu tidak tersimpan)';

            // --- [PERUBAHAN TAMPILAN DI SINI] ---
            // Menambahkan item.home_team dan item.away_team
            el.innerHTML = `
                <strong>${item.league}</strong>
                <span class="hist-match">${item.home_team || 'Tim Home'} vs ${item.away_team || 'Tim Away'}</span>
                <small>${timestamp}</small>
                <span class="hist-preds">
                    HDA: ${item.prediction.HDA?.label || '-'} | 
                    OU: ${item.prediction.OU25?.label || '-'} | 
                    BTTS: ${item.prediction.BTTS?.label || '-'}
                </span>
            `;
            // --- [AKHIR PERUBAHAN] ---
            
            historyList.appendChild(el);
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            await fetch('/api/clear_history', { method: 'POST' });
            renderHistory();
        });
    }

    // Hanya jalankan renderHistory jika elemennya ada (artinya, user login)
    if (historyList) {
        renderHistory();
    }
});