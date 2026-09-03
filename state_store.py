import json, os
from datetime import datetime, timezone
import config

def _default():
    return {'last_accession_number':None,'filing_history':[],'analyses':[],'last_analysis':None}

def _ensure():
    os.makedirs(os.path.dirname(config.STATE_FILE),exist_ok=True)
    if not os.path.exists(config.STATE_FILE):
        with open(config.STATE_FILE,'w',encoding='utf-8') as f: json.dump({},f)

def load_state():
    _ensure()
    with open(config.STATE_FILE,'r',encoding='utf-8') as f: return json.load(f)

def save_state(state):
    _ensure()
    with open(config.STATE_FILE,'w',encoding='utf-8') as f: json.dump(state,f,indent=2)

def get_ticker_state(ticker): return load_state().get(ticker.upper(),_default())

def update_ticker_state(ticker,**updates):
    ticker=ticker.upper(); state=load_state(); cur=state.get(ticker,_default()); cur.update(updates); state[ticker]=cur; save_state(state)

def append_filing_record(ticker,record):
    ticker=ticker.upper(); state=load_state(); cur=state.get(ticker,_default()); cur.setdefault('filing_history',[]).append(record); cur['filing_history']=cur['filing_history'][-12:]; state[ticker]=cur; save_state(state)

def save_analysis(ticker,analysis):
    ticker=ticker.upper(); state=load_state(); cur=state.get(ticker,_default()); cur['last_analysis']=analysis; cur.setdefault('analyses',[]).append(analysis); cur['analyses']=cur['analyses'][-12:]; cur['last_run']=datetime.now(timezone.utc).isoformat(); state[ticker]=cur; save_state(state)
