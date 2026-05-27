# 📡 IPTV Channel Picker v4

**Zero CORS issues** — semua request ke server IPTV diproses oleh Python Serverless Function di Vercel, bukan dari browser.

## 🏗 Arsitektur

```
Browser  →  POST /api/iptv  →  Vercel Python (api/iptv.py)  →  Server IPTV
   ↑                                                                ↓
   └─────────────── JSON response (channels) ──────────────────────┘
```

Browser **tidak pernah langsung** kontak ke server IPTV → tidak ada CORS, IP browser aman.

## 🚀 Deploy ke Vercel (3 langkah)

### 1. Push ke GitHub

```bash
git init
git add .
git commit -m "init: iptv channel picker v4"
git branch -M main
git remote add origin https://github.com/USERNAME/iptv-picker.git
git push -u origin main
```

### 2. Deploy ke Vercel

Klik tombol di bawah **atau** manual:

```bash
npm i -g vercel
vercel
```

> Vercel otomatis mendeteksi Python di folder `api/` dan Node static di `public/`.

### 3. Buka URL

Vercel memberi URL seperti `https://iptv-picker-xxx.vercel.app` — langsung bisa dipakai.

---

## 📁 Struktur Project

```
iptv-picker/
├── api/
│   └── iptv.py          ← Python serverless (handles semua IPTV requests)
├── public/
│   └── index.html       ← Frontend UI
├── requirements.txt     ← Python deps (hanya stdlib, tidak perlu pip extra)
├── vercel.json          ← Routing config
└── README.md
```

---

## 🔌 API Endpoint

`POST /api/iptv` — semua action lewat sini:

| action | params | keterangan |
|---|---|---|
| `xtream_auth` | base, user, pass | cek kredensial Xtream |
| `xtream_live` | base, user, pass | ambil semua Live TV |
| `xtream_vod`  | base, user, pass | ambil semua VOD |
| `mac_auth`    | portal, mac | handshake MAC portal |
| `mac_channels`| portal, mac, token | ambil channel MAC |
| `m3u_fetch`   | url | download + parse M3U |

---

## ✨ Fitur

- ✅ Xtream Code (Live TV + VOD)
- ✅ MAC Portal (Stalker/Ministra)  
- ✅ URL M3U/M3U8
- ✅ Search real-time Panel A & B
- ✅ Sort: A→Z, Z→A, Numerik
- ✅ Pagination (80 baris/hal)
- ✅ Keranjang (pilih per baris / halaman / semua)
- ✅ Export M3U (dengan EPG URL)
- ✅ Export TXT

## 📄 License

MIT
