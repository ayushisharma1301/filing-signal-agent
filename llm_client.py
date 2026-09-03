import os
from google import genai
from google.genai import types
import config

SYSTEM_PROMPT = """
You are the Equity Research Divergence Sentinel.

Your job is to screen new SEC filings and decide whether they deserve an equity
research analyst's attention. You do NOT calculate financial numbers yourself.
Python tools provide filing data, FinBERT sentiment, price movement and the
statistical divergence result.

Agent workflow:
1. Check for a new 10-K/10-Q.
2. If none exists, stop.
3. If new, inspect MD&A and Risk Factors using the filing-section tool.
4. Score the filing with local FinBERT.
5. Get the recent price move.
6. Compare sentiment with the company's own historical sentiment.
7. Decide whether the filing contains a meaningful divergence worth flagging.
8. If flagged, write a concise 3-5 sentence analyst note.

Look for meaningful changes in management tone, newly emphasized risks,
weakening/strengthening language, unusual shifts versus the company's own
history, and sentiment/price moving in opposite directions.

Never invent figures, events, causes or quotations. If evidence is insufficient,
say so. This is a research-triage signal, not an investment recommendation.
"""

def _declarations():
    return [
        types.FunctionDeclaration(name="check_new_filing",description="Check SEC EDGAR for a new 10-K or 10-Q since the last processed filing.",parameters=types.Schema(type="OBJECT",properties={"ticker":types.Schema(type="STRING"),"last_known_accession":types.Schema(type="STRING")},required=["ticker"])),
        types.FunctionDeclaration(name="get_filing_sections",description="Read bounded excerpts from the latest cached filing, especially MD&A and Risk Factors.",parameters=types.Schema(type="OBJECT",properties={"ticker":types.Schema(type="STRING")},required=["ticker"])),
        types.FunctionDeclaration(name="score_filing_sentiment",description="Run local FinBERT sentiment scoring on the latest cached filing.",parameters=types.Schema(type="OBJECT",properties={"ticker":types.Schema(type="STRING")},required=["ticker"])),
        types.FunctionDeclaration(name="get_price_snapshot",description="Get current price and approximately 90-day price change.",parameters=types.Schema(type="OBJECT",properties={"ticker":types.Schema(type="STRING")},required=["ticker"])),
        types.FunctionDeclaration(name="compute_divergence",description="Compare current sentiment against the ticker's own history and price movement.",parameters=types.Schema(type="OBJECT",properties={"ticker":types.Schema(type="STRING"),"sentiment_compound":types.Schema(type="NUMBER"),"price_pct_change":types.Schema(type="NUMBER")},required=["ticker","sentiment_compound","price_pct_change"]))
    ]

def run(messages,execute_tool):
    key=os.environ.get("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY is missing. Add it to .env or Streamlit Secrets.")
    client=genai.Client(api_key=key)
    tools=[types.Tool(function_declarations=_declarations())]
    contents=[types.Content(role="user",parts=[types.Part.from_text(text=messages[0]["content"])])]
    for _ in range(config.MAX_AGENT_TURNS):
        response=client.models.generate_content(model=config.GEMINI_MODEL,contents=contents,config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,tools=tools,temperature=0.1))
        candidate=response.candidates[0]; parts=candidate.content.parts if candidate.content else []
        calls=[p.function_call for p in parts if getattr(p,"function_call",None)]
        if not calls:
            return "\n".join(p.text for p in parts if getattr(p,"text",None)).strip() or "(agent returned no text)"
        contents.append(candidate.content); responses=[]
        for call in calls:
            result=execute_tool(call.name,dict(call.args or {}))
            responses.append(types.Part.from_function_response(name=call.name,response={"result":result}))
        contents.append(types.Content(role="user",parts=responses))
    return "Agent hit the maximum tool-call turn limit."
