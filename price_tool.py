import yfinance as yf
def get_price_snapshot(ticker):
    ticker=ticker.upper(); hist=yf.Ticker(ticker).history(period="3mo",auto_adjust=False)
    if hist.empty or len(hist)<2: return {"ticker":ticker,"error":"No usable price history returned."}
    close=hist["Close"].dropna(); current=float(close.iloc[-1]); old=float(close.iloc[0])
    return {"ticker":ticker,"current_price":current,"price_pct_change_90d":((current/old)-1)*100,"as_of":str(close.index[-1])}
