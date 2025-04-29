# **Aplikasi Pencarian Ecommerce Sederhana v0.4**

Versi: 0.4 (Mengirim Traces & Logs via OTLP)  
Tanggal: 29 April 2025

## **1\. Gambaran Umum**

Aplikasi ini adalah sebuah layanan web sederhana yang dibangun menggunakan Python dan Flask. Tujuannya adalah untuk menyediakan antarmuka web bagi pengguna untuk melakukan pencarian data transaksi dari indeks Elasticsearch kibana\_sample\_data\_ecommerce. Aplikasi ini telah diinstrumentasi menggunakan OpenTelemetry untuk mencoba mengirim data *traces* dan *logs* langsung ke Elastic APM Server melalui protokol OTLP/HTTP. Logs diformat menggunakan ECS (Elastic Common Schema) sebelum dikirim.

**Status Saat Ini:** Pengiriman *traces* berhasil dikonfigurasi dan terverifikasi masuk ke Elastic APM. Pengiriman *logs* via OTLP telah diimplementasikan dalam kode, namun **belum terverifikasi berfungsi** dan mungkin memerlukan troubleshooting lebih lanjut di sisi APM Server atau konfigurasi.

## **2\. Fitur Utama**

* Antarmuka web sederhana berbasis HTML untuk memasukkan kueri pencarian.  
* Pencarian *multi-match* pada field yang relevan di indeks Elasticsearch.  
* Menampilkan hasil pencarian dalam format yang mudah dibaca.  
* Konfigurasi koneksi Elasticsearch, Flask, dan OpenTelemetry dikelola melalui file .env.  
* **Integrasi OpenTelemetry**:  
  * Mengirim data **traces** ke backend OpenTelemetry (Elastic APM Server) melalui protokol OTLP/HTTP (Berhasil).  
  * Mencoba mengirim data **logs** (diformat sebagai ECS JSON) ke backend OpenTelemetry (Elastic APM Server) melalui protokol OTLP/HTTP (Status: Belum Terverifikasi).  
  * Secara otomatis menginstrumentasi request Flask dan panggilan ke library elasticsearch-py.  
  * Menginstrumentasi logging Python standar untuk menambahkan trace.id dan span.id ke log secara otomatis.

## **3\. Teknologi yang Digunakan**

* **Bahasa Pemrograman**: Python 3  
* **Web Framework**: Flask  
* **Mesin Pencari**: Elasticsearch  
* **Klien Elasticsearch**: elasticsearch-py  
* **Templating**: Jinja2 (via Flask)  
* **Konfigurasi**: python-dotenv  
* **Observabilitas/Telemetri**:  
  * opentelemetry-api, opentelemetry-sdk  
  * opentelemetry-instrumentation-flask  
  * opentelemetry-instrumentation-elasticsearch  
  * opentelemetry-instrumentation-logging  
  * opentelemetry-exporter-otlp-proto-http  
* **Logging**:  
  * Modul logging standar Python  
  * ecs-logging

## **4\. Struktur Proyek**

simple-search-app/  
├── .env.example           \# Contoh file konfigurasi  
├── .gitignore             \# File yang diabaikan Git  
├── app.py                 \# Kode utama aplikasi  
├── requirements.txt       \# Dependensi Python  
└── templates/  
    ├── index.html         \# Template halaman utama  
    └── results.html       \# Template halaman hasil

## **5\. Setup dan Instalasi**

1. **Prasyarat**:  
   * Python 3.x, pip.  
   * Git (untuk clone dari GitHub).  
   * Akses ke instance Elasticsearch.  
   * Elastic APM Server berjalan, dapat diakses, terhubung ke Elasticsearch, dan dikonfigurasi untuk menerima data OTLP (traces *dan* logs).  
2. **Clone Repository**:  
   git clone \<url\_repository\_github\_anda\>  
   cd simple-search-app

3. **Buat & Aktifkan Virtual Environment**:  
   python \-m venv venv  
   \# Aktivasi (Windows PowerShell): .\\venv\\Scripts\\Activate.ps1  
   \# Aktivasi (Windows CMD): venv\\Scripts\\activate.bat  
   \# Aktivasi (Linux/macOS): source venv/bin/activate

4. **Instal Dependensi**:  
   pip install \-r requirements.txt

5. **Buat File Konfigurasi (.env)**:  
   * Salin file .env.example menjadi .env:  
     \# Windows CMD  
     copy .env.example .env  
     \# Windows PowerShell  
     Copy-Item .env.example .env  
     \# Linux/macOS  
     cp .env.example .env

   * **Edit file .env** dan masukkan nilai konfigurasi yang benar untuk environment Anda (endpoint ES, endpoint APM, kredensial, dll.). Lihat isi .env.example di bawah.  
6. **Jalankan Aplikasi**:  
   python app.py

7. **Akses Aplikasi**: Buka browser ke http://127.0.0.1:5000.

## **6\. File Kode**

Berikut adalah isi dari file-file utama. Anda dapat menemukan file lengkapnya di repositori ini.

### **requirements.txt**

\# requirements.txt

\# Web Framework  
Flask

\# Elasticsearch Client  
elasticsearch\>=8.0.0,\<9.0.0

\# Environment Variables  
python-dotenv

\# \--- OpenTelemetry Core \---  
opentelemetry-api  
opentelemetry-sdk

\# \--- OpenTelemetry Instrumentations \---  
opentelemetry-instrumentation-flask  
opentelemetry-instrumentation-elasticsearch  
opentelemetry-instrumentation-logging \# Untuk korelasi trace-log

\# \--- OpenTelemetry Exporters \---  
\# Mengirim Traces dan Logs via OTLP/HTTP  
opentelemetry-exporter-otlp-proto-http

\# \--- Logging \---  
ecs-logging \# Untuk format log ECS JSON

### **.env.example**

\# .env.example  
\# Salin file ini menjadi .env dan isi nilainya sesuai environment Anda.  
\# JANGAN commit file .env yang berisi kredensial ke Git.

\# \--- Konfigurasi Elasticsearch (Untuk Pencarian) \---  
\# Ganti dengan host ES Anda (bisa https://...)  
ELASTICSEARCH\_HOSTS=http://localhost:9200  
\# Opsional: Jika pakai Basic Auth (hapus \# dan isi nilainya)  
\# ELASTICSEARCH\_USER=elastic  
\# ELASTICSEARCH\_PASSWORD=your\_password\_here  
\# Opsional: Jika pakai API Key (hapus \# dan isi nilainya)  
\# ELASTICSEARCH\_API\_KEY\_ID=your\_api\_key\_id  
\# ELASTICSEARCH\_API\_KEY\_SECRET=your\_api\_key\_secret  
INDEX\_NAME=kibana\_sample\_data\_ecommerce

\# \--- Konfigurasi Flask \---  
\# Ganti dengan kunci rahasia yang kuat dan unik untuk aplikasi Anda\!  
FLASK\_SECRET\_KEY='ganti\_dengan\_kunci\_rahasia\_anda\_yang\_unik\_dan\_aman'

\# \--- Konfigurasi OpenTelemetry (SESUAIKAN DENGAN NILAI ANDA) \---  
\# Nama layanan Anda yang akan muncul di backend OTel  
OTEL\_SERVICE\_NAME=ecommerce-search-app  
\# WAJIB: Endpoint OTLP (URL Dasar APM Server Anda)  
OTEL\_EXPORTER\_OTLP\_ENDPOINT=http://localhost:8200 \# GANTI DENGAN ENDPOINT APM SERVER ANDA (misal: https://\<id\>.apm.\<region\>.aws.cloud.es.io:443)  
\# WAJIB JIKA APM SERVER MEMERLUKAN: Header Otentikasi (hapus \# dan ganti nilainya)  
\# Contoh Secret Token:  
\# OTEL\_EXPORTER\_OTLP\_HEADERS=Authorization=Bearer \<YOUR\_APM\_SECRET\_TOKEN\>  
\# Contoh API Key:  
\# OTEL\_EXPORTER\_OTLP\_HEADERS=Authorization=ApiKey \<YOUR\_BASE64\_ENCODED\_APM\_API\_KEY\>  
\# Atribut Resource Tambahan (Opsional tapi direkomendasikan)  
OTEL\_RESOURCE\_ATTRIBUTES=service.version=0.4.0,deployment.environment=development \# Sesuaikan versi & env  
\# Menandakan penggunaan OTLP untuk logs (opsional, untuk kejelasan)  
\# OTEL\_LOGS\_EXPORTER=otlp

\# \--- Konfigurasi Logging \---  
\# Level log aplikasi (DEBUG, INFO, WARNING, ERROR, CRITICAL)  
APP\_LOG\_LEVEL=INFO

*(File app.py, templates/index.html, templates/results.html, dan .gitignore dapat dilihat langsung di file-file repositori.)*

## **7\. Troubleshooting Logs OTLP**

Jika log tidak muncul di Kibana:

* Periksa log startup aplikasi untuk error terkait OTLPLogExporter.  
* Verifikasi konfigurasi OTEL\_EXPORTER\_OTLP\_ENDPOINT dan OTEL\_EXPORTER\_OTLP\_HEADERS di .env.  
* Periksa log APM Server untuk error saat menerima atau memproses log OTLP.  
* Pastikan APM Server dikonfigurasi untuk menerima log OTLP.  
* Periksa Data View yang benar di Kibana Logs UI.  
* Pertimbangkan kembali ke pendekatan alternatif (mencetak ECS JSON ke stdout dan menggunakan Filebeat).