document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const dropzoneDefault = document.getElementById('dropzoneDefault');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const btnChangeFile = document.getElementById('btnChangeFile');
    const btnProcess = document.getElementById('btnProcess');
    const btnSpinner = document.getElementById('btnSpinner');
    const clientError = document.getElementById('clientError');
    const resultText = document.getElementById('resultText');
    const btnCopy = document.getElementById('btnCopy');
    const copyBtnText = document.getElementById('copyBtnText');
    const btnClear = document.getElementById('btnClear');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const statsWordCount = document.getElementById('statsWordCount');
    const statsCharCount = document.getElementById('statsCharCount');

    let currentFile = null;

    // Dozwolone rozszerzenia i typy MIME
    const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif'];
    const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif'];

    // Formatowanie rozmiaru pliku
    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Walidacja pliku po stronie klienta
    function validateFile(file) {
        if (!file) return false;

        const name = file.name.toLowerCase();
        const hasValidExt = ALLOWED_EXTENSIONS.some(ext => name.endsWith(ext));
        const hasValidMime = ALLOWED_MIME_TYPES.includes(file.type.toLowerCase());

        if (!hasValidExt && !hasValidMime) {
            showError('Niedozwolony format pliku! Wybierz plik z rozszerzeniem .jpg, .jpeg, .png lub .gif.');
            return false;
        }

        // Limit rozmiaru np. 16MB
        if (file.size > 16 * 1024 * 1024) {
            showError('Rozmiar pliku przekracza dopuszczalny limit 16MB.');
            return false;
        }

        hideError();
        return true;
    }

    function showError(message) {
        clientError.textContent = message;
        clientError.style.display = 'block';
    }

    function hideError() {
        clientError.textContent = '';
        clientError.style.display = 'none';
    }

    function setSelectedFile(file) {
        if (!validateFile(file)) {
            clearSelectedFile();
            return;
        }

        currentFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = `(${formatBytes(file.size)})`;

        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            dropzoneDefault.style.display = 'none';
            previewContainer.style.display = 'flex';
            btnProcess.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function clearSelectedFile() {
        currentFile = null;
        fileInput.value = '';
        imagePreview.src = '';
        dropzoneDefault.style.display = 'block';
        previewContainer.style.display = 'none';
        btnProcess.disabled = true;
    }

    // Drag and drop event listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('drag-active');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('drag-active');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files && dt.files.length > 0) {
            setSelectedFile(dt.files[0]);
        }
    });

    // Kliknięcie w dropzone (jeśli nie kliknięto przycisku zmiany)
    dropzone.addEventListener('click', (e) => {
        if (e.target !== btnChangeFile && !btnChangeFile.contains(e.target)) {
            fileInput.click();
        }
    });

    // Klawiatura (Dostępność: Enter / Spacja otwiera wybór pliku)
    dropzone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            setSelectedFile(e.target.files[0]);
        }
    });

    btnChangeFile.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    // Przeliczanie statystyk tekstu
    function updateTextStats(text) {
        const chars = text.length;
        const words = text.trim().length > 0 ? text.trim().split(/\s+/).length : 0;
        statsWordCount.textContent = `Słów: ${words}`;
        statsCharCount.textContent = `Znaków: ${chars}`;
    }

    // Przetwarzanie OCR przez backend
    btnProcess.addEventListener('click', async () => {
        if (!currentFile) return;

        hideError();
        setLoadingState(true);

        const psmSelect = document.getElementById('psmSelect');
        const enhanceCheckbox = document.getElementById('enhanceCheckbox');

        const formData = new FormData();
        formData.append('image', currentFile);
        if (psmSelect) {
            formData.append('psm', psmSelect.value);
        }
        if (enhanceCheckbox) {
            formData.append('enhance', enhanceCheckbox.checked ? 'true' : 'false');
        }

        try {
            const response = await fetch('/api/ocr', {
                method: 'POST',
                body: formData
            });

            if (response.status === 401) {
                showError('Sesja wygasła lub brak autoryzacji. Przekierowanie do logowania...');
                setTimeout(() => {
                    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                }, 1200);
                return;
            }

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Wystąpił błąd podczas rozpoznawania tekstu.');
            }

            const extractedText = data.text || '';
            resultText.value = extractedText;
            updateTextStats(extractedText);

            if (extractedText.length === 0) {
                resultText.value = '[Silnik OCR nie wykrył żadnego czytelnego tekstu na obrazie.]';
            }

            btnCopy.disabled = !extractedText;
            btnClear.disabled = false;
        } catch (err) {
            showError(err.message);
        } finally {
            setLoadingState(false);
        }
    });

    function setLoadingState(isLoading) {
        btnProcess.disabled = isLoading;
        btnSpinner.style.display = isLoading ? 'inline-block' : 'none';
        loadingOverlay.style.display = isLoading ? 'flex' : 'none';
        if (isLoading) {
            btnProcess.querySelector('.btn-text').textContent = 'Przetwarzanie OCR...';
        } else {
            btnProcess.querySelector('.btn-text').textContent = 'Rozpoznaj tekst (OCR)';
        }
    }

    // Kopiowanie tekstu do schowka
    btnCopy.addEventListener('click', async () => {
        const textToCopy = resultText.value;
        if (!textToCopy) return;

        try {
            await navigator.clipboard.writeText(textToCopy);
            btnCopy.classList.add('copied');
            copyBtnText.textContent = 'Skopiowano!';

            setTimeout(() => {
                btnCopy.classList.remove('copied');
                copyBtnText.textContent = 'Kopiuj do schowka';
            }, 2500);
        } catch (err) {
            console.error('Błąd kopiowania:', err);
            // Fallback
            resultText.select();
            document.execCommand('copy');
            copyBtnText.textContent = 'Skopiowano!';
            setTimeout(() => {
                copyBtnText.textContent = 'Kopiuj do schowka';
            }, 2500);
        }
    });

    // Czyszczenie wyników
    btnClear.addEventListener('click', () => {
        resultText.value = '';
        updateTextStats('');
        btnCopy.disabled = true;
        btnClear.disabled = true;
    });

    resultText.addEventListener('input', () => {
        updateTextStats(resultText.value);
        btnCopy.disabled = !resultText.value.trim();
        btnClear.disabled = !resultText.value;
    });
});
