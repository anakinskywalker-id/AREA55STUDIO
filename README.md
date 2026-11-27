# Property 360° VR — Web Tur Virtual Properti

Web tur virtual 360° VR untuk marketing developer properti (interior & eksterior rumah), dilengkapi dengan:
- **Minimap Denah Interaktif**: Titik lokasi ruangan otomatis menyala mengikuti ruangan yang sedang dilihat (misal saat di Master Bedroom, pin Master Bedroom aktif). Klik pin di denah untuk langsung pindah ruangan.
- **Kompas / Radar Arah Pandang**: Kerucut radar di denah berputar real-time mengikuti arah kamera 360°.
- **Mode VR Cardboard (Split-Screen) & Gyroscope HP**: Bisa langsung dipakai di HP atau kacamata VR.
- **Multi-Projek + Link Khusus**: Setiap projek punya URL sendiri (misal `/p/cluster-anggrek`).
- **Panel Admin Berpassword + Visual Editor**:
  - Upload foto 360° equirectangular & gambar denah.
  - Klik langsung pada denah untuk menaruh titik ruangan.
  - Klik langsung pada foto 360° untuk menaruh panah pindah ruangan.
  - Terintegrasi dengan **GitHub** (penyimpanan file & `data/projects.json`) dan **Cloudflare Pages Functions** (autentikasi password & API sync ke GitHub).

---

## 1. Cara Menjalankan Secara Lokal (Testing di Komputer)

Pastikan Python 3.10+ sudah terpasang, lalu jalankan:

```bash
python dev_server.py
```

Buka di browser:
- **Katalog Projek**: `http://127.0.0.1:8080/`
- **Tur 360° Demo**: `http://127.0.0.1:8080/p/cluster-anggrek`
- **Panel Admin**: `http://127.0.0.1:8080/admin.html` (password default lokal: `admin123`)

---

## 2. Cara Deploy ke GitHub + Cloudflare Pages

1. **Upload / Push** seluruh folder projek ini ke repository GitHub Anda.
2. Buka **Cloudflare Dashboard → Workers & Pages → Create → Pages → Connect to Git**, pilih repository tersebut.
   - **Build command**: *(kosongkan)*
   - **Build output directory**: `/` (root)
3. Masuk ke **Settings → Environment variables** pada projek Cloudflare Pages Anda, lalu tambahkan:
   - `ADMIN_PASSWORD` = password admin pilihan Anda
   - `SESSION_SECRET` = teks acak panjang untuk keamanan cookie sesi
   - `GITHUB_TOKEN` = GitHub Personal Access Token (izin `Contents: Read and Write` pada repo tersebut)
   - `GITHUB_OWNER` = username/organisasi GitHub Anda
   - `GITHUB_REPO` = nama repository GitHub Anda
   - `GITHUB_BRANCH` = `main` (atau branch utama repo Anda)
4. **Redeploy** sekali setelah menambahkan Environment Variables. Selesai! Sekarang setiap kali Anda mengedit projek atau mengupload foto 360° dari `/admin.html`, Cloudflare akan langsung menyimpannya ke GitHub Anda.
