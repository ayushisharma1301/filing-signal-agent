import re, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
MODEL_NAME="ProsusAI/finbert"; _tokenizer=None; _model=None
def _load():
    global _tokenizer,_model
    if _tokenizer is None:
        _tokenizer=AutoTokenizer.from_pretrained(MODEL_NAME)
        _model=AutoModelForSequenceClassification.from_pretrained(MODEL_NAME); _model.eval()
    return _tokenizer,_model
def _chunks(text,n=180):
    words=re.findall(r"\S+",text)
    for i in range(0,len(words),n):
        x=" ".join(words[i:i+n])
        if len(x)>100: yield x
def score_text(text,max_chunks=120):
    tok,model=_load(); chunks=list(_chunks(text))[:max_chunks]
    if not chunks:return {"error":"Filing text is too short to score."}
    totals={"positive":0.0,"negative":0.0,"neutral":0.0}
    with torch.no_grad():
        for chunk in chunks:
            inp=tok(chunk,return_tensors="pt",truncation=True,max_length=512)
            probs=torch.softmax(model(**inp).logits,dim=-1)[0].tolist()
            for i,p in enumerate(probs):
                label=model.config.id2label[i].lower()
                if label in totals: totals[label]+=float(p)
    for k in totals: totals[k]/=len(chunks)
    return {**totals,"compound":totals["positive"]-totals["negative"],"chunks_scored":len(chunks)}
