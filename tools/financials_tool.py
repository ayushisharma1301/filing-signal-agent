import requests, time, json, re
import config
from tools.edgar_tool import _ciks

HEADERS={'User-Agent':config.SEC_USER_AGENT,'Accept-Encoding':'gzip, deflate'}

def _get(url):
    for attempt in range(3):
        r=requests.get(url,headers=HEADERS,timeout=60)
        if r.status_code==429:
            time.sleep(2*(attempt+1)); continue
        r.raise_for_status(); return r
    r.raise_for_status()

def _facts_for_ticker(ticker):
    cik=_ciks().get(ticker.upper())
    if not cik:return None
    return _get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json').json()

def _period_value(unit_rows):
    rows=[r for r in unit_rows if r.get('form') in ('10-Q','10-K') and r.get('val') is not None]
    return sorted(rows,key=lambda x:(x.get('end',''),x.get('filed','')),reverse=True)

def get_financial_snapshot(ticker):
    data=_facts_for_ticker(ticker)
    if not data:return {'error':'No SEC company facts found'}
    us=data.get('facts',{}).get('us-gaap',{})
    wanted={
      'Revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'],
      'NetIncome':['NetIncomeLoss'],
      'OperatingIncome':['OperatingIncomeLoss'],
      'OperatingCashFlow':['NetCashProvidedByUsedInOperatingActivities'],
      'CapitalExpenditure':['PaymentsToAcquirePropertyPlantAndEquipment'],
      'ResearchAndDevelopment':['ResearchAndDevelopmentExpense'],
      'TotalAssets':['Assets'],
      'TotalDebt':['LongTermDebtNoncurrent','LongTermDebtCurrent'],
      'Cash':['CashAndCashEquivalentsAtCarryingValue'],
      'GrossProfit':['GrossProfit'],
    }
    out={}
    for label,tags in wanted.items():
        rows=[]
        for tag in tags:
            node=us.get(tag)
            if not node:continue
            units=node.get('units',{})
            for unit,vals in units.items():
                for r in _period_value(vals): rows.append({**r,'unit':unit,'tag':tag})
            if rows:break
        # de-duplicate by end/form/fy/fp
        seen=set(); clean=[]
        for r in rows:
            key=(r.get('end'),r.get('form'),r.get('fy'),r.get('fp'))
            if key not in seen: seen.add(key); clean.append(r)
        out[label]=clean[:6]
    return {'ticker':ticker.upper(),'company':data.get('entityName'),'facts':out}

def _latest(rows):
    return rows[0] if rows else None

def _comparable_previous(rows, cur):
    # Prefer the same form and fiscal period, then the same duration.
    candidates=[r for r in rows if r is not cur]
    same_fp=[r for r in candidates if r.get('form')==cur.get('form') and r.get('fp')==cur.get('fp')]
    if same_fp:return sorted(same_fp,key=lambda x:x.get('end',''),reverse=True)[0]
    same_form=[r for r in candidates if r.get('form')==cur.get('form')]
    return sorted(same_form,key=lambda x:x.get('end',''),reverse=True)[0] if same_form else None

def compare_financials(snapshot):
    if 'facts' not in snapshot:return {'error':'No facts'}
    changes=[]
    for metric,rows in snapshot['facts'].items():
        cur=_latest(rows); prev=_comparable_previous(rows,cur) if cur else None
        if not cur or not prev:continue
        try:
            cv=float(cur['val']); pv=float(prev['val'])
            if pv==0: continue
            pct=(cv/pv-1)*100
            changes.append({'metric':metric,'current':cv,'previous':pv,'pct_change':pct,'current_period':cur.get('end'),'previous_period':prev.get('end'),'unit':cur.get('unit'),'form':cur.get('form'),'fp':cur.get('fp'),'comparison_basis':'same filing form/fiscal period when available'})
        except Exception:continue
    changes.sort(key=lambda x:abs(x['pct_change']),reverse=True)
    return {'largest_changes':changes[:config.MAX_FACTS]}
