import streamlit as st
import json
from pathlib import Path
import config
from state_store import load_state
from tools.transcript_tool import save_uploaded_document
from agent import run_watchlist
from tools.edgar_tool import list_recent_filings

st.set_page_config(page_title='Equity Research Filing Intelligence', page_icon='📊', layout='wide')
st.title('📊 Equity Research Filing Intelligence Agent')
st.caption('Agentic filing triage: identify which filings deserve analyst time, why they matter, and what the analyst should do next.')


def load_latest():
    state = load_state()
    return [state.get(t, {}).get('last_analysis') for t in config.WATCHLIST if state.get(t, {}).get('last_analysis')]


def rank_key(a):
    return {'READ_NOW': 0, 'REVIEW': 1, 'MONITOR': 2, 'IGNORE_FOR_NOW': 3}.get(a.get('triage_label'), 9)


def triage_label(a):
    label = a.get('triage_label')
    if label in {'READ_NOW', 'REVIEW', 'MONITOR', 'IGNORE_FOR_NOW'}:
        return label
    return {'ESCALATE':'READ_NOW','INVESTIGATE':'REVIEW','MONITOR':'MONITOR','NO_MATERIAL_CHANGE':'IGNORE_FOR_NOW'}.get(a.get('verdict'), 'REVIEW')


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
            st.success(f"Saved {uploaded.name} ({saved['characters']:,} characters).")
        except Exception as e:
            st.error(str(e))

# ---------- TOP: ANALYST ACTION CENTER ----------
latest = load_latest()
st.markdown('## 🚨 Analyst Action Center')

if not latest:
    st.warning('No filing has been analyzed yet. Click **Analyze latest filings** below to generate the agent\'s triage and final recommendation.')
else:
    ordered = sorted(latest, key=rank_key)
    read_now = [a for a in ordered if triage_label(a) == 'READ_NOW']
    review = [a for a in ordered if triage_label(a) == 'REVIEW']
    monitor = [a for a in ordered if triage_label(a) == 'MONITOR']
    ignore = [a for a in ordered if triage_label(a) == 'IGNORE_FOR_NOW']

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('🔴 Read now', len(read_now))
    c2.metric('🟠 Review', len(review))
    c3.metric('🟡 Monitor', len(monitor))
    c4.metric('⚪ Ignore for now', len(ignore))

    st.markdown('### What should the analyst do?')
    for a in ordered:
        label = triage_label(a)
        meta = a.get('filing_meta', {})
        form = meta.get('form', 'Filing')
        date = meta.get('filing_date', '—')
        with st.container(border=True):
            left, mid, right = st.columns([1.3, 2.0, 5.5])
            left.markdown(f'### {a.get("ticker", "—")}')
            left.caption(f'{form} • filed {date}')
            mid.markdown(f'**{label.replace("_", " ")}**')
            mid.write(a.get('priority', '—'))
            right.markdown(f'**Agent recommendation:** {a.get("analyst_recommendation", "Review the filing and validate the key signals.")}')
            right.write(a.get('executive_summary', ''))

    st.markdown('### Filing attention queue')
    for heading, group, instruction in [
        ('🔴 READ NOW — highest value of analyst time', read_now, 'Open and read these filings first.'),
        ('🟠 REVIEW — moderately important', review, 'Review the highlighted sections after the read-now queue.'),
        ('🟡 MONITOR — keep on radar', monitor, 'No need to spend substantial time immediately; monitor the next filing or new signal.'),
        ('⚪ IGNORE FOR NOW — lowest priority', ignore, 'No material change detected from supplied evidence; defer unless another signal appears.')
    ]:
        if group:
            st.markdown(f'**{heading}**')
            st.caption(instruction)
            for a in group:
                meta = a.get('filing_meta', {})
                st.write(f"• **{a.get('ticker')} — {meta.get('form','filing')} — {meta.get('filing_date','—')}**: {a.get('analyst_recommendation','')}" )

st.divider()

# ---------- RUN CONTROL ----------
st.markdown('## 🔎 Run analysis')
st.write('The agent analyzes the latest 10-K/10-Q for every company in the watchlist, then places each filing into the analyst attention queue above.')
if st.button('🔎 Analyze latest filings', type='primary', width='stretch'):
    with st.spinner('Retrieving SEC filings, financial statement data, prior filings and market context, then generating research triage...'):
        st.session_state.results = run_watchlist(force=True)
    st.success('Analysis complete. Scroll to the top to see the analyst action center.')
    st.rerun()

# ---------- DETAILED RESULTS ----------
latest = load_latest()
if latest:
    st.divider()
    st.subheader('Detailed evidence behind the triage')
    for a in sorted(latest, key=rank_key):
        with st.expander(f"{a.get('ticker')} — {triage_label(a).replace('_',' ')} — {a.get('filing_meta',{}).get('form','Filing')} {a.get('filing_meta',{}).get('filing_date','')}"):
            if a.get('financial_statement_changes'):
                st.markdown('**Major financial-statement changes**')
                for item in a['financial_statement_changes'][:8]:
                    st.write(f"• **{item['metric']}**: {item['change']} — {item['reason']} ({item['materiality']})")
            if a.get('accounting_policy_changes'):
                st.markdown('**Accounting / policy changes**')
                for item in a['accounting_policy_changes'][:6]:
                    st.write(f"• **{item['topic']}**: {item['change']} → {item['business_implication']}")
            if a.get('strategic_financial_decisions'):
                st.markdown('**Financial decisions / capital allocation**')
                for item in a['strategic_financial_decisions'][:6]:
                    st.write(f"• **{item['topic']}**: {item['change']} → {item['implication']}")
            if a.get('risk_changes'):
                st.markdown('**Risk changes**')
                for item in a['risk_changes'][:6]:
                    st.write(f"• **{item['risk']}**: {item['change']} — {item['why_it_matters']}")
            tone = a.get('management_tone', {})
            st.write(f"**Management tone:** {tone.get('direction','—')} — {tone.get('what_changed','—')}")
            if a.get('cross_source_divergences'):
                st.markdown('**Cross-source divergences**')
                for item in a['cross_source_divergences'][:8]: st.write('• ' + item)
            st.markdown('**Research calls to action**')
            for i, item in enumerate(a.get('research_actions', [])[:10], 1): st.write(f'{i}. {item}')
            with st.expander('Evidence used'):
                for e in a.get('evidence', []): st.write('• ' + e)
            st.download_button('Download JSON', json.dumps(a, indent=2), file_name=f"{a.get('ticker','company')}_analysis.json", mime='application/json', key=f"dl_{a.get('ticker')}")

# ---------- FILING ROOM ----------
st.divider()
st.subheader('📚 Filing Room')
st.caption('Browse recent SEC filings. The attention queue above tells you which analyzed filing deserves your time first.')
room_ticker = st.selectbox('Company filing archive', config.WATCHLIST, key='room_ticker')
recent = list_recent_filings(room_ticker, limit=12)
if recent.get('error'):
    st.warning(recent['error'])
elif recent.get('filings'):
    for f in recent['filings']:
        label = f"{f['form']} | filed {f['filing_date']} | report date {f.get('report_date') or '—'}"
        with st.expander(label):
            st.write(f"Accession: {f['accession_number']}")
            st.link_button('Open SEC filing', f['url'])
else:
    st.caption('No recent SEC filings returned.')

st.divider()
st.caption('SEC filings are the primary evidence source. Uploaded PDFs/TXT files are optional research context. The agent produces research triage and actions, not personalized investment advice.')
