import streamlit as st
import json
import config
from state_store import load_state
from tools.transcript_tool import save_uploaded_document
from agent import run_watchlist
from tools.edgar_tool import list_recent_filings

st.set_page_config(page_title='Equity Research Filing Intelligence', page_icon='📊', layout='wide')
st.title('📊 Equity Research Filing Intelligence Agent')
st.caption('Whole-filing intelligence: financial statement changes • accounting policies • capital allocation • risks • management language • earnings-call context')

with st.sidebar:
    st.header('Coverage')
    st.write(', '.join(config.WATCHLIST))
    st.info('Research triage only. Outputs are evidence-grounded research actions, not personalized investment advice.')
    st.subheader('Upload research document')
    ticker = st.selectbox('Company', config.WATCHLIST)
    uploaded = st.file_uploader('Upload earnings call / report (.txt or .pdf)', type=['txt', 'pdf'])
    if uploaded is not None:
        if st.button('Save uploaded document'):
            try:
                saved = save_uploaded_document(ticker, uploaded)
                st.success(f"Saved {uploaded.name} ({saved['characters']:,} extracted characters).")
            except Exception as e:
                st.error(f'Could not read the upload: {type(e).__name__}: {e}')

c1, c2 = st.columns([3, 1])
with c1:
    st.markdown('### What the agent checks')
    st.markdown('''- **Financial statements:** largest quarter/year changes and disclosed reasons\n- **Accounting:** policy changes, new standards, estimates and judgments\n- **Capital allocation:** R&D, capex, acquisitions, debt, buybacks, liquidity, restructuring\n- **Language:** management tone, risk-factor changes and unusual wording\n- **Cross-source:** filing vs financials vs price vs uploaded document\n- **Verdict:** ESCALATE / INVESTIGATE / MONITOR / NO_MATERIAL_CHANGE''')
with c2:
    st.metric('Companies', len(config.WATCHLIST))

if st.button('🔎 Analyze watchlist', type='primary', width='stretch'):
    with st.spinner('Retrieving filings and analyzing evidence...'):
        st.session_state.results = run_watchlist()
    st.success('Analysis complete.')

state = load_state()
latest = []
for t in config.WATCHLIST:
    a = state.get(t, {}).get('last_analysis')
    if a: latest.append(a)

if latest:
    st.divider(); st.subheader('Latest research verdicts')
    for a in sorted(latest, key=lambda x: {'ESCALATE': 0, 'INVESTIGATE': 1, 'MONITOR': 2, 'NO_MATERIAL_CHANGE': 3}.get(x.get('verdict'), 9)):
        with st.container(border=True):
            x, y, z = st.columns([1.4, 1.3, 5])
            x.markdown(f"### {a.get('ticker')}")
            y.metric('Verdict', a.get('verdict', '—'))
            z.markdown(f"**{a.get('priority', '—')}** — {a.get('executive_summary', '')}")
            if a.get('financial_statement_changes'):
                st.markdown('**Major financial-statement changes**')
                for item in a['financial_statement_changes'][:6]: st.write(f"• **{item['metric']}**: {item['change']} — {item['reason']} ({item['materiality']})")
            if a.get('accounting_policy_changes'):
                st.markdown('**Accounting / policy changes**')
                for item in a['accounting_policy_changes'][:5]: st.write(f"• **{item['topic']}**: {item['change']} → {item['business_implication']}")
            if a.get('strategic_financial_decisions'):
                st.markdown('**Financial decisions / capital allocation**')
                for item in a['strategic_financial_decisions'][:5]: st.write(f"• **{item['topic']}**: {item['change']} → {item['implication']}")
            if a.get('risk_changes'):
                st.markdown('**Risk changes**')
                for item in a['risk_changes'][:5]: st.write(f"• **{item['risk']}**: {item['change']} — {item['why_it_matters']}")
            tone = a.get('management_tone', {})
            st.write(f"**Management tone:** {tone.get('direction', '—')} — {tone.get('what_changed', '—')}")
            if a.get('cross_source_divergences'):
                st.markdown('**Cross-source divergences**')
                for item in a['cross_source_divergences'][:6]: st.write('• ' + item)
            st.markdown('**Research calls to action**')
            for i, item in enumerate(a.get('research_actions', [])[:8]): st.write(f'{i+1}. {item}')
            with st.expander('Evidence used'):
                for e in a.get('evidence', []): st.write('• ' + e)
            st.download_button('Download JSON', json.dumps(a, indent=2), file_name=f"{a.get('ticker', 'company')}_analysis.json", mime='application/json')

st.divider()
st.subheader('📚 Filing room')
room_ticker = st.selectbox('Company filing archive', config.WATCHLIST, key='room_ticker')
try:
    recent = list_recent_filings(room_ticker, limit=12)
except Exception as e:
    recent = {'filings': [], 'error': f'{type(e).__name__}: {e}'}

if recent.get('filings'):
    for f in recent['filings']:
        label = f"{f['form']} | filed {f['filing_date']} | report date {f.get('report_date') or '—'}"
        with st.expander(label):
            st.write(f"Accession: {f['accession_number']}")
            st.link_button('Open SEC filing', f['url'])
elif recent.get('error'):
    st.warning('SEC filing archive is temporarily unavailable. Check your SEC_USER_AGENT secret (use a real name + email) and try again later. The app itself is still available.')
else:
    st.caption('No recent SEC filings returned.')

st.divider()
st.caption('SEC filings are the primary evidence source. Uploaded TXT/PDF documents are optional context. The app does not scrape proprietary transcript providers.')
st.divider(); st.subheader('Coverage status')
for t in config.WATCHLIST:
    s = state.get(t, {})
    a = s.get('last_analysis')
    st.write(f"**{t}** — {a.get('verdict', 'Not analyzed') if a else 'Not analyzed'} — {a.get('filing_meta', {}).get('filing_date', '') if a else ''}")
