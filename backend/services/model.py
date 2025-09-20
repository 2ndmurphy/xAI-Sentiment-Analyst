import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class SentimentAnalyzer:
    def __init__(self, model_name="cardiffnlp/twitter-xlm-roberta-base-sentiment"):
        self.labels = ["Negative", "Neutral", "Positive"]
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

    def clean_text(self, text: str) -> str:
        """Cleaning sederhana untuk tweet"""
        text = re.sub(r"http\S+", "", text)   # remove urls
        text = re.sub(r"@\w+", "@user", text) # replace mentions
        text = re.sub(r"#\w+", "", text)      # remove hashtags
        text = re.sub(r"\s+", " ", text)      # remove extra spaces
        return text.strip()

    def predict(self, text: str) -> dict:
        """Prediksi sentimen untuk satu teks"""
        cleaned = self.clean_text(text)
        inputs = self.tokenizer(cleaned, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1).cpu().numpy()[0]

        pred_idx = probs.argmax()
        return {
            "text": text,
            "cleaned_text": cleaned,
            "label": self.labels[pred_idx],
            "probabilities": {self.labels[i]: float(probs[i]) for i in range(len(self.labels))}
        }

    def predict_batch(self, texts: list) -> pd.DataFrame:
        """Prediksi banyak teks (list of str), return DataFrame"""
        results = [self.predict(t) for t in texts]
        return pd.DataFrame(results)

    def predict_from_csv(self, csv_path: str, text_column="text", output_path=None) -> pd.DataFrame:
        """Prediksi dari CSV, optionally simpan hasil"""
        df = pd.read_csv(csv_path)
        texts = df[text_column].astype(str).tolist()
        results = self.predict_batch(texts)
        final_df = pd.concat([df.reset_index(drop=True), results[["label", "cleaned_text"]]], axis=1)

        if output_path:
            final_df.to_csv(output_path, index=False)
        return final_df
