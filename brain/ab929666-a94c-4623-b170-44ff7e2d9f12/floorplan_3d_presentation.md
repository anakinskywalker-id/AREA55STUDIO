# Model 3D Arsitektur: Ground Floor Plan

Berdasarkan denah denah arsitektur (*Ground Floor Plan*), model 3D telah berhasil dibangun secara presisi dengan skala 1:1 (dimensi total bangunan sekitar **30.7 m × 10.2 m**). Sesuai instruksi, fokus pemodelan ditujukan pada elemen struktur utama: **dinding (walls), pintu & kusen (doors & frames), jendela & dinding kaca (windows & glass walls), serta lantai (floors per zone)** tanpa elemen furniture dan vegetasi.

---

## 📸 Galeri Render 3D

````carousel
![Isometrik Tampak Tenggara (South-East)](C:/Users/Ust. Udin/.gemini/antigravity/brain/ab929666-a94c-4623-b170-44ff7e2d9f12/render_isometric_se.png)
<!-- slide -->
![Isometrik Tampak Barat Daya (South-West)](C:/Users/Ust. Udin/.gemini/antigravity/brain/ab929666-a94c-4623-b170-44ff7e2d9f12/render_isometric_sw.png)
<!-- slide -->
![Tampak Atas 3D (Top-Down Axonometric)](C:/Users/Ust. Udin/.gemini/antigravity/brain/ab929666-a94c-4623-b170-44ff7e2d9f12/render_topdown.png)
<!-- slide -->
![Perspektif Cutaway](C:/Users/Ust. Udin/.gemini/antigravity/brain/ab929666-a94c-4623-b170-44ff7e2d9f12/render_perspective.png)
<!-- slide -->
![Detail Courtyard Tengah & Dinding Kaca](C:/Users/Ust. Udin/.gemini/antigravity/brain/ab929666-a94c-4623-b170-44ff7e2d9f12/render_courtyard.png)
````

---

## 🏛️ Detail Elemen yang Dimodelkan

| Komponen | Spesifikasi & Detail Pemodelan |
| :--- | :--- |
| **Dinding (Walls)** | Dinding keliling eksterior (tebal 20 cm) dan partisi interior (tebal 15 cm) dengan tinggi cutaway 2.8 m. Dilengkapi balok lintel di atas pintu/jendela untuk keterbacaan ruang 3D yang optimal. |
| **Pintu (Doors)** | Kusen aluminium gelap (*dark bronze/black*), daun pintu panel kayu solid modern dengan bukaan sudut dinamis (25°-35°) dan handel pintu stainless steel. Pintu gerbang utama (*Main Entrance Gate 01*) dimodelkan dengan kisi-kisi modern. |
| **Jendela & Dinding Kaca (Windows)** | Dinding kaca geser (*sliding glass doors*) dari lantai ke plafon mengelilingi seluruh area *inner courtyard*, jendela *ribbon/clerestory* sepanjang koridor utara (09), serta jendela lebar kamar tidur anak (18) menghadap taman belakang. |
| **Lantai (Floors)** | Dibuat terpisah per zona fungsional dengan material berbeda:<br>• **Parkir (02):** Paving blok / beton eksterior.<br>• **Teras Depan (03):** Decking kayu jati luar ruangan (*timber slats*).<br>• **Ruang Makan & Dapur (06/07), Lobby (04), Koridor (09):** Terrazzo / ubin porselen poles terang.<br>• **Kamar Tidur (12, 18) & Workspace (11):** Parquet kayu oak natural.<br>• **Kamar Mandi (05, 14):** Ubin batu alam *slate* abu-abu.<br>• **Courtyard & Taman (10):** Hamparan kerikil (*gravel bed*) dengan batu pijakan (*stepping stones*).<br>• **Bathtub Luar (15):** Decking kayu dan bathtub oval keramik. |

---

## 📁 File Proyek 3D

Seluruh file model telah disimpan dan siap digunakan:

1. **File Blender (.blend):**  
   [house_floorplan_3d.blend](file:///C:/Users/Ust.%20Udin/.gemini/antigravity/scratch/floorplan_3d/house_floorplan_3d.blend)  
   *(Lengkap dengan susunan Outliner per Collection: Walls, Doors, Windows, Floors, Fixtures, Staging, kamera, dan pencahayaan)*.
2. **File Format Universal (.glb):**  
   [house_floorplan_3d.glb](file:///C:/Users/Ust.%20Udin/.gemini/antigravity/scratch/floorplan_3d/house_floorplan_3d.glb)  
   *(Dapat dibuka langsung di 3D Viewer bawaan Windows, web viewer, atau diimpor ke software 3D lain)*.
3. **Skrip Generator Python:**  
   [build_model.py](file:///C:/Users/Ust.%20Udin/.gemini/antigravity/scratch/floorplan_3d/build_model.py)
