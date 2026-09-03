import os

WATCHLIST = [x.strip().upper() for x in os.getenv('WATCHLIST','JPM,GS,MS,BAC,WFC').split(',') if x.strip()]
SEC_USER_AGENT = os.getenv('SEC_USER_AGENT','Filing Signal Agent research@example.com')
GEMINI_MODEL = os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY','')
MAX_FILING_CHARS = int(os.getenv('MAX_FILING_CHARS','120000'))
MAX_SECTION_CHARS = int(os.getenv('MAX_SECTION_CHARS','22000'))
MAX_FACTS = int(os.getenv('MAX_FACTS','30'))
PRICE_LOOKBACK_DAYS = int(os.getenv('PRICE_LOOKBACK_DAYS','90'))
BASE_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(BASE_DIR,'data','cache')
STATE_FILE = os.path.join(BASE_DIR,'data','state.json')
TRANSCRIPT_DIR = os.path.join(BASE_DIR,'data','transcripts')
