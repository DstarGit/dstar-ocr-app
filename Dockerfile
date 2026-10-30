FROM python:3.11-slim

# Metadane i optymalizacja Pythona
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalacja Tesseract OCR oraz pakietów językowych (polski + angielski)
# Czyszczenie cache apt, aby zminimalizować rozmiar obrazu na VPS Mikrus
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-pol \
    tesseract-ocr-eng \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalacja zależności Python z flagą --no-cache-dir
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu aplikacji
COPY . .

# Tworzenie bezpiecznego użytkownika nieuprzywilejowanego
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Otwarcie portu kontenera
EXPOSE 5000

# Produkcyjne uruchomienie przez Gunicorn z 2 workerami i limitem czasu
CMD ["gunicorn", "--workers=2", "--bind=0.0.0.0:5000", "--timeout=60", "--access-logfile=-", "--error-logfile=-", "app:app"]
