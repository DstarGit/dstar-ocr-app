# Mikrus OCR App 🔍

Lekka, zoptymalizowana i zabezpieczona hasłem aplikacja webowa do rozpoznawania tekstu (OCR) oparta na **Python 3.11**, **Flask**, **Pillow**, **pytesseract** i **Docker**, przygotowana specjalnie pod mikrowęzły VPS o ograniczonych zasobach (np. **Mikrus**).

---

## 🚀 Kluczowe cechy i optymalizacje pod Mikrusa

1. **Przetwarzanie wyłącznie w pamięci RAM (`io.BytesIO`)**:
   - Zero operacji dyskowych I/O na VPS – brak tymczasowych plików na dysku.
2. **Ochrona przed wyczerpaniem pamięci (OOM)**:
   - Obrazy o wymiarach powyżej **2000×2000 px** są automatycznie i proporcjonalnie zmniejszane przed analizą OCR.
   - Ścisły limit pamięci w `docker-compose.yml` (`mem_limit: 512m`, `reservations: 128m`).
3. **Zaawansowane przetwarzanie i wysoka dokładność OCR**:
   - **Inteligentne skalowanie (DPI Boost 2.5x)**: Dla małych czcionek i zrzutów ekranu (np. tabele serwerowe, specyfikacje) aplikacja skaluje obraz algorytmem `LANCZOS` i wyrównuje kontrast (`ImageOps.autocontrast`), co zapobiega gubieniu znaków i krótkich słów (np. *SAS*, *HP*, *Up*).
   - **Wybór układu tekstu (Tesseract PSM)**:
     - `PSM 4`: Kolumny o zmiennej szerokości / tabele klucz-wartość (domyślny – idealny do zrzutów ekranu i formularzy).
     - `PSM 6`: Jednolity blok tekstu (akapity, artykuły, notatki).
     - `PSM 3`: W pełni automatyczna segmentacja (domyślny tryb Tesseracta).
     - `PSM 11`: Rzadki tekst / szukanie pojedynczych napisów.
4. **Zabezpieczenie hasłem dostępu**:
   - Dostęp do aplikacji jest chroniony pojedynczym polem hasła (bez loginu).
   - Zaszyfrowane ciasteczka sesji (`Flask Session`, `HttpOnly`, `SameSite=Lax`).
   - Dynamiczne pobieranie hasła z pliku `.env` (`APP_PASSWORD`).
5. **Optymalizacja animowanych GIF-ów**:
   - Wyodrębnianie wyłącznie pierwszej klatki (`image.seek(0)`) i konwersja do RGB – zapobiega alokacji pamięci dla wszystkich klatek animacji.
6. **Wielojęzyczność**:
   - Tesseract z pakietami języka polskiego i angielskiego (`lang='pol+eng'`).
7. **Lekki obraz Docker**:
   - Oparty na `python:3.11-slim` z czyszczeniem pamięci podręcznej pakietów `apt` i `pip`.
8. **Produkcyjny serwer WSGI**:
   - `gunicorn` skonfigurowany pod 2 workery (`-w 2`) z limitem czasu (`timeout 60s`).

---

## 📁 Struktura projektu

```text
mikrus-ocr-app/
├── app.py                  # Główna aplikacja Flask (autoryzacja, preprocess, OCR, API)
├── requirements.txt        # Zależności Pythona (Flask, Pillow, pytesseract, gunicorn, python-dotenv)
├── Dockerfile              # Lekki obraz z Tesseract OCR (pol+eng)
├── docker-compose.yml      # Konfiguracja z limitem RAM (512MB) i wolumenami na kod/.env
├── .env                    # Aktywna konfiguracja (hasło, port, secret key)
├── .env.example            # Przykładowy szablon zmiennych środowiskowych
├── .dockerignore           # Pliki wykluczone z budowania obrazu
├── templates/
│   ├── login.html          # Minimalistyczny ekran logowania (jedno pole hasła)
│   └── index.html          # Dwukolumnowy interfejs OCR z opcjami ulepszeń i układu
└── static/
    ├── css/
    │   └── style.css       # Responsywne style UI z ciemnym motywem i panelem opcji
    └── js/
        └── app.js          # Obsługa Drag & Drop, walidacja, schowek i asynchroniczny OCR
```

---

## ⚙️ Konfiguracja zmiennych środowiskowych (`.env`)

Przed uruchomieniem aplikacji skonfiguruj plik `.env`:

```ini
# Port na którym ma działać aplikacja (domyślnie 5000 lub port Mikrusa np. 20211)
OCR_PORT=20211

# Hasło dostępu do aplikacji (jedno pole w formularzu)
APP_PASSWORD=twoje_tajne_haslo

# Klucz do podpisywania sesji Flask (losowy ciąg znaków)
SECRET_KEY=wygenerowany_tajny_klucz_sesji
```

> **Zmiana hasła:** Po edycji `APP_PASSWORD` w pliku `.env` wystarczy zrestartować kontener: `docker compose restart` (trwa ~1 sekundę).

---

## 🚀 Szybki start (Docker Compose)

### 1. Przejście do katalogu projektu na serwerze Mikrus
```bash
cd /root/MCPAPPS/ocr-app
```

### 2. Skonfigurowanie pliku `.env`
```bash
cp .env.example .env
nano .env
```

### 3. Zbudowanie i uruchomienie kontenera w tle
```bash
docker compose up -d --build
```

### 4. Sprawdzenie statusu i zużycia zasobów
```bash
docker compose ps
docker stats mikrus_ocr_app
```
*(Aplikacja zużywa zaledwie około 60-80 MB pamięci RAM)*

Podgląd logów w czasie rzeczywistym:
```bash
docker compose logs -f
```

---

## 🌐 Uruchomienie lokalne (bez Dockera)

1. Zainstaluj silnik Tesseract OCR z obsługą języków polskiego i angielskiego:
   - **Ubuntu/Debian**:
     ```bash
     sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng
     ```
   - **macOS**:
     ```bash
     brew install tesseract tesseract-lang
     ```
   - **Windows**:
     Pobierz instalator z [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) i dodaj Tesseract do zmiennej PATH.

2. Utwórz i aktywuj środowisko wirtualne:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate   # Windows
   ```

3. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```

4. Uruchom serwer produkcyjny (Linux/macOS):
   ```bash
   gunicorn -w 2 -b 0.0.0.0:5000 app:app
   ```
   Lub dewelopersko:
   ```bash
   python app.py
   ```

---

## 🔌 API REST (`/api/ocr`)

Endpoint REST API do zautomatyzowanego rozpoznawania tekstu:

- **Metoda**: `POST`
- **Ścieżka**: `/api/ocr`
- **Content-Type**: `multipart/form-data`
- **Autoryzacja**: Aktywna sesja (ciasteczko sesji po `/login`)
- **Pola formularza**:
  - `image` (lub `file`) [wymagane]: Plik graficzny (`.jpg`, `.jpeg`, `.png`, `.gif`)
  - `psm` [opcjonalne]: Tryb segmentacji Tesseract (`4` [domyślny], `6`, `3`, `11`)
  - `enhance` [opcjonalne]: `true` lub `false` (włącza skalowanie 2.5x i auto-kontrast)

### Przykładowa odpowiedź poprawna (`HTTP 200`):
```json
{
  "success": true,
  "text": "Disk Information\n\nLocation: 1.10\nSerial Number: 59P0A045FA1F\nUsage: Pool A, Standard Tier\nType: SAS\nSize: 600GB\nStatus: Up\nr/min: 15k\nManufacturer: HP\nModel: EH000600JWHPN\nRevision: HPD4\nPower On Hours: 62728\nFDE State: Not FDE Capable\nFDE Lock Key: 00000000\nSector Format: 512n\nTransfer Rate: 6.0\nSMART: Enabled\nDrive Spin Down Count: 1"
}
```

### Przykładowa odpowiedź błędu braku autoryzacji (`HTTP 401`):
```json
{
  "success": false,
  "unauthorized": true,
  "error": "Wymagana autoryzacja hasłem dostępu."
}
```
