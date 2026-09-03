import json, os, time
from google import genai
from google.genai import types
import config

SYSTEM = '''You are an institutional equity-research filing intelligence agent. Your job is to decide how much analyst attention a filing deserves.

Analyze the whole supplied evidence pack, with the SEC filing as the primary source. Identify material changes in financial statements, their disclosed reasons, accounting policies/estimates, capital allocation and financial decisions, risks, management language, price context, and earnings-call context where supplied.

The most important output is TRIAGE. Decide whether the analyst should:
- READ_NOW: the filing contains a material change, accounting issue, strategic financial decision, risk shift, unexplained financial movement, or meaningful cross-source divergence that deserves immediate analyst attention.
- REVIEW: there is a meaningful development worth reviewing, but it is not urgent.
- MONITOR: there is a potentially relevant change, but the filing does not yet justify significant analyst time.
- IGNORE_FOR_NOW: no material change is evident from the supplied evidence; the analyst can defer reading this filing unless another signal appears.

Use the verdict mapping:
ESCALATE -> READ_NOW
INVESTIGATE -> REVIEW
MONITOR -> MONITOR
NO_MATERIAL_CHANGE -> IGNORE_FOR_NOW

Every important claim must be grounded in supplied evidence. Never invent numbers, causes, quotations or accounting-policy changes. Distinguish reported facts from inference. If the filing does not disclose a reason, explicitly say so.

The final recommendation must be a practical research action for an analyst (what to read, reconcile, compare, question, or monitor), not a buy/sell/hold recommendation.
Return STRICT JSON matching the requested schema.'''

SCHEMA = types.Schema(type='OBJECT', properties={
    'verdict': types.Schema(type='STRING'),
    'priority': types.Schema(type='STRING'),
    'triage_label': types.Schema(type='STRING'),
    'analyst_recommendation': types.Schema(type='STRING'),
    'executive_summary': types.Schema(type='STRING'),
    'financial_statement_changes': types.Schema(type='ARRAY', items=types.Schema(type='OBJECT', properties={
        'metric': types.Schema(type='STRING'), 'change': types.Schema(type='STRING'), 'reason': types.Schema(type='STRING'), 'materiality': types.Schema(type='STRING')}, required=['metric','change','reason','materiality'])),
    'accounting_policy_changes': types.Schema(type='ARRAY', items=types.Schema(type='OBJECT', properties={
        'topic': types.Schema(type='STRING'), 'change': types.Schema(type='STRING'), 'business_implication': types.Schema(type='STRING'), 'evidence': types.Schema(type='STRING')}, required=['topic','change','business_implication','evidence'])),
    'strategic_financial_decisions': types.Schema(type='ARRAY', items=types.Schema(type='OBJECT', properties={
        'topic': types.Schema(type='STRING'), 'change': types.Schema(type='STRING'), 'implication': types.Schema(type='STRING'), 'evidence': types.Schema(type='STRING')}, required=['topic','change','implication','evidence'])),
    'risk_changes': types.Schema(type='ARRAY', items=types.Schema(type='OBJECT', properties={
        'risk': types.Schema(type='STRING'), 'change': types.Schema(type='STRING'), 'why_it_matters': types.Schema(type='STRING')}, required=['risk','change','why_it_matters'])),
    'management_tone': types.Schema(type='OBJECT', properties={
        'direction': types.Schema(type='STRING'), 'what_changed': types.Schema(type='STRING'), 'confidence': types.Schema(type='STRING')}, required=['direction','what_changed','confidence']),
    'cross_source_divergences': types.Schema(type='ARRAY', items=types.Schema(type='STRING')),
    'research_actions': types.Schema(type='ARRAY', items=types.Schema(type='STRING')),
    'evidence': types.Schema(type='ARRAY', items=types.Schema(type='STRING'))
}, required=['verdict','priority','triage_label','analyst_recommendation','executive_summary','financial_statement_changes','accounting_policy_changes','strategic_financial_decisions','risk_changes','management_tone','cross_source_divergences','research_actions','evidence'])


def analyze(evidence_pack):
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is missing')
    client = genai.Client(api_key=key)
    prompt = ('Analyze this filing evidence pack and produce the final analyst triage. '
              'The analyst should see the most important recommendation first.\n\nEVIDENCE PACK:\n' +
              json.dumps(evidence_pack, ensure_ascii=False)[:500000])
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    response_mime_type='application/json',
                    response_schema=SCHEMA
                )
            )
            return json.loads(resp.text)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
