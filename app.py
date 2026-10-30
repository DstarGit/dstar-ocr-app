import io
import os
import hmac
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract

app = Flask(__name__)

# Ograniczenie rozmiaru przesyłanego pliku (np. max 16MB) w celu ochrony pamięci RAM
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Konfiguracja bezpiecznej sesji opartej o ciasteczka
app.secret_key = os.environ.get('SECRET_KEY', 'b7f8e3a2c5d1e9f4082167d3b5e4a8c2')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif'}
ALLOWED_PIL_FORMATS = {'JPEG', 'PNG', 'GIF'}
MAX_DIMENSION = 2500


def get_current_password() -> str:
    """
    Odczytuje aktualne hasło w locie:
    1. Najpierw sprawdza plik .env (jeśli istnieje, np. zamontowany wolumen /app/.env lub lokalny .env).
    2. W razie braku pliku .env pobiera ze zmiennej środowiskowej APP_PASSWORD.
    """
    env_paths = ['.env', '/app/.env']
    for path in env_paths:
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('APP_PASSWORD=') and not line.startswith('#'):
                            val = line.split('=', 1)[1].strip()
                            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            if val:
                                return val
            except Exception:
                pass

    return os.environ.get('APP_PASSWORD', '111089').strip()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Wymagana autoryzacja hasłem dostępu.',
                    'unauthorized': True
                }), 401
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def is_allowed_file(filename: str, content_type: str) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return False
    if content_type.lower() not in ALLOWED_MIME_TYPES:
        return False
    return True


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('authenticated'):
        return redirect(url_for('index'))

    error = None
    next_url = request.args.get('next') or request.form.get('next') or ''

    if request.method == 'POST':
        submitted_password = request.form.get('password', '').strip()
        expected_password = get_current_password()

        if submitted_password and hmac.compare_digest(submitted_password, expected_password):
            session.permanent = True
            session['authenticated'] = True

            # Zabezpieczenie przed atakami open-redirect
            target = next_url if (next_url.startswith('/') and not next_url.startswith('//')) else url_for('index')
            return redirect(target)
        else:
            error = 'Nieprawidłowe hasło dostępu. Spróbuj ponownie.'

    return render_template('login.html', error=error, next=next_url)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/api/ocr', methods=['POST'])
@login_required
def process_ocr():
    if 'image' not in request.files and 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Brak pliku graficznego w żądaniu (pole "image" lub "file").'
        }), 400

    uploaded_file = request.files.get('image') or request.files.get('file')

    if not uploaded_file or uploaded_file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Nie wybrano żadnego pliku.'
        }), 400

    # 1. Weryfikacja rozszerzenia i MIME type
    if not is_allowed_file(uploaded_file.filename, uploaded_file.content_type):
        return jsonify({
            'success': False,
            'error': 'Nieobsługiwany format pliku. Akceptowane formaty: JPG, JPEG, PNG, GIF.'
        }), 400

    # Opcje przekazane w formularzu
    psm_mode = request.form.get('psm', '4').strip()
    enhance_param = request.form.get('enhance', 'true').strip().lower()
    do_enhance = enhance_param in ('true', '1', 'yes', 'on')

    allowed_psm = {'1', '3', '4', '6', '11'}
    selected_psm = psm_mode if psm_mode in allowed_psm else '4'

    try:
        # 2. Przetwarzanie wyłącznie w pamięci RAM (io.BytesIO)
        file_bytes = uploaded_file.read()
        image_stream = io.BytesIO(file_bytes)

        # 3. Odczyt i weryfikacja nagłówka obrazu przez Pillow
        image = Image.open(image_stream)

        if image.format not in ALLOWED_PIL_FORMATS:
            return jsonify({
                'success': False,
                'error': f'Nieprawidłowa sygnatura pliku obrazu ({image.format}). Dozwolone: JPG, PNG, GIF.'
            }), 400

        # 4. Obsługa GIF - tylko pierwsza klatka + konwersja do RGB
        if image.format == 'GIF':
            image.seek(0)
            image = image.convert('RGB')
        elif image.mode not in ('RGB', 'L'):
            # Obsługa przezroczystości (np. PNG RGBA) - nałożenie na białe tło przed OCR
            if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
                image = image.convert('RGBA')
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            else:
                image = image.convert('RGB')

        # 5. Inteligentny preprocessing pod OCR:
        # Tesseract wymaga wysokości małych liter rzędu 30-33px. Zrzuty ekranu (72-96 DPI) mają litery 12-14px.
        if do_enhance:
            max_side = max(image.width, image.height)
            if max_side < 1200:
                scale_factor = 2.5
            elif max_side < 1700:
                scale_factor = 1.8
            else:
                scale_factor = 1.0

            if scale_factor > 1.0:
                new_w = int(image.width * scale_factor)
                new_h = int(image.height * scale_factor)
                image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Konwersja do skali szarości i autokontrast dla kolorowych/wyblakłych fontów
            image = image.convert('L')
            image = ImageOps.autocontrast(image, cutoff=1)
        else:
            # Standardowe ograniczenie rozmiaru
            if image.width > MAX_DIMENSION or image.height > MAX_DIMENSION:
                image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

        # 6. Ekstrakcja tekstu Tesseract z konfiguracją PSM
        # PSM 4: pojedyncza kolumna zmiennej wielkości tekstu - perfekcyjnie łączy etykietę i wartość w wiersz
        tess_config = f'--psm {selected_psm}'
        text = pytesseract.image_to_string(image, lang='pol+eng', config=tess_config)

        return jsonify({
            'success': True,
            'text': text.strip(),
            'psm_used': selected_psm
        }), 200

    except UnidentifiedImageError:
        return jsonify({
            'success': False,
            'error': 'Przesłany plik jest uszkodzony lub nie jest poprawnym obrazem.'
        }), 400
    except pytesseract.TesseractError as e:
        return jsonify({
            'success': False,
            'error': f'Błąd silnika OCR: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Wystąpił nieoczekiwany błąd podczas przetwarzania: {str(e)}'
        }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'success': False,
        'error': 'Przesłany plik przekracza dozwolony limit rozmiaru (maksymalnie 16MB).'
    }), 413


if __name__ == '__main__':
    # Uruchomienie deweloperskie
    app.run(host='0.0.0.0', port=5000, debug=False)
