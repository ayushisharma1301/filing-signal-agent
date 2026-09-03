import os, re
from pathlib import Path
import config


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def save_transcript(ticker, text, source='user upload'):
    os.makedirs(config.TRANSCRIPT_DIR, exist_ok=True)
    clean = _clean(text)
    path = Path(config.TRANSCRIPT_DIR, f'{ticker.upper()}_latest.txt')
    path.write_text(clean, encoding='utf-8')
    return {'ticker': ticker.upper(), 'source': source, 'characters': len(clean), 'path': str(path)}


def extract_pdf_text(file_bytes):
    """Extract text from a PDF upload using pypdf."""
    from io import BytesIO
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or '')
        except Exception:
            pages.append('')
    return _clean('\n'.join(pages))


def save_uploaded_document(ticker, uploaded_file):
    """Accept .txt or .pdf uploads and store normalized text for the agent."""
    name = getattr(uploaded_file, 'name', 'upload.txt')
    raw = uploaded_file.getvalue()
    suffix = Path(name).suffix.lower()
    if suffix == '.pdf':
        text = extract_pdf_text(raw)
        source = f'user PDF upload: {name}'
    elif suffix == '.txt':
        text = raw.decode('utf-8', errors='ignore')
        source = f'user TXT upload: {name}'
    else:
        raise ValueError('Only .txt and .pdf files are supported.')
    if not text.strip():
        raise ValueError('No extractable text was found in this document.')
    return save_transcript(ticker, text, source=source)


def get_transcript(ticker):
    p = Path(config.TRANSCRIPT_DIR, f'{ticker.upper()}_latest.txt')
    return p.read_text(encoding='utf-8') if p.exists() else None
