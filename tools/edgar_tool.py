import os, re
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import config

HEADERS={"User-Agent":config.SEC_USER_AGENT,"Accept-Encoding":"gzip, deflate"}
_cik_map=None

def _ciks():
    global _cik_map
    if _cik_map is None:
        r=requests.get("https://www.sec.gov/files/company_tickers.json",headers=HEADERS,timeout=30); r.raise_for_status()
        _cik_map={v["ticker"].upper():str(v["cik_str"]).zfill(10) for v in r.json().values()}
    return _cik_map

def _clean_html(html):
    soup=BeautifulSoup(html,"html.parser")
    for tag in soup(["script","style","noscript"]): tag.decompose()
    return re.sub(r"\s+"," ",soup.get_text(" ",strip=True))

def _extract_sections(text):
    lower=text.lower(); out={}
    markers={
        "risk_factors":["risk factors","item 1a. risk factors","item 1a risk factors"],
        "mda":["management’s discussion and analysis","management's discussion and analysis","item 7. management’s discussion","item 7. management's discussion"]
    }
    for key, starts in markers.items():
        pos=-1
        for marker in starts:
            i=lower.find(marker)
            if i>=0 and (pos<0 or i<pos): pos=i
        if pos>=0: out[key]=text[pos:pos+30000]
    return out or {"document_excerpt":text[:30000]}

def check_new_filing(ticker,last_known_accession=None):
    ticker=ticker.upper(); cik=_ciks().get(ticker)
    if not cik: return {"has_new_filing":False,"error":f"Ticker {ticker} not found in SEC map."}
    r=requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",headers=HEADERS,timeout=30); r.raise_for_status()
    recent=r.json()["filings"]["recent"]; candidates=[]
    for i,form in enumerate(recent["form"]):
        if form in ("10-K","10-Q"):
            candidates.append({"form":form,"filing_date":recent["filingDate"][i],"accession_number":recent["accessionNumber"][i],"primary_document":recent["primaryDocument"][i]})
    if not candidates: return {"has_new_filing":False,"message":f"No recent 10-K/10-Q for {ticker}."}
    latest=candidates[0]
    if last_known_accession and latest["accession_number"]==last_known_accession:
        return {"has_new_filing":False,"message":f"No new 10-K/10-Q for {ticker}."}
    acc=latest["accession_number"].replace("-","")
    url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{latest['primary_document']}"
    r=requests.get(url,headers=HEADERS,timeout=60); r.raise_for_status()
    text=_clean_html(r.text)
    os.makedirs(config.CACHE_DIR,exist_ok=True)
    Path(config.CACHE_DIR,f"{ticker}.txt").write_text(text,encoding="utf-8")
    return {"has_new_filing":True,"ticker":ticker,"form":latest["form"],"filing_date":latest["filing_date"],"accession_number":latest["accession_number"],"filing_url":url,"text_length":len(text),"sections_available":list(_extract_sections(text))}

def get_filing_sections(ticker):
    p=Path(config.CACHE_DIR,f"{ticker.upper()}.txt")
    if not p.exists(): return {"error":"No cached filing. Call check_new_filing first."}
    return _extract_sections(p.read_text(encoding="utf-8"))

def get_cached_filing_text(ticker):
    p=Path(config.CACHE_DIR,f"{ticker.upper()}.txt")
    return p.read_text(encoding="utf-8") if p.exists() else None
