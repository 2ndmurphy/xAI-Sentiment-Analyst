# Web Scraping Twitter with Playwright

## 📖 Deskripsi
Proyek ini adalah aplikasi Python untuk melakukan web scraping pada platform **Twitter (X)** menggunakan **Playwright**. Aplikasi ini dirancang untuk mengambil tweet berdasarkan kata kunci pencarian tertentu, memproses teksnya, dan menyimpan hasilnya ke dalam file CSV. Proyek ini dapat digunakan untuk analisis sentimen, pengumpulan data, atau riset lainnya.

---

## 🎯 Tujuan
- Mengotomatisasi pengambilan data tweet berdasarkan kata kunci tertentu.
- Membersihkan teks tweet menggunakan preprocessing.
- Menyimpan data hasil scraping ke dalam format CSV untuk analisis lebih lanjut.

---

## 🔗 Referensi
- [Playwright Documentation](https://playwright.dev/python/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Uv Package Manager](https://docs.astral.sh/uv/)

---

## ✨ Fitur
- **Scraping Tweet**: Mengambil tweet terbaru berdasarkan kata kunci pencarian.
- **Preprocessing Teks**: Membersihkan teks tweet untuk analisis lebih lanjut.
- **Batch Save**: Menyimpan data secara bertahap untuk efisiensi.
- **Cookie Management**: Mendukung login otomatis menggunakan file cookie.
- **Konfigurasi Mudah**: Parameter seperti jumlah tweet dan batch size dapat diatur.

---

## 🛠️ Tools yang Digunakan
- **Python 3.9+**
- **Playwright**: Untuk scraping data dari Twitter.
- **Pandas**: Untuk manipulasi dan penyimpanan data.
- **Asyncio**: Untuk menjalankan proses scraping secara asinkron.
- **JSON**: Untuk manajemen file cookie.

---

## 🚀 Cara Memulai Proyek

### 1. **Clone Repository**
```bash
git clone https://github.com/username/webscraping_v2.git
cd webscraping_v2
```

### 2. **Install Dependencies**
Pastikan Anda sudah menginstall Uv 0.7+, python 3.9+, dan pip. Kemudian, jalankan:
```bash
uv sync
```

### 3. **Activate Virtual Environment**
```bash
source .venv/Script/activate
```

### 4. **Setup Playwright**
```bash
playwright install
```

### 5. **Konfigurasi**

- File Cookie: Pastikan file cookies.json sudah tersedia di root folder.
- Parameter Scraping: Ubah konfigurasi
seperti kata kunci pencarian (SEARCH_QUERIES) di file main.py.

### 5. **Jalankan Program**
```bash
uv run main.py
```

```text
webscraping_v2
├── helpers
│   ├── __init__.py
│   ├── csv_helpers.py
│   ├── scraper.py
│   └── preprocess.py
├── main.py
├── cookies.json
├── tweets_sentiment.csv
└── README.md
```
