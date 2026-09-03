# Enhanced Architecture

```text
SEC EDGAR
  │
  ├── 10-K / 10-Q metadata + full filing
  ├── XBRL Company Facts
  └── filing sections
        │
        ├── Financial statements
        ├── MD&A
        ├── Risk Factors
        ├── Accounting policies / estimates
        └── Notes

Optional earnings-call transcript
        │
        ▼
Evidence pack
        │
        ├── largest financial-statement changes
        ├── disclosed reasons
        ├── accounting-policy changes
        ├── capital-allocation decisions
        ├── risk-factor changes
        ├── management-language signals
        └── price context
        │
        ▼
Gemini agent (structured JSON)
        │
        ├── ESCALATE
        ├── INVESTIGATE
        ├── MONITOR
        └── NO_MATERIAL_CHANGE
        │
        ▼
Research calls to action + evidence
```

## Design principle

The agent is not a summarizer. It is a **research triage and decision-support layer**. Python retrieves and calculates evidence; Gemini interprets the evidence, reconciles sources, assigns a verdict, and produces research actions.

## Accounting policy coverage

The pipeline explicitly searches for significant/critical accounting policies, recent accounting pronouncements, adoption language, impairment, fair value, revenue recognition, lease accounting and estimate/judgment language. The LLM must distinguish an actual policy change from a mere disclosure.

## Financial-statement coverage

SEC XBRL Company Facts are used to surface large changes in common metrics such as revenue, net income, operating income, operating cash flow, capex, R&D, assets, debt, cash and gross profit. The filing remains the source for explaining *why* the number changed.

## Transcript coverage

Earnings-call transcripts are supported as optional uploaded `.txt` evidence. The project deliberately does not scrape a proprietary transcript provider. A production version can add a licensed/public transcript connector later.

## Important limitation

This is a portfolio-grade research assistant, not a trading system. A financial-statement change is not automatically good or bad. Recommendations are research actions such as reviewing a note, reconciling a metric, or asking management a question—not personalized buy/sell/hold advice.
