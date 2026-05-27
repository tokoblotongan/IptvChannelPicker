# 📡 IPTV Channel Picker v3

Aplikasi web untuk memilih dan mengekspor channel IPTV ke format M3U/TXT.  
Dibangun dengan pure HTML/CSS/JS — **zero dependencies**, langsung buka di browser.

## ✨ Fitur

- **3 sumber**: Xtream Code, MAC Portal, URL M3U
- **Cari real-time** di Panel A dan Panel B
- **Sort**: A→Z, Z→A, Numerik
- **Navigasi halaman** (80 baris/hal) — aman untuk 12.000+ channel
- **Keranjang** (basket) — pilih per baris, per halaman, atau semua
- **Export M3U** dengan EPG URL support
- **Export TXT** (daftar nama + URL)

---

## 🚀 Deploy ke Vercel via GitHub

### 1. Push ke GitHub

```bash
# Buat repo baru di github.com, lalu:
git init
git add .
git commit -m "init: IPTV Channel Picker v3"
git branch -M main
git remote add origin https://github.com/USERNAME/iptv-picker.git
git push -u origin main
```

### 2. Import ke Vercel

1. Buka [vercel.com](https://vercel.com) → **Add New Project**
2. Import repo GitHub `iptv-picker`
3. Biarkan semua pengaturan default → klik **Deploy**
4. Selesai! App live di `https://iptv-picker-xxx.vercel.app`

### 3. Custom Domain (opsional)

Di Vercel dashboard → Settings → Domains → tambahkan domain kamu.

---

## 🔧 Mengatasi CORS

Browser memblokir request langsung ke server IPTV. Ada 2 solusi:

### Solusi A — Gunakan Proxy Bawaan (sudah tersedia)

File `api/proxy.js` adalah Vercel Serverless Function yang bertindak sebagai proxy.  
Setelah deploy, kamu bisa panggil:

```
https://your-app.vercel.app/api/proxy?url=http://iptv-server:8080/player_api.php?username=...
```

Untuk mengaktifkan proxy di `index.html`, ganti semua `fetch(url, ...)` dengan:

```js
// Sebelum:
fetch(`${base}/player_api.php?username=${u}&password=${p}`)

// Sesudah (gunakan proxy):
fetch(`/api/proxy?url=${encodeURIComponent(`${base}/player_api.php?username=${u}&password=${p}`)}`)
```

### Solusi B — Ekstensi Browser

Install ekstensi [CORS Unblock](https://chrome.google.com/webstore/detail/cors-unblock/) untuk development lokal.

### Solusi C — Jalankan Lokal

```bash
# Python simple server
python3 -m http.server 8080
# Buka http://localhost:8080
```

---

## 📁 Struktur File

```
iptv-picker/
├── index.html       # Aplikasi utama (single file)
├── api/
│   └── proxy.js     # Vercel Serverless proxy untuk CORS
├── vercel.json      # Konfigurasi Vercel
└── README.md
```

---

## 📋 Cara Pakai

1. **Pilih sumber** — Xtream Code / MAC Portal / URL M3U
2. **Isi kredensial** → klik **LOAD CHANNEL**
3. **Panel A**: channel list → klik `+ Pilih` untuk masuk keranjang
4. Gunakan `⊕ Halaman ini` atau `⊕ Semua` untuk tambah massal
5. **Panel B**: cek keranjang, hapus yang tidak perlu
6. **Export M3U** / **Export TXT** → file langsung ter-download

---

## ⚙️ Pengembangan Lanjut

### Tambah autentikasi (opsional)
Edit `api/proxy.js` → tambahkan API key check:

```js
const API_KEY = process.env.PROXY_API_KEY;
if (req.headers['x-api-key'] !== API_KEY) {
  return res.status(401).json({ error: 'Unauthorized' });
}
```

Lalu set di Vercel: Settings → Environment Variables → `PROXY_API_KEY=your-secret-key`

### Simpan history (opsional)
Tambahkan localStorage untuk menyimpan kredensial dan basket terakhir.

---

## 📄 License

MIT — Bebas digunakan dan dimodifikasi.
