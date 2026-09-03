import re, math

def _sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+',text or '') if len(s.strip())>60]

def extract_language_signals(sections):
    text=' '.join(sections.get(k,'') for k in ('mda','risk_factors','accounting_policies','notes'))
    sentences=_sentences(text)
    keywords={
      'uncertainty':['uncertain','uncertainty','volatility','challenging','adverse','headwind','may adversely','material weakness'],
      'investment':['research and development','R&D','capital expenditure','investment','technology','capacity expansion','acquisition'],
      'liquidity':['liquidity','cash flow','credit facility','covenant','debt','refinancing'],
      'accounting':['accounting policy','adopted','adoption','impairment','fair value','estimate','allowance','revenue recognition','lease'],
      'restructuring':['restructuring','impairment','write-down','write-off','severance','reorganization'],
    }
    hits={k:[] for k in keywords}
    for s in sentences:
        low=s.lower()
        for k,words in keywords.items():
            if any(w.lower() in low for w in words): hits[k].append(s[:700])
    return {k:v[:8] for k,v in hits.items() if v}

def compare_text(current, previous):
    a=set(re.findall(r'\b[a-z]{5,}\b',current.lower())); b=set(re.findall(r'\b[a-z]{5,}\b',previous.lower()))
    if not a or not b:return {'lexical_shift':None}
    j=1-len(a&b)/len(a|b)
    return {'lexical_shift':round(j,3),'new_terms':sorted(list(a-b))[:50],'dropped_terms':sorted(list(b-a))[:50]}
