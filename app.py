import json
import streamlit as st
import config
from state_store import load_state
from tools.transcript_tool import save_uploaded_document
from agent import run_watchlist, run_agent_for_ticker
from tools.edgar_tool import list_recent_filings

st.set_page_config(page_title='Equity Research Filing Intelligence', page_icon='📊', layout='wide')
st.title('📊 Equity Research Filing Intelligence Agent')
st.caption('Agentic filing triage: identify which filings deserve analyst time, why they matter, and what the analyst should do next.')


def load_latest():
    state = load_state()
    return [state.get(t, {}).get('last_analysis') for t in config.WATCHLIST if state.get(t, {}).get('last_analysis')]


def rank_key(a):
    return {'READ_NOW': 0, 'REVIEW': 1, 'MONITOR': 2, 'IGNORE_FOR_NOW': 3}.get(triage_label(a), 9)


def triage_label(a):
    label = a.get('triage_label')
    if label in {'READ_NOW', 'REVIEW', 'MONITOR', 'IGNORE_FOR_NOW'}:
        return label
    return {'ESCALATE':'READ_NOW','INVESTIGATE':'REVIEW','MONITOR':'MONITOR','NO_MATERIAL_CHANGE':'IGNORE_FOR_NOW'}.get(a.get('verdict'), 'REVIEW')


def show_run_results(results):
    if not results:
        return
    st.markdown('### Run status')
    for ticker, result in results.items():
        status = result.get('status', 'UNKNOWN')
        if status == 'READY':
            label = triage_label(result)
            st.success(f'**{ticker}** — {label.replace("_", " ")} — analysis completed.')
        elif status in {'SEC_ERROR', 'NO_FILING_DATA', 'NO_NEW_FILING'}:
            msg = result.get('message') or result.get('error') or 'No analysis result returned.'
            st.warning(f'**{ticker}** — {status}: {msg}')
        else:
            st.error(f'**{ticker}** — {status}: {result.get("error") or result.get("message") or "Unknown error"}')


with st.sidebar:
    st.header('Coverage')
    st.write(', '.join(config.WATCHLIST))
    st.info('Research triage only. The agent recommends research actions, not buy/sell/hold decisions.')
    st.subheader('Upload filing / earnings-call context')
    ticker = st.selectbox('Company', config.WATCHLIST)
    uploaded = st.file_uploader('Upload .txt or .pdf', type=['txt', 'pdf'])
    if uploaded is not None and st.button('Save uploaded document'):
        try:
            saved = save_uploaded_document(ticker, uploaded)
            st.success(f'Saved {uploaded.name} ({saved["characters"]:,} characters).')
        except Exception as e:
            st.error(f'Could not save document: {type(e).__name__}: {e}')

# ---------- TOP: ANALYST ACTION CENTER ----------
latest = load_latest()
st.markdown('## 🚨 Analyst Action Center')

if not latest:
    st.warning('No filing has been analyzed yet. Start with **Analyze selected company** below. After the first successful run, this section becomes the analyst priority queue.')
else:
    ordered = sorted(latest, key=rank_key)
    groups = {k: [a for a in ordered if triage_label(a) == k] for k in ['READ_NOW','REVIEW','MONITOR','IGNORE_FOR_NOW']}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('🔴 Read now', len(groups['READ_NOW']))
    c2.metric('🟠 Review', len(groups['REVIEW']))
    c3.metric('🟡 Monitor', len(groups['MONITOR']))
    c4.metric('⚪ Ignore for now', len(groups['IGNORE_FOR_NOW']))

    st.markdown('### What should the analyst do first?')
    for a in ordered:
        label = triage_label(a)
        meta = a.get('filing_meta', {})
        with st.container(border=True):
            left, mid, right = st.columns([1.2, 1.8, 7])
            left.markdown(f'### {a.get("ticker", "—")}')
            left.caption(f'{meta.get("form", "Filing")} • filed {meta.get("filing_date", "—")}')
            mid.markdown(f'**{label.replace("_", " ")}**')
            mid.caption(a.get('priority', ''))
            right.markdown(f'**Agent recommendation:** {a.get("analyst_recommendation", "Review the highlighted evidence.")}')
            right.write(a.get('executive_summary', ''))

    st.markdown('### Filing attention queue')
    for heading, key, instruction in [
        ('🔴 READ NOW — highest value of analyst time', 'READ_NOW', 'Open and read these filings first.'),
        ('🟠 REVIEW — moderately important', 'REVIEW', 'Review the highlighted sections after the read-now queue.'),
        ('🟡 MONITOR — keep on radar', 'MONITOR', 'Do not spend substantial time immediately; monitor the next filing or signal.'),
        ('⚪ IGNORE FOR NOW — lowest priority', 'IGNORE_FOR_NOW', 'Defer unless another signal appears.')
    ]:
        if groups[key]:
            st.markdown(f'**{heading}**')
            st.caption(instruction)
            for a in groups[key]:
                meta = a.get('filing_meta', {})
                st.write(f'• **{a.get("ticker")} — {meta.get("form", "filing")} — {meta.get("filing_date", "—")}**: {a.get("analyst_recommendation", "")}')

st.divider()

# ---------- RUN CONTROL ----------
st.markdown('## 🔎 Run analysis')
st.write('For the first test, analyze one company. This avoids spending the free Gemini quota on five companies before we know the SEC connection and API key are working.')

c1, c2 = st.columns(2)
with c1:
    if st.button(f'🔎 Analyze {ticker}', type='primary', width='stretch'):
        with st.spinner(f'Analyzing {ticker}: SEC filing → financials → prior filing → market context → Gemini triage...'):
            try:
                result = run_agent_for_ticker(ticker, force=True)
                st.session_state.last_run_results = {ticker: result}
            except Exception as e:
                st.session_state.last_run_results = {ticker: {'status': 'ERROR', 'ticker': ticker, 'error': f'{type(e).__name__}: {e}'}}
        st.rerun()
with c2:
    if st.button('🔎 Analyze entire watchlist', width='stretch'):
        with st.spinner('Analyzing the watchlist. This can take several minutes because each company requires SEC retrieval plus one Gemini call...'):
            try:
                st.session_state.last_run_results = run_watchlist(force=True)
            except Exception as e:
                st.session_state.last_run_results = {'WATCHLIST': {'status': 'ERROR', 'error': f'{type(e).__name__}: {e}'}}
        st.rerun()

if st.session_state.get('last_run_results'):
    show_run_results(st.session_state.last_run_results)

st.caption('If a company shows SEC_ERROR, the dashboard will now display the actual failure instead of silently returning to “Not analyzed”.')

# ---------- DETAILED RESULTS ----------
latest = load_latest()
if latest:
    st.divider()
    st.subheader('Detailed evidence behind the triage')
    for a in sorted(latest, key=rank_key):
        with st.expander(f'{a.get("ticker")} — {triage_label(a).replace("_"," ")} — {a.get("filing_meta",{}).get("form","Filing")} {a.get("filing_meta",{}).get("filing_date","")}'):
            if a.get('financial_statement_changes'):
                st.markdown('**Major financial-statement changes**')
                for item in a['financial_statement_changes'][:8]:
                    st.write(f'• **{item.get("metric", "") }**: {item.get("change", "")} — {item.get("reason", "")} ({item.get("materiality", "")})')
            if a.get('accounting_policy_changes'):
                st.markdown('**Accounting / policy changes**')
                for item in a['accounting_policy_changes'][:6]:
                    st.write(f'• **{item.get("topic", "") }**: {item.get("change", "")} → {item.get("business_implication", "")}')
            if a.get('strategic_financial_decisions'):
                st.markdown('**Financial decisions / capital allocation**')
                for item in a['strategic_financial_decisions'][:6]:
                    st.write(f'• **{item.get("topic", "") }**: {item.get("change", "")} → {item.get("implication", "")}')
            if a.get('risk_changes'):
                st.markdown('**Risk changes**')
                for item in a['risk_changes'][:6]:
                    st.write(f'• **{item.get("risk", "") }**: {item.get("change", "")} — {item.get("why_it_matters", "")}')
            tone = a.get('management_tone', {})
            st.write(f'**Management tone:** {tone.get("direction", "—")} — {tone.get("what_changed", "—")}')
            if a.get('cross_source_divergences'):
                st.markdown('**Cross-source divergences**')
                for item in a['cross_source_divergences'][:8]:
                    st.write('• ' + item)
            st.markdown('**Research calls to action**')
            for i, item in enumerate(a.get('research_actions', [])[:10], 1):
                st.write(f'{i}. {item}')
            with st.expander('Evidence used'):
                for e in a.get('evidence', []):
                    st.write('• ' + e)
            st.download_button('Download JSON', json.dumps(a, indent=2), file_name=f'{a.get("ticker", "company")}_analysis.json', mime='application/json', key=f'dl_{a.get("ticker")}')

# ---------- FILING ROOM ----------
st.divider()
st.subheader('📚 Filing Room')
st.caption('The archive is optional. It is loaded only when requested so a temporary SEC error cannot interfere with the main analysis.')
room_ticker = st.selectbox('Company filing archive', config.WATCHLIST, key='room_ticker')
if st.button('Load recent filings'):
    with st.spinner('Loading SEC filing archive...'):
        st.session_state.filing_room = list_recent_filings(room_ticker, limit=12)
room = st.session_state.get('filing_room')
if room:
    if room.get('error'):
        st.warning(room['error'])
    elif room.get('filings'):
        for f in room['filings']:
            label = f"{f['form']} | filed {f['filing_date']} | report date {f.get('report_date') or '—'}"
            with st.expander(label):
                st.write(f"Accession: {f['accession_number']}")
                st.link_button('Open SEC filing', f['url'])
    else:
        st.caption('No recent SEC filings returned.')

st.divider()
st.caption('SEC filings are the primary evidence source. Uploaded PDFs/TXT files are optional research context. The agent produces research triage and actions, not personalized investment advice.')
