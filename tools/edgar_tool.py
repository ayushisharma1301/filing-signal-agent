import os, re, time, json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import config

HEADERS = {
    'User-Agent': config.SEC_USER_AGENT,
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'application/json, text/html, */*',
}
CIK_URL = 'https://www.sec.gov/files/company_tickers.json'
_cik_map = None
_session = requests.Session()
_session.headers.update(HEADERS)


def _get(url, timeout=45, retries=4):
    last = None
    for attempt in range(retries):
        try:
            r = _session.get(url, timeout=timeout)
            if r.status_code in (429, 403, 503):
                last = requests.HTTPError(f'SEC returned HTTP {r.status_code} for {url}')
                if attempt < retries - 1:
                    time.sleep(min(12, 2 ** attempt + 1))
                    continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            if attempt < retries - 1:
                time.sleep(min(12, 2 ** attempt + 1))
    raise last or RuntimeError('SEC request failed')


def _safe_get(url, timeout=45):
    try:
        return _get(url, timeout=timeout)
    except Exception as e:
        return None


def _ciks():
    global _cik_map
    if _cik_map is None:
        r = _get(CIK_URL)
        _cik_map = {v['ticker'].upper(): str(v['cik_str']).zfill(10) for v in r.json().values()}
    return _cik_map


def _clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    return re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))


def _find(text, patterns):
    low = text.lower()
    positions = [low.find(p.lower()) for p in patterns]
    positions = [p for p in positions if p >= 0]
    return min(positions) if positions else -1


def _extract_sections(text):
    sections = {}
    specs = {
        'business': (['item 1. business', 'item 1 business'], ['item 1a. risk factors', 'item 1a risk factors'], 18000),
        'risk_factors': (['item 1a. risk factors', 'item 1a risk factors', 'risk factors'], ['item 1b.', 'item 2. properties'], config.MAX_SECTION_CHARS),
        'mda': (['item 7. management’s discussion and analysis', "item 7. management's discussion and analysis", 'management’s discussion and analysis', "management's discussion and analysis"], ['item 7a.', 'item 8. financial statements'], config.MAX_SECTION_CHARS),
        'financial_statements': (['item 8. financial statements', 'consolidated statements', 'financial statements'], ['item 9.', 'item 9a.'], 26000),
        'accounting_policies': (['significant accounting policies', 'critical accounting policies', 'accounting policies', 'recent accounting pronouncements'], ['accounting standards updates', 'item 7.', 'management’s discussion and analysis'], 18000),
        'notes': (['notes to consolidated financial statements', 'notes to financial statements'], ['item 9.', 'item 9a.', 'item 9b.'], 30000),
    }
    for key, (starts, ends, limit) in specs.items():
        s = _find(text, starts)
        if s >= 0:
            end = _find(text, ends)
            if end <= s:
                end = min(len(text), s + limit)
            sections[key] = text[s:min(end, s + limit)]
    if not sections:
        sections['document_excerpt'] = text[:config.MAX_SECTION_CHARS]
    return sections


def list_recent_filings(ticker, limit=12):
    ticker = ticker.upper()
    try:
        cik = _ciks().get(ticker)
        if not cik:
            return {'ticker': ticker, 'filings': [], 'error': f'{ticker} not found in SEC ticker map'}
        recent = _get(f'https://data.sec.gov/submissions/CIK{cik}.json').json()['filings']['recent']
        rows = []
        for i, form in enumerate(recent['form']):
            if form in ('10-K', '10-Q', '8-K'):
                acc = recent['accessionNumber'][i]
                acc_clean = acc.replace('-', '')
                doc = recent['primaryDocument'][i]
                rows.append({
                    'form': form,
                    'filing_date': recent['filingDate'][i],
                    'report_date': recent['reportDate'][i],
                    'accession_number': acc,
                    'primary_document': doc,
                    'url': f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}'
                })
                if len(rows) >= limit:
                    break
        return {'ticker': ticker, 'filings': rows}
    except Exception as e:
        return {'ticker': ticker, 'filings': [], 'error': f'SEC filing list unavailable: {type(e).__name__}: {e}'}


def _fetch_filing_text(cik, row):
    acc = row['accession_number'].replace('-', '')
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{row['primary_document']}"
    return url, _clean_html(_get(url, timeout=90).text)


def get_previous_filing(ticker, current_accession):
    try:
        ticker = ticker.upper(); cik = _ciks().get(ticker)
        if not cik: return {'error': 'Ticker not found'}
        recent = _get(f'https://data.sec.gov/submissions/CIK{cik}.json').json()['filings']['recent']
        current_index = next((i for i, a in enumerate(recent['accessionNumber']) if a == current_accession), None)
        if current_index is None: return {'error': 'Current accession not found'}
        current_form = recent['form'][current_index]
        for i in range(current_index + 1, len(recent['form'])):
            if recent['form'][i] == current_form:
                row = {'form': recent['form'][i], 'filing_date': recent['filingDate'][i], 'report_date': recent['reportDate'][i], 'accession_number': recent['accessionNumber'][i], 'primary_document': recent['primaryDocument'][i]}
                url, text = _fetch_filing_text(cik, row)
                return {**row, 'filing_url': url, 'text': text[:config.MAX_FILING_CHARS], 'sections': _extract_sections(text)}
        return {'error': 'No prior filing of the same form found'}
    except Exception as e:
        return {'error': f'Previous SEC filing unavailable: {type(e).__name__}: {e}'}


def check_new_filing(ticker, last_known_accession=None):
    ticker = ticker.upper()
    try:
        cik = _ciks().get(ticker)
        if not cik: return {'has_new_filing': False, 'error': f'{ticker} not found in SEC ticker map'}
        recent = _get(f'https://data.sec.gov/submissions/CIK{cik}.json').json()['filings']['recent']
        candidates = []
        for i, form in enumerate(recent['form']):
            if form in ('10-K', '10-Q'):
                candidates.append({'form': form, 'filing_date': recent['filingDate'][i], 'accession_number': recent['accessionNumber'][i], 'primary_document': recent['primaryDocument'][i], 'report_date': recent['reportDate'][i]})
        if not candidates: return {'has_new_filing': False, 'message': 'No recent 10-K/10-Q found'}
        latest = candidates[0]
        if last_known_accession and latest['accession_number'] == last_known_accession:
            return {'has_new_filing': False, 'message': f"No new 10-K/10-Q since {last_known_accession}", 'latest': latest}
        acc = latest['accession_number'].replace('-', '')
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{latest['primary_document']}"
        text = _clean_html(_get(url, timeout=90).text)
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        Path(config.CACHE_DIR, f'{ticker}.txt').write_text(text[:config.MAX_FILING_CHARS], encoding='utf-8')
        Path(config.CACHE_DIR, f'{ticker}_meta.json').write_text(json.dumps({**latest, 'filing_url': url, 'cik': cik}), encoding='utf-8')
        return {'has_new_filing': True, 'ticker': ticker, **latest, 'filing_url': url, 'text_length': len(text), 'sections_available': list(_extract_sections(text))}
    except Exception as e:
        return {'has_new_filing': False, 'error': f'SEC filing retrieval failed: {type(e).__name__}: {e}'}


def get_filing_sections(ticker):
    p = Path(config.CACHE_DIR, f'{ticker.upper()}.txt')
    if not p.exists(): return {'error': 'No cached filing'}
    return _extract_sections(p.read_text(encoding='utf-8'))


def get_cached_filing_text(ticker):
    p = Path(config.CACHE_DIR, f'{ticker.upper()}.txt')
    return p.read_text(encoding='utf-8') if p.exists() else None


def get_filing_meta(ticker):
    p = Path(config.CACHE_DIR, f'{ticker.upper()}_meta.json')
    if not p.exists(): return {}
    return json.loads(p.read_text(encoding='utf-8'))
