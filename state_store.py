import json, os
from datetime import datetime, timezone
from config import STATE_FILE

def _default():
    return {"last_accession_number": None, "sentiment_history": [], "filing_history": [], "last_flag": None, "last_run": None}
def _ensure():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f: json.dump({}, f)
def load_state():
    _ensure()
    with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f)
def save_state(state):
    _ensure()
    with open(STATE_FILE, "w", encoding="utf-8") as f: json.dump(state, f, indent=2)
def get_ticker_state(ticker): return load_state().get(ticker.upper(), _default())
def update_ticker_state(ticker, **updates):
    ticker=ticker.upper(); state=load_state(); cur=state.get(ticker,_default()); cur.update(updates); state[ticker]=cur; save_state(state)
def append_sentiment(ticker, score):
    ticker=ticker.upper(); state=load_state(); cur=state.get(ticker,_default()); h=cur.get("sentiment_history",[]); h.append(float(score)); cur["sentiment_history"]=h[-8:]; state[ticker]=cur; save_state(state)
def append_filing_record(ticker, record):
    ticker=ticker.upper(); state=load_state(); cur=state.get(ticker,_default()); h=cur.get("filing_history",[]); h.append(record); cur["filing_history"]=h[-8:]; cur["last_run"]=datetime.now(timezone.utc).isoformat(); state[ticker]=cur; save_state(state)
