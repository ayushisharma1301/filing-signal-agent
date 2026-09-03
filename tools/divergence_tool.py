import math
def compute_divergence(current_sentiment,sentiment_history,price_pct_change,z_threshold=1.5):
    h=[float(x) for x in sentiment_history if x is not None]
    if len(h)<2:return {"flag":False,"reason":"not_enough_history","message":"Need at least 2 prior sentiment readings."}
    mean=sum(h)/len(h); std=math.sqrt(sum((x-mean)**2 for x in h)/len(h))
    z=999.0 if std==0 and current_sentiment!=mean else (0.0 if std==0 else (current_sentiment-mean)/std)
    opposite=(current_sentiment>0 and price_pct_change<0) or (current_sentiment<0 and price_pct_change>0)
    sharp=abs(z)>=z_threshold; flag=bool(sharp and opposite)
    return {"flag":flag,"sentiment_z":z,"historical_mean":mean,"historical_std":std,"price_pct_change":price_pct_change,"opposite_direction":opposite,"sharp_shift":sharp,"message":"Sentiment/price divergence detected." if flag else "No divergence crossed the configured threshold."}
