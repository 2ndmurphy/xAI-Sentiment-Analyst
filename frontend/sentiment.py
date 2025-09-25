import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class SentimentAnalyzer:
    def __init__(self, model_name="model/twitter-xlm-roberta"):
        self.labels = ["Negative", "Neutral", "Positive"]
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

    def clean_text(self, text: str) -> str:
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"@\w+", "@user", text)
        text = re.sub(r"#\w+", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def predict_batch(self, texts: list) -> pd.DataFrame:
        results = []
        for text in texts:
            cleaned = self.clean_text(text)
            inputs = self.tokenizer(cleaned, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
            pred_idx = probs.argmax()
            results.append({
                "text": text,
                "cleaned_text": cleaned,
                "label": self.labels[pred_idx],
                "Negative": float(probs[0]),
                "Neutral": float(probs[1]),
                "Positive": float(probs[2])
            })
        return pd.DataFrame(results)