# Equity Research Filing Intelligence Agent

An enhanced, cloud-friendly equity research agent that collates company filings and optional earnings-call transcripts, analyzes the whole available evidence pack, and produces a final research verdict with calls to action.

## What changed from the original MVP

- Whole-filing coverage rather than sentiment-only screening
- SEC XBRL financial-statement change detection
- Reasons for changes grounded in the filing
- Accounting-policy / accounting-estimate change detection
- Capital-allocation and financial-decision analysis
- Risk-factor and management-language analysis
- Optional earnings-call transcript ingestion
- Cross-source reconciliation: filing + financials + price + transcript
- Structured verdict: `ESCALATE`, `INVESTIGATE`, `MONITOR`, `NO_MATERIAL_CHANGE`
- Research calls to action and evidence list
- No FinBERT dependency: avoids a large local model download and reduces Streamlit Cloud friction
- Fewer LLM calls: one evidence pack → one structured final analysis per company

## Zero-cost stack

SEC EDGAR + SEC XBRL + yfinance + Streamlit Community Cloud + Gemini free-tier model.

Set `GEMINI_MODEL=gemini-3.5-flash-lite` by default. Check current Gemini availability/rate limits before deployment.

## Cloud deployment

1. Upload this repository to GitHub.
2. Create a Streamlit Community Cloud app pointing to `app.py`.
3. Add Streamlit Secrets:

```toml
GEMINI_API_KEY = "your_key"
SEC_USER_AGENT = "Your Name your.email@example.com"
GEMINI_MODEL = "gemini-3.5-flash-lite"
WATCHLIST = "JPM,GS,MS,BAC,WFC"
```

Never commit `.env` or API keys.

## Transcript workflow

Use the sidebar to upload an earnings-call transcript as `.txt` for a selected company. It is then included in the next evidence pack for that company.

## Run locally (optional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Research interpretation

The agent's verdict is an attention-priority decision. It does not constitute personalized investment advice. Always inspect the cited filing evidence before acting on a research hypothesis.
