import os
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "Filing Signal Agent your.email@example.com")
WATCHLIST = [x.strip().upper() for x in os.environ.get("WATCHLIST", "JPM,GS,MS,BAC,WFC").split(",") if x.strip()]
DIVERGENCE_Z_THRESHOLD = float(os.environ.get("DIVERGENCE_Z_THRESHOLD", "1.5"))
MAX_AGENT_TURNS = int(os.environ.get("MAX_AGENT_TURNS", "8"))
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
BASE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE_DIR, "data", "state.json")
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
