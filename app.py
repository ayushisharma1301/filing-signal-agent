import streamlit as st
import config
from state_store import load_state

st.set_page_config(page_title="Equity Research Divergence Sentinel",page_icon="📈",layout="wide")
st.title("📈 Equity Research Divergence Sentinel")
st.markdown("An agent that screens new SEC filings for meaningful changes in management language and prioritizes filings where tone, historical sentiment, and price action diverge.")

with st.expander("Agentic workflow"):
    st.markdown("1. Discover a new 10-K/10-Q.\n2. Decide which filing sections to inspect.\n3. Measure tone with local FinBERT and price with yfinance.\n4. Compute the historical divergence signal.\n5. Decide whether the evidence deserves analyst attention.\n6. Write a grounded note only when warranted.")

if st.button("Screen watchlist now",type="primary",width="stretch"):
    from agent import run_watchlist
    with st.spinner("Screening filings — first FinBERT run may take several minutes..."):
        st.session_state["results"]=run_watchlist()
    st.success("Screening completed.")

state=load_state()
tracked=sum(len(state.get(t,{}).get("sentiment_history",[])) for t in config.WATCHLIST)
flags=sum(1 for t in config.WATCHLIST if state.get(t,{}).get("last_flag"))
a,b,c=st.columns(3); a.metric("Companies covered",len(config.WATCHLIST)); b.metric("Sentiment observations",tracked); c.metric("Attention flags",flags)
st.divider(); st.subheader("Coverage")
for ticker in config.WATCHLIST:
    s=state.get(ticker,{}); h=s.get("sentiment_history",[]); f=s.get("last_flag")
    with st.container(border=True):
        x,y,z,q=st.columns([1,2,2,5]); x.markdown(f"**{ticker}**"); y.caption(f"{len(h)} score(s)" if h else "Not screened"); z.caption(f"Latest tone: {h[-1]:+.3f}" if h else "—")
        q.markdown(f"⚠ **Analyst attention** — {f.get('note','')}" if f else ("✓ No active stored flag" if h else "Waiting for first screen"))
if "results" in st.session_state:
    st.divider(); st.subheader("Latest agent output")
    for ticker,result in st.session_state["results"].items():
        with st.expander(ticker): st.write(result)
