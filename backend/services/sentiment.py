import re
import html
from typing import List, Dict
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|(?:\b[\w-]+\.)+[a-zA-Z]{2,})(?=\s|$)",
    flags=re.IGNORECASE,
)

MENTION_PATTERN = re.compile(r"@\w+")
HASHTAG_PATTERN = re.compile(r"#(\w+)")
MULTI_WS = re.compile(r"\s+")
REPEAT_CHARS = re.compile(r"(.)\1{2,}")


class SentimentAnalyzer:
    def __init__(
        self, model_name="cardiffnlp/twitter-xlm-roberta-base-sentiment", device=None
    ):
        self.labels = ["Negative", "Neutral", "Positive"]
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # set use_fast=False only if you need it; fast tokenizers are usually faster
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

    def clean_text(
        self,
        text: str,
        *,
        keep_hashtag_text: bool = True,
        replace_mentions_with_tag: bool = True,
        lower: bool = False,
        remove_emojis: bool = False,
    ) -> str:
        if not isinstance(text, str):
            return ""

        # unescape HTML entities
        text = html.unescape(text)

        # remove URLs (full urls, www, and simple domain patterns)
        text = URL_PATTERN.sub("", text)

        # normalize mentions
        if replace_mentions_with_tag:
            text = MENTION_PATTERN.sub("@user", text)
        else:
            text = MENTION_PATTERN.sub("", text)

        # hashtags: either remove '#' but keep the word (topic), or remove entirely
        if keep_hashtag_text:
            text = HASHTAG_PATTERN.sub(r"\1", text)  # turn #AI -> AI
        else:
            text = HASHTAG_PATTERN.sub("", text)

        # optionally remove emojis (very lossy); better to map them to text if useful
        if remove_emojis:
            # crude emoji removal: remove non-word, non-space typical emojis (works often)
            text = re.sub(r"[^\x00-\x7F]+", " ", text)

        # reduce repeated characters (heyyyy -> heyy)
        text = REPEAT_CHARS.sub(r"\1\1", text)

        # remove extra whitespace and strip
        text = MULTI_WS.sub(" ", text).strip()

        if lower:
            text = text.lower()

        return text

    def _predict_chunk(self, texts: list[str]) -> list[dict]:
        cleaned = [self.clean_text(t) for t in texts]
        inputs = self.tokenizer(
            cleaned, return_tensors="pt", padding=True, truncation=True, max_length=512
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1).cpu().numpy()

        results = []
        for orig_text, clean_text, p in zip(texts, cleaned, probs):
            pred_idx = int(np.argmax(p))
            results.append(
                {
                    "text": orig_text,
                    "cleaned_text": clean_text,
                    "label": self.labels[pred_idx],
                    "Negative": float(p[0]),
                    "Neutral": float(p[1]),
                    "Positive": float(p[2]),
                }
            )
        return results

    def predict_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict]:
        results = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            results.extend(self._predict_chunk(chunk))
        return results
