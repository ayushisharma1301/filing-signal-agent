# Equity Research Divergence Sentinel

## Purpose
An agentic equity-research triage system. It watches a small public-company
watchlist, detects new SEC 10-K/10-Q filings, chooses which filing information
to inspect, scores management tone with local FinBERT, compares the tone with
the company's own history and recent price movement, and decides whether the
filing deserves analyst attention.

## Zero-cost stack
SEC EDGAR + yfinance + local FinBERT + local statistical divergence + Gemini
2.5 Flash Free Tier + Streamlit.

## Local Windows
```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
python agent.py
streamlit run app.py
```

Set `GEMINI_API_KEY` and a real `SEC_USER_AGENT` in `.env`.

## Cloud
Push the project to GitHub, create a Streamlit Community Cloud app with
`app.py`, and add the Gemini key and SEC User-Agent under Streamlit Secrets.
Do not upload `.env`.

## Demo
`python seed_demo_data.py JPM` adds synthetic history for demonstrations only.

## Limitations
SEC section extraction is heuristic; FinBERT is pretrained; short histories
make the z-score less robust; price movement is contextual rather than causal;
the signal is research triage, not investment advice.
