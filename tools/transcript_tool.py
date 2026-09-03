import os
import re
from pathlib import Path
import config


def save_transcript(ticker, text, source="user upload"):
    os.makedirs(config.TRANSCRIPT_DIR, exist_ok=True)

    clean = re.sub(r"\s+", " ", text or "").strip()

    path = Path(
        config.TRANSCRIPT_DIR,
        f"{ticker.upper()}_latest.txt"
    )

    path.write_text(clean, encoding="utf-8")

    return {
        "ticker": ticker.upper(),
        "source": source,
        "characters": len(clean),
        "path": str(path)
    }


def get_transcript(ticker):
    path = Path(
        config.TRANSCRIPT_DIR,
        f"{ticker.upper()}_latest.txt"
    )

    return path.read_text(encoding="utf-8") if path.exists() else None
