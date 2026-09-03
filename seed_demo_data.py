import sys
from state_store import append_sentiment,update_ticker_state
DEMO_HISTORY=[0.05,0.06,0.04]
def seed(ticker="JPM"):
    ticker=ticker.upper(); update_ticker_state(ticker,last_accession_number=None,last_flag=None)
    for score in DEMO_HISTORY: append_sentiment(ticker,score)
    print(f"Seeded {ticker} with synthetic demo history: {DEMO_HISTORY}")
if __name__=="__main__": seed(sys.argv[1] if len(sys.argv)>1 else "JPM")
