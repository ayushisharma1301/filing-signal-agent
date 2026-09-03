from datetime import datetime, timezone
import config
from state_store import get_ticker_state, update_ticker_state, append_filing_record, save_analysis
from tools.edgar_tool import check_new_filing, get_filing_sections, get_filing_meta, get_previous_filing, list_recent_filings
from tools.financials_tool import get_financial_snapshot, compare_financials
from tools.price_tool import get_price_snapshot
from tools.language_tool import extract_language_signals, compare_text
from tools.transcript_tool import get_transcript
from llm_client import analyze


def build_evidence(ticker, force=False):
    state = get_ticker_state(ticker)
    filing = check_new_filing(ticker, None if force else state.get('last_accession_number'))

    if filing.get('error') and not filing.get('has_new_filing'):
        return {'ticker': ticker, 'status': 'SEC_ERROR', 'message': filing.get('error')}

    if not filing.get('has_new_filing') and not force:
        # There is no new filing since the last successful run. The app can still
        # display the previous verdict, but should not spend another Gemini call.
        return {'ticker': ticker, 'status': 'NO_NEW_FILING', 'message': filing.get('message', 'No new filing'), 'latest': filing.get('latest')}

    if filing.get('has_new_filing'):
        update_ticker_state(ticker, last_accession_number=filing['accession_number'])
        append_filing_record(ticker, filing)

    meta = get_filing_meta(ticker)
    sections = get_filing_sections(ticker)
    if not meta or 'error' in sections:
        return {'ticker': ticker, 'status': 'NO_FILING_DATA', 'message': 'Filing metadata/text is not available yet.'}

    prior = get_previous_filing(ticker, meta.get('accession_number', '')) if meta.get('accession_number') else {}
    financials = get_financial_snapshot(ticker)
    changes = compare_financials(financials)
    price = get_price_snapshot(ticker)
    transcript = get_transcript(ticker)

    pack = {
        'ticker': ticker,
        'filing_meta': meta,
        'sections': sections,
        'financial_snapshot': financials,
        'financial_changes': changes,
        'price': price,
        'language_signals': extract_language_signals(sections),
        'prior_filing': {
            'meta': {k: prior.get(k) for k in ('form', 'filing_date', 'report_date', 'accession_number', 'filing_url')},
            'sections': prior.get('sections', {})
        },
        'language_delta': {
            k: compare_text(sections.get(k, ''), prior.get('sections', {}).get(k, ''))
            for k in ('mda', 'risk_factors', 'accounting_policies', 'notes')
            if sections.get(k) and prior.get('sections', {}).get(k)
        }
    }
    if transcript:
        pack['earnings_call_transcript'] = transcript[:80000]

    # Filing Room metadata is context only; it is not separately sent to Gemini.
    pack['recent_filings'] = list_recent_filings(ticker, limit=12)
    return {'status': 'READY', 'evidence': pack}


def run_agent_for_ticker(ticker, force=False):
    built = build_evidence(ticker, force=force)
    if built.get('status') != 'READY':
        return built
    result = analyze(built['evidence'])
    result['ticker'] = ticker
    result['filing_meta'] = built['evidence']['filing_meta']
    result['generated_at'] = datetime.now(timezone.utc).isoformat()
    save_analysis(ticker, result)
    return result


def run_watchlist(force=True):
    """Analyze the latest 10-K/10-Q for each watchlist company.

    The dashboard then ranks those filing-level verdicts into READ NOW,
    REVIEW, MONITOR and IGNORE FOR NOW so an analyst sees the triage first.
    """
    out = {}
    for ticker in config.WATCHLIST:
        try:
            out[ticker] = run_agent_for_ticker(ticker, force=force)
        except Exception as e:
            out[ticker] = {'status': 'ERROR', 'ticker': ticker, 'error': f'{type(e).__name__}: {e}'}
    return out
