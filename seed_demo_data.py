import json, os
from datetime import datetime, timezone
import config
os.makedirs(os.path.dirname(config.STATE_FILE),exist_ok=True)
state={t:{'last_accession_number':None,'filing_history':[],'analyses':[],'last_analysis':None} for t in config.WATCHLIST}
with open(config.STATE_FILE,'w') as f: json.dump(state,f,indent=2)
print('Initialized clean state for:',', '.join(config.WATCHLIST))
