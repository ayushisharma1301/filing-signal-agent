from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
import config
from llm_client import run as run_llm
from state_store import append_sentiment,get_ticker_state,update_ticker_state
from tools.edgar_tool import check_new_filing,get_cached_filing_text,get_filing_sections
from tools.price_tool import get_price_snapshot
from tools.sentiment_tool import score_text
from tools.divergence_tool import compute_divergence

def execute_tool(name,args):
    ticker=str(args.get("ticker","")).upper()
    if name=="check_new_filing":
        state=get_ticker_state(ticker)
        result=check_new_filing(ticker,args.get("last_known_accession",state.get("last_accession_number")))
        if result.get("has_new_filing"): update_ticker_state(ticker,last_accession_number=result["accession_number"])
        return result
    if name=="get_filing_sections": return get_filing_sections(ticker)
    if name=="score_filing_sentiment":
        text=get_cached_filing_text(ticker)
        if not text:return {"error":"No cached filing. Call check_new_filing first."}
        result=score_text(text)
        if "compound" in result: append_sentiment(ticker,result["compound"])
        return result
    if name=="get_price_snapshot": return get_price_snapshot(ticker)
    if name=="compute_divergence":
        state=get_ticker_state(ticker); history=state.get("sentiment_history",[])[:-1]
        return compute_divergence(float(args["sentiment_compound"]),history,float(args["price_pct_change"]),config.DIVERGENCE_Z_THRESHOLD)
    return {"error":f"Unknown tool: {name}"}

def run_agent_for_ticker(ticker):
    result=run_llm([{"role":"user","content":f"Screen {ticker} for a new filing and decide whether it deserves analyst attention."}],execute_tool)
    lower=result.lower()
    update_ticker_state(ticker,last_run=datetime.now(timezone.utc).isoformat())
    if "flag" in lower or "divergence" in lower: update_ticker_state(ticker,last_flag={"note":result})
    return result

def run_watchlist():
    out={}
    for ticker in config.WATCHLIST:
        print(f"Checking {ticker}...")
        try: out[ticker]=run_agent_for_ticker(ticker)
        except Exception as e: out[ticker]=f"Error: {type(e).__name__}: {e}"
        print(f"  -> {str(out[ticker])[:180]}")
    return out

if __name__=="__main__": run_watchlist()
