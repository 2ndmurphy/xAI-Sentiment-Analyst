import re

# ====== PREPROCESS FUNCTION (NEW - Lebih advanced untuk bilingual Indo-Eng) ======
# Technical: Stemming Indo via Sastrawi (jika tersedia) atau heuristic affix stripper.
# Stopwords bilingual; keep hashtags untuk retain konteks topik. Best practice: Evaluasi dengan sample data untuk tuning (e.g., precision stemming ~80%).
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    _factory = StemmerFactory()
    _id_stemmer = _factory.create_stemmer()
    _HAS_SASTRAWI = True
except Exception:
    _HAS_SASTRAWI = False

try:
    import nltk
    from nltk.corpus import stopwords
    try:
        _ = stopwords.words("english")
    except LookupError:
        nltk.download("stopwords")
    EN_STOPWORDS = set(stopwords.words("english"))
except Exception:
    EN_STOPWORDS = set([
        "the","and","is","in","it","of","to","a","for","on","that","this","with","as","are",
        "was","be","by","an","or","from","at","not","have","has","but","they","you","i"
    ])

ID_STOPWORDS = set([
    "yang","dan","di","ke","dari","pada","untuk","dengan","atau","ini","itu","adalah",
    "sebagai","oleh","karena","agar","sampai","juga","sudah","belum","masih","apa","siapa",
    "dimana","kapan","kenapa","berapa","sebuah","beberapa","tetapi","jadi","agar","pun",
    "nya","nya","lah","kah","itu","ini","kami","kita","saya","dia","mereka","kalian","kamu"
])

STOPWORDS = set(w.lower() for w in (EN_STOPWORDS | ID_STOPWORDS))

URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#\w+")
NON_ALPHANUM_RE = re.compile(r"[^0-9a-zA-Z\u00C0-\u024F\s]")  # keep basic latin + accents
MULTISPACE_RE = re.compile(r"\s+")

INDO_PREFIXES = ["ber", "bel", "be", "me", "mem", "men", "meng", "meny", "pe", "pem", "pen", "peng", "di", "ke", "se", "per", "ter"]
INDO_SUFFIXES = ["kan", "an", "i"]

def _strip_indo_affixes(word):
    w = word
    for suf in sorted(INDO_SUFFIXES, key=len, reverse=True):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    for pref in sorted(INDO_PREFIXES, key=len, reverse=True):
        if w.startswith(pref) and len(w) - len(pref) >= 3:
            w = w[len(pref):]
            break
    return w or word

def preprocess_text(text,
        remove_stopwords=True,
        stem_indonesian=True,
        keep_hashtags=True):  # Set True untuk retain hashtags seperti #AI
    if not isinstance(text, str):
        text = str(text)

    s = text.lower()

    s = URL_RE.sub(" ", s)
    s = MENTION_RE.sub(" ", s)
    if not keep_hashtags:
        s = HASHTAG_RE.sub(" ", s)
    else:
        s = re.sub(r"#(\w+)", r"\1", s)

    s = NON_ALPHANUM_RE.sub(" ", s)

    s = MULTISPACE_RE.sub(" ", s).strip()

    if not s:
        return "", []

    tokens = s.split()

    processed = []
    for t in tokens:
        if t.isnumeric():
            continue

        if remove_stopwords and t in STOPWORDS:
            continue

        if stem_indonesian:
            if _HAS_SASTRAWI:
                try:
                    t_stem = _id_stemmer.stem(t)
                except Exception:
                    t_stem = _strip_indo_affixes(t)
            else:
                t_stem = _strip_indo_affixes(t)
        else:
            t_stem = t

        if remove_stopwords and t_stem in STOPWORDS:
            continue

        if len(t_stem) <= 1:
            continue

        processed.append(t_stem)

    cleaned = " ".join(processed)
    return cleaned  # Return string cleaned untuk scraping