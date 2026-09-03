import json, os, time
from google import genai
from google.genai import types
import config

SYSTEM='''You are an institutional equity-research filing intelligence agent. Your job is to analyze company filings and supporting earnings-call material as a research TRIAGE system, not to provide personalized investment advice. Analyze the whole available evidence pack, but prioritize material changes.

You must identify: (1) major financial-statement changes and plausible reasons explicitly supported by the filing, (2) accounting-policy changes, new standards, estimates or judgments with business implications, (3) unusual capital-allocation/financial decisions such as R&D, capex, acquisitions, debt, buybacks, liquidity, restructuring or impairments, (4) material risk-factor changes, (5) management-language changes, and (6) contradictions or confirmations across filing, financials, price and transcript.

Every important claim must be grounded in supplied evidence. Never invent numbers, causes, quotations or accounting-policy changes. Distinguish reported facts from inference. If the filing does not explain a reason, say that the reason is not clearly disclosed.

Return STRICT JSON matching the requested schema. The final verdict must be one of: 'ESCALATE', 'INVESTIGATE', 'MONITOR', 'NO_MATERIAL_CHANGE'. Recommendations are research actions (what to read/check/ask), not buy/sell/hold advice.
'''

SCHEMA=types.Schema(type='OBJECT',properties={
 'verdict':types.Schema(type='STRING'),
 'priority':types.Schema(type='STRING'),
 'executive_summary':types.Schema(type='STRING'),
 'financial_statement_changes':types.Schema(type='ARRAY',items=types.Schema(type='OBJECT',properties={'metric':types.Schema(type='STRING'),'change':types.Schema(type='STRING'),'reason':types.Schema(type='STRING'),'materiality':types.Schema(type='STRING')},required=['metric','change','reason','materiality'])),
 'accounting_policy_changes':types.Schema(type='ARRAY',items=types.Schema(type='OBJECT',properties={'topic':types.Schema(type='STRING'),'change':types.Schema(type='STRING'),'business_implication':types.Schema(type='STRING'),'evidence':types.Schema(type='STRING')},required=['topic','change','business_implication','evidence'])),
 'strategic_financial_decisions':types.Schema(type='ARRAY',items=types.Schema(type='OBJECT',properties={'topic':types.Schema(type='STRING'),'change':types.Schema(type='STRING'),'implication':types.Schema(type='STRING'),'evidence':types.Schema(type='STRING')},required=['topic','change','implication','evidence'])),
 'risk_changes':types.Schema(type='ARRAY',items=types.Schema(type='OBJECT',properties={'risk':types.Schema(type='STRING'),'change':types.Schema(type='STRING'),'why_it_matters':types.Schema(type='STRING')},required=['risk','change','why_it_matters'])),
 'management_tone':types.Schema(type='OBJECT',properties={'direction':types.Schema(type='STRING'),'what_changed':types.Schema(type='STRING'),'confidence':types.Schema(type='STRING')},required=['direction','what_changed','confidence']),
 'cross_source_divergences':types.Schema(type='ARRAY',items=types.Schema(type='STRING')),
 'research_actions':types.Schema(type='ARRAY',items=types.Schema(type='STRING')),
 'evidence':types.Schema(type='ARRAY',items=types.Schema(type='STRING'))
},required=['verdict','priority','executive_summary','financial_statement_changes','accounting_policy_changes','strategic_financial_decisions','risk_changes','management_tone','cross_source_divergences','research_actions','evidence'])

def analyze(evidence_pack):
    key=os.getenv('GEMINI_API_KEY')
    if not key: raise RuntimeError('GEMINI_API_KEY is missing')
    client=genai.Client(api_key=key)
    prompt='''Analyze this evidence pack for the company. Treat the filing as the primary source. Review all supplied sections and financial metrics. Produce a final research verdict and actionable research follow-ups.\n\nEVIDENCE PACK:\n'''+json.dumps(evidence_pack,ensure_ascii=False)[:500000]
    for attempt in range(4):
        try:
            resp=client.models.generate_content(model=config.GEMINI_MODEL,contents=prompt,config=types.GenerateContentConfig(system_instruction=SYSTEM,response_mime_type='application/json',response_schema=SCHEMA,temperature=0.1))
            return json.loads(resp.text)
        except Exception:
            if attempt==3: raise
            time.sleep(2**attempt)
