# app.py
import os
import logging
import sys
import re

from flask import Flask, render_template, request, flash
from elasticsearch import Elasticsearch, ConnectionError, NotFoundError
from dotenv import load_dotenv

# --- OpenTelemetry Core Imports ---
from opentelemetry import trace
from opentelemetry import _logs as otel_logs
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor # Pastikan ini diimpor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
# Import exporter OTLP untuk traces
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
# Coba impor log exporter
try:
    from opentelemetry.exporter.otlp.proto.http.log_exporter import OTLPLogExporter
except ImportError:
    try:
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        print("Berhasil mengimpor OTLPLogExporter dari path alternatif.")
    except ImportError:
        print("WARNING: Tidak dapat menemukan OTLPLogExporter. Pengiriman log via OTLP dinonaktifkan.")
        # Set ke None agar konfigurasi log OTel dilewati
        OTLPLogExporter = None


from opentelemetry.sdk.resources import Resource, SERVICE_NAME

# --- OpenTelemetry Instrumentor Imports ---
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# --- ECS Logging Import ---
import ecs_logging # Tetap gunakan untuk memformat log record

# Muat variabel dari file .env
load_dotenv()

# --- Dapatkan Konfigurasi dari Environment ---
otel_service_name = os.getenv('OTEL_SERVICE_NAME', 'ecommerce-search-app')
log_level_str = os.getenv('APP_LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
otel_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
otel_headers = os.getenv('OTEL_EXPORTER_OTLP_HEADERS')
otel_res_attrs_str = os.getenv('OTEL_RESOURCE_ATTRIBUTES', '')

# --- Validasi Konfigurasi Penting ---
if not otel_endpoint:
    print("FATAL: Variabel environment OTEL_EXPORTER_OTLP_ENDPOINT belum diatur! Tidak dapat mengirim telemetri.")
    sys.exit(1)

# --- Konfigurasi Resource OpenTelemetry ---
resource_attributes = {
    SERVICE_NAME: otel_service_name,
}
if otel_res_attrs_str:
    try:
        parsed_attrs = dict(pair.split('=', 1) for pair in otel_res_attrs_str.split(','))
        resource_attributes.update(parsed_attrs)
    except ValueError:
        print(f"WARNING: Gagal mem-parsing OTEL_RESOURCE_ATTRIBUTES: '{otel_res_attrs_str}'.")
resource = Resource(attributes=resource_attributes)

# --- Konfigurasi Pipeline OpenTelemetry Tracing ---
trace_provider = TracerProvider(resource=resource)
exporter_headers_dict = {}
if otel_headers:
    try:
        if '=' in otel_headers:
             key, value = otel_headers.split('=', 1)
             exporter_headers_dict[key.strip()] = value.strip()
        else:
             print(f"WARNING: Format OTEL_EXPORTER_OTLP_HEADERS tidak dikenali: '{otel_headers}'")
    except Exception as e:
        print(f"WARNING: Gagal mem-parsing OTEL_EXPORTER_OTLP_HEADERS: {e}")

try:
    trace_exporter = OTLPSpanExporter(
        endpoint=otel_endpoint, # SDK akan menambahkan /v1/traces
        headers=exporter_headers_dict if exporter_headers_dict else None
    )
    trace_processor = BatchSpanProcessor(trace_exporter)
    trace_provider.add_span_processor(trace_processor)
    trace.set_tracer_provider(trace_provider)
    print(f"OpenTelemetry Tracing dikonfigurasi. Exporter: OTLPSpanExporter, Endpoint: {otel_endpoint}")
    if exporter_headers_dict:
        print("Header otentikasi OTLP untuk Traces dikonfigurasi.")
except Exception as e:
    print(f"ERROR: Gagal mengkonfigurasi OTLP Trace Exporter: {e}")

# --- Konfigurasi Pipeline OpenTelemetry Logging ---
log_provider = LoggerProvider(resource=resource)
log_exporter = None # Inisialisasi
if OTLPLogExporter: # Hanya konfigurasi jika exporter berhasil diimpor
    try:
        log_exporter = OTLPLogExporter(
            endpoint=otel_endpoint, # SDK akan menambahkan /v1/logs
            headers=exporter_headers_dict if exporter_headers_dict else None
        )
        log_processor = BatchLogRecordProcessor(log_exporter)
        log_provider.add_log_record_processor(log_processor)
        otel_logs.set_logger_provider(log_provider)
        print(f"OpenTelemetry Logging dikonfigurasi. Exporter: OTLPLogExporter, Endpoint: {otel_endpoint}")
        if exporter_headers_dict:
            print("Header otentikasi OTLP untuk Logs dikonfigurasi.")
    except Exception as e:
        print(f"ERROR: Gagal mengkonfigurasi OTLP Log Exporter: {e}")
        log_exporter = None # Set ke None jika gagal
else:
    # Pesan ini sudah dicetak saat import gagal
    pass


# --- Konfigurasi Logging Python Standar ---
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.handlers.clear()

ecs_formatter = ecs_logging.StdlibFormatter()

# Tentukan handler: OTel jika berhasil, jika tidak kembali ke stdout
if log_exporter: # Jika OTel Log Exporter berhasil dibuat
    otel_handler = LoggingHandler(level=log_level, logger_provider=log_provider)
    otel_handler.setFormatter(ecs_formatter)
    root_logger.addHandler(otel_handler)
    # Gunakan logger setelah dikonfigurasi
    logger_init = logging.getLogger(otel_service_name)
    logger_init.info("Logging Python dikonfigurasi untuk mengirim logs via OTLP dengan format ECS.")
else: # Fallback ke stdout jika OTel log gagal
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(ecs_formatter)
    root_logger.addHandler(stdout_handler)
    # Gunakan logger setelah dikonfigurasi
    logger_init = logging.getLogger(otel_service_name)
    logger_init.info("Logging Python dikonfigurasi untuk mencetak format ECS ke stdout (OTLP Log Exporter gagal/tidak ditemukan).")

# Dapatkan logger utama untuk digunakan di seluruh aplikasi
logger = logging.getLogger(otel_service_name)
logger.info(f"Log level diatur ke: {log_level_str}") # Log ini sekarang akan dikirim/dicetak


# --- Instrumentasi OpenTelemetry ---
try:
    LoggingInstrumentor().instrument(
        set_logging_format=False,
        tracer_provider=trace_provider,
        logger_provider=log_provider if log_exporter else None
    )
    logger.info("OpenTelemetry LoggingInstrumentor diaktifkan untuk korelasi.")
except Exception as e:
    logger.error(f"Gagal mengaktifkan LoggingInstrumentor: {e}", exc_info=True)


tracer = trace.get_tracer(__name__)

# --- Aplikasi Flask ---
app = Flask(__name__)

try:
    FlaskInstrumentor().instrument_app(app, tracer_provider=trace_provider)
    logger.info("OpenTelemetry FlaskInstrumentor diaktifkan.")
except Exception as e:
    logger.error(f"Gagal mengaktifkan FlaskInstrumentor: {e}", exc_info=True)


app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key_for_dev_only')
if app.secret_key == 'default_secret_key_for_dev_only' or \
   app.secret_key == 'ganti_dengan_kunci_rahasia_anda_yang_unik_dan_aman':
    logger.warning("FLASK_SECRET_KEY belum diatur dengan aman di file .env!")


# --- Konfigurasi Elasticsearch ---
es_hosts_str = os.getenv('ELASTICSEARCH_HOSTS')
es_user = os.getenv('ELASTICSEARCH_USER')
es_password = os.getenv('ELASTICSEARCH_PASSWORD')
es_api_key_id = os.getenv('ELASTICSEARCH_API_KEY_ID')
es_api_key_secret = os.getenv('ELASTICSEARCH_API_KEY_SECRET')
index_name = os.getenv('INDEX_NAME', 'kibana_sample_data_ecommerce')

es_client = None

if not es_hosts_str:
    logger.error("ELASTICSEARCH_HOSTS tidak ditemukan di file .env atau environment.")
else:
    es_hosts = es_hosts_str.split(',')
    try:
        auth_params = {}
        auth_method = "tanpa otentikasi khusus"
        if es_api_key_id and es_api_key_secret:
            auth_params['api_key'] = (es_api_key_id, es_api_key_secret)
            auth_method = "API Key"
        elif es_user and es_password:
            auth_params['basic_auth'] = (es_user, es_password)
            auth_method = "Basic Auth"

        logger.info(f"Mencoba menghubungkan ke Elasticsearch di {es_hosts} menggunakan {auth_method}.")

        es_client = Elasticsearch(
            hosts=es_hosts,
            **auth_params
        )

        try:
            ElasticsearchInstrumentor().instrument(tracer_provider=trace_provider)
            logger.info("OpenTelemetry ElasticsearchInstrumentor diaktifkan.")
        except Exception as instr_err:
             logger.warning(f"Gagal mengaktifkan ElasticsearchInstrumentor: {instr_err}. Mungkin tidak diperlukan jika versi library sudah mendukung OTel bawaan.")

        if not es_client.ping():
            logger.error(f"Koneksi ping ke Elasticsearch di {es_hosts} GAGAL!")
            es_client = None
        else:
            logger.info(f"Berhasil terhubung (ping) ke Elasticsearch di {es_hosts}!")

    except ConnectionError as e:
        logger.error(f"Gagal terhubung ke Elasticsearch di {es_hosts}: {e}", exc_info=True)
        es_client = None
    except Exception as e:
        logger.error(f"Terjadi error saat menginisialisasi koneksi Elasticsearch: {e}", exc_info=True)
        es_client = None


# --- Rute Flask ---
@app.route('/')
def index():
    """Menampilkan halaman utama dengan form pencarian."""
    logger.debug(f"Request diterima untuk endpoint: {request.path}")
    if not es_client:
        flash("Koneksi ke server Elasticsearch gagal dikonfigurasi atau tidak berhasil.")
        logger.warning("Menampilkan halaman index, tetapi koneksi ES tidak aktif.")
    return render_template('index.html')

@app.route('/search')
def search():
    """Menangani request pencarian dan menampilkan hasil."""
    logger.debug(f"Request diterima untuk endpoint: {request.path}")
    current_span = trace.get_current_span()

    if not es_client:
        flash("Tidak dapat terhubung ke server Elasticsearch.")
        logger.error("Pencarian gagal karena koneksi ES tidak aktif.")
        if current_span and current_span.is_recording():
             current_span.set_status(trace.StatusCode.ERROR, "Koneksi Elasticsearch tidak aktif")
        return render_template('results.html', query=request.args.get('query', ''), results=[], error="Tidak dapat terhubung ke server Elasticsearch.")

    query = request.args.get('query', '')
    results = []
    error_message = None

    if current_span and current_span.is_recording():
        current_span.set_attribute("app.search.query", query)

    if not query:
        flash("Silakan masukkan kata kunci pencarian.")
        logger.warning("Pencarian tidak dilakukan karena query kosong.")
        return render_template('index.html')

    logger.info(f"Melakukan pencarian untuk query: '{query}'")
    search_fields = ["customer_full_name", "email", "products.product_name", "category", "manufacturer"]
    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": search_fields,
                "fuzziness": "AUTO"
            }
        },
        "size": 50
    }

    try:
        response = es_client.search(index=index_name, body=search_body)
        results = response['hits']['hits']
        logger.info(f"Pencarian untuk '{query}' berhasil, ditemukan {len(results)} hasil.")
        if current_span and current_span.is_recording():
            current_span.set_attribute("app.search.results_count", len(results))

    except ConnectionError as e:
        error_message = "Gagal terhubung ke Elasticsearch saat melakukan pencarian."
        logger.error(f"{error_message}: {e}", exc_info=True)
    except NotFoundError as e:
        error_message = f"Indeks '{index_name}' tidak ditemukan di Elasticsearch."
        logger.error(f"{error_message}: {e}", exc_info=True)
    except Exception as e:
        error_message = f"Terjadi kesalahan saat melakukan pencarian: {e}"
        logger.error(error_message, exc_info=True)
        if "security_exception" in str(e).lower():
             error_message = "Kesalahan otentikasi saat menghubungi Elasticsearch. Periksa kredensial di file .env."
             logger.error("Kemungkinan error otentikasi Elasticsearch.")

    if error_message and current_span and current_span.is_recording():
        current_span.set_attribute("app.search.error", error_message)
        current_span.set_status(trace.StatusCode.ERROR, description=error_message)

    return render_template('results.html', query=query, results=results, error=error_message)

# --- Main Execution ---
if __name__ == '__main__':
    if app.secret_key == 'default_secret_key_for_dev_only' or \
       app.secret_key == 'ganti_dengan_kunci_rahasia_anda_yang_unik_dan_aman':
        logger.warning("\n\n *** PERINGATAN: JANGAN GUNAKAN FLASK_SECRET_KEY DEFAULT DI PRODUCTION! ***\n\n")

    logger.info(f"Menjalankan aplikasi Flask '{app.name}'...")
    logger.info(f"OpenTelemetry Service Name: {otel_service_name}")
    if 'trace_exporter' in locals():
        logger.info(f"OpenTelemetry Trace Exporter: {trace_exporter.__class__.__name__}")
    if 'log_exporter' in locals() and log_exporter:
        logger.info(f"OpenTelemetry Log Exporter: {log_exporter.__class__.__name__}")
    else:
        logger.warning("OpenTelemetry Log Exporter tidak aktif.")


    # Gunakan use_reloader=False saat menggunakan OTel, terutama dalam mode debug
    # Hapus host/port agar default Flask (127.0.0.1:5000) digunakan
    app.run(debug=True, use_reloader=False) # debug=False untuk production

