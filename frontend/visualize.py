import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
import nltk
from nltk.corpus import stopwords

# pastikan stopwords Indonesia tersedia
nltk.download("stopwords")
stop_words = set(stopwords.words("indonesian"))

def plot_bar_chart(df: pd.DataFrame):
    counts = df["label"].value_counts()
    st.markdown("### 📊 Diagram Batang")
    st.bar_chart(counts)

def plot_pie_chart(df: pd.DataFrame):
    counts = df["label"].value_counts()
    if counts.empty: 
        return
    labels, sizes = counts.index.tolist(), counts.values.tolist()
    colors = sns.color_palette("Set2", n_colors=len(labels))
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
    ax.axis("equal")
    st.markdown("### 🥧 Diagram Pie")
    st.pyplot(fig)

def plot_wordcloud(df: pd.DataFrame):
    text = " ".join(df["cleaned_text"].astype(str))
    wc = WordCloud(width=600, height=400, background_color="white",
                   stopwords=stop_words, colormap="Set2").generate(text)
    fig, ax = plt.subplots()
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.markdown("### ☁️ Word Cloud")
    st.pyplot(fig)

def plot_ngram(df: pd.DataFrame, n: int = 1, top_k: int = 10):
    vectorizer = CountVectorizer(ngram_range=(n, n), stop_words=list(stop_words))
    X = vectorizer.fit_transform(df["cleaned_text"].astype(str))
    counts = X.sum(axis=0).A1 # type: ignore
    vocab = vectorizer.get_feature_names_out()
    freq_df = pd.DataFrame({"ngram": vocab, "count": counts}).sort_values("count", ascending=False).head(top_k)
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(data=freq_df, x="count", y="ngram", palette="Set2", ax=ax)
    st.markdown(f"### 📑 Diagram {n}-Gram (Top {top_k})")
    st.pyplot(fig)
