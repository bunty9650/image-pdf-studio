# ⚡ All-in-One Image & PDF Studio (Local Python Tool)

A high-performance, 100% locally runnable Python tool suite to convert, compress, format change, and stitch images and PDFs without relying on any external internet or third-party servers.

---

## 🌟 Features (Aapki Sabhi Requirements Ka Solution)

1. **Image to PDF (Kisi Bhi Format Wali File)**
   - Single image ya multiple images ko ek crisp PDF document me convert karein.
   - **Sequence Change:** Move Up, Move Down, aur 1-Click Reverse order options.
   - **Preview:** Kisi bhi image par click karke full HD preview modal dekhein.
   - Page formats: `Fit Image (Original)`, `A4`, `Letter`.

2. **Merge PDF Documents (PDFs Ko Merge Karein - NEW!)**
   - 2 ya usse zyada PDF files ko ek single document me merge karein.
   - Merge karne se pehle **Sequence (Order) Change** karein.
   - **Multi-page PDF Viewer:** Kisi bhi PDF ke pages ko Previous/Next buttons se flip karke inspect karein.

3. **PDF to Images (Kisi Bhi PDF Ko High Quality Images Me)**
   - PDF ke pages ko high-resolution images me extract karein (PNG lossless, JPG, WEBP).
   - Clarity / DPI Selection: **150 DPI (Standard)**, **300 DPI (High Clarity)**, ya **600 DPI (Ultra Print Sharpness)**.
   - PDF ko preview karne ka live button.

4. **Smart Size Compression (Image Aur PDF Dono Ke Liye)**
   - **Manual Target Size (KB / MB):** Exact target size enter karein (jaise `200 KB` ya `1.5 MB`). Smart binary search quality aur dimensions optimize karke target size achieve karta hai.
   - **Quality Percentage Slider:** 10% se 95% quality control.

5. **Image Format Converter (Format Change Karein)**
   - Formats: `JPG`, `PNG`, `WEBP`, `BMP`, `TIFF`, `ICO`.
   - Transparency automatically white background par composite hoti hai.

6. **2 to 5 Images Ko Clarity Ke Sath Merge / Stitch Karein**
   - **Live Alignment Graphics Canvas:** Images merge hone se pehle screen par live layout diagram dikhta hai!
   - Sequence change karein (Move Up, Move Down, Reverse).
   - Horizontal aur Vertical alignment with pure Lanczos scaling.

---

## 🚀 How to Run (Kaise Chalayein)

Aapke pas 3 aasan tarike hain:

### Option 1: Desktop Application (GUI) - Recommended
Bas folder me jaakar **`run_gui.bat`** (ya **`run.bat`**) par double-click karein:
```bash
python gui_app.py
```
Ek modern, responsive desktop window open ho jayegi jisme tabs ke sath sabhi tools uplabdh hain.

---

### Option 2: Web Browser UI (Chrome / Edge / Firefox)
Agar aapko Drag & Drop aur Browser me chalana pasand hai:
Bas **`run_web.bat`** par double click karein (ya terminal me):
```bash
python web_app.py
```
Aapka default browser automatically open ho jayega (`http://127.0.0.1:5000`).

---

### Option 3: Command-Line (CLI)
Terminal ya script se use karne ke liye `cli.py` uplabdh hai:

```bash
# 1. Images to PDF
python cli.py img2pdf photo1.jpg photo2.png -o output.pdf --page-size A4

# 2. PDF to Images (300 DPI high clarity)
python cli.py pdf2img document.pdf -o output_images --format png --dpi 300

# 3. Compress Image ya PDF to 250 KB
python cli.py compress scanned.pdf -o compressed.pdf --target-kb 250
python cli.py compress photo.jpg -o photo_small.jpg --target-kb 200

# 4. Format Convert (JPG to WEBP)
python cli.py format image.jpg -o image.webp --format webp

# 5. Merge 2 to 5 images horizontally with 10px gap
python cli.py merge img1.png img2.png img3.png -o stitched.png --direction horizontal --gap 10
```

---

## 📁 Project Files Structure

| File | Kaam (Description) |
|---|---|
| `converter_core.py` | Pure Python processing engine (Pillow + PyMuPDF) |
| `ui_assets.py` | High-definition vector icon engine (Runtime anti-aliased icons, zero emojis) |
| `gui_app.py` | Premium Desktop GUI App (Dark modern sidebar + visual file cards) |
| `web_app.py` | Premium Local Web UI with SVG icons & Drag & Drop |
| `cli.py` | Command line interface for batch scripting |
| `run.bat` | Interactive launcher menu |
| `run_gui.bat` | One-click Desktop GUI launcher |
| `run_web.bat` | One-click Web Browser launcher |
| `test_converter_core.py` | Automated unit tests |
| `requirements-desktop.txt` | Local Python dependencies list (`pillow`, `pymupdf`) |

---

## 🔒 100% Offline & Secure
Sabhi operations aapke computer par locally run hote hain. Koi bhi file kisi bhi external server ya internet par upload nahi hoti hai.
