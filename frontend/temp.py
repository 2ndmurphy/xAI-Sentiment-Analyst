import streamlit as st
import httpx
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import re

# =====================
# Sentiment Analyzer
# =====================
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


# =====================
# Streamlit App
# =====================
API_URL = "http://127.0.0.1:8000/scrape"

st.set_page_config(page_title="Tweet Scraper + Analyzer", layout="wide")
st.title("🐦 Tweet Scraper + Analyzer")

# Scraping Form
with st.form("scrape_form"):
    query = st.text_input("🔍 Masukkan keyword/topik")
    limit = st.slider("Jumlah tweet", 10, 200, 20)
    submitted = st.form_submit_button("Mulai Scrape")

if "df" not in st.session_state:
    st.session_state.df = None

if submitted:
    if not query.strip():
        st.warning("⚠️ Keyword/topik tidak boleh kosong.")
    else:
        with st.spinner("⚡ Scraping in progress..."):
            try:
                resp = httpx.post(API_URL, json={"query": query, "limit": limit}, timeout=120.0)
                if resp.status_code == 200:
                    data = resp.json()
                    tweets = data.get("tweets", [])
                    if tweets:
                        df = pd.DataFrame(tweets)
                        st.session_state.df = df
                        st.success(f"✅ Dapat {data['count']} tweets untuk '{data['query']}'")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("Tidak ada tweet yang berhasil diambil.")
                else:
                    st.error(f"Scraping gagal. Status code: {resp.status_code}")
            except Exception as e:
                st.error(f"Gagal konek ke backend: {e}")

# Analisis Sentimen
if st.session_state.df is not None:
    if st.button("Analisis Sentimen"):
        analyzer = SentimentAnalyzer()
        with st.spinner("🧠 Analisis sentimen..."):
            result_df = analyzer.predict_batch(st.session_state.df["text"].tolist())
            st.session_state.df = pd.concat(
                [st.session_state.df.reset_index(drop=True), result_df[["label", "cleaned_text"]]], axis=1
            )

        st.success("✅ Analisis sentimen selesai!")
        st.dataframe(st.session_state.df, use_container_width=True)

        # Statistik label
        st.subheader("📊 Distribusi Sentimen")
        label_counts = st.session_state.df["label"].value_counts()
        st.bar_chart(label_counts)
        