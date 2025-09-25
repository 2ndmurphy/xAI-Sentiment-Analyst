import streamlit as st
import httpx
import pandas as pd
from sentiment import SentimentAnalyzer
from visualize import plot_bar_chart, plot_pie_chart, plot_wordcloud, plot_ngram

API_URL = "http://127.0.0.1:8000/scrape"

st.set_page_config(page_title="Tweet Scraper + Analyzer", layout="wide")
st.title("🐦 Tweet Scraper + Analyzer")

# ================================
# Inisialisasi Session State
# ================================
if "df" not in st.session_state:
    st.session_state.df = None
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

# ================================
# Scraping Form
# ================================
with st.form("scrape_form"):
    query = st.text_input("🔍 Masukkan keyword/topik")
    limit = st.slider("Jumlah tweet", 10, 200, 20)
    submitted = st.form_submit_button("Mulai Scrape")

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
                        st.session_state.analyzed = False
                        st.success(f"✅ Dapat {data['count']} tweets untuk '{data['query']}'")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("Tidak ada tweet yang berhasil diambil.")
                else:
                    st.error(f"Scraping gagal. Status code: {resp.status_code}")
            except Exception as e:
                st.error(f"Gagal konek ke backend: {e}")

# ================================
# Analisis Sentimen + Visualisasi
# ================================
if st.session_state.df is not None:
    if st.button("🚀 Analisis Sentimen"):
        analyzer = SentimentAnalyzer()
        with st.spinner("🧠 Analisis sentimen..."):
            result_df = analyzer.predict_batch(st.session_state.df["text"].dropna().tolist())
            st.session_state.df = pd.concat(
                [st.session_state.df.reset_index(drop=True), result_df[["label", "cleaned_text"]]], axis=1
            )
        st.session_state.analyzed = True
        st.success("✅ Analisis sentimen selesai!")
        st.dataframe(st.session_state.df, use_container_width=True)

if st.session_state.analyzed and st.session_state.df is not None:
    st.subheader("👁️ Visualisasi Sentimen")

    col1, col2 = st.columns(2)
    with col1:
        plot_bar_chart(st.session_state.df)
    with col2:
        plot_pie_chart(st.session_state.df)

    col3, col4 = st.columns(2)
    with col3:
        plot_wordcloud(st.session_state.df)
    with col4:
        plot_ngram(st.session_state.df, n=2)  # contoh bigram