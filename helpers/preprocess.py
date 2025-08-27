import re
from emoji import demojize as unemojify

# ====== UTILITY FUNCTIONS ======
def preprocess_tweet(text: str) -> str:
    text = text.lower()
    text = re.sub(r"@\w+", "USER", text)
    text = re.sub(r"https?:\/\/[^\s]+", "HTTPURL", text)
    text = re.sub(r"[(\<\>\)\{\}:\!\?\-\_\=]", "", text)
    text = re.sub(r"[^\w\s.,!?]", "", text)
    text = re.sub(r"\b\d+\b", "NUM", text)
    text = re.sub(r"\s+", " ", text)
    text = unemojify(text.strip())
    return text