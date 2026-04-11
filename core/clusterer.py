import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer

CAT_COLORS = {
    "Encyclopedia": "#4C72B0",
    "Social Media":  "#ff6314",
    "News":          "#3fb950",
    "Web Search":    "#bc8cff",
}
CAT_MAP = {
    "Wikipedia":  "Encyclopedia",
    "Social Media": "Social Media",
    "News":       "News",
    "Web Search": "Web Search",
}


class TextClusterer:
    def __init__(self, n_clusters: int = 6):
        self.n = n_clusters

    def build_df(self, items: list[dict]) -> pd.DataFrame:
        rows = []
        for it in items:
            cat = it.get("category", "Web Search")
            rows.append({
                "title":    (it.get("title") or "")[:120],
                "body":     (it.get("body")  or "")[:400],
                "text":     f"{it.get('title','')} {it.get('body','')}".strip(),
                "url":      it.get("url", ""),
                "source":   it.get("source", ""),
                "category": cat,
                "color":    CAT_COLORS.get(cat, "#8b949e"),
                "published": it.get("published", ""),
            })
        return pd.DataFrame(rows)

    def add_clusters(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < self.n:
            df = df.copy()
            df["topic_id"]    = 0
            df["topic_label"] = "General"
            df["px"] = np.random.rand(len(df))
            df["py"] = np.random.rand(len(df))
            return df

        texts = df["text"].fillna("").tolist()
        tfidf = TfidfVectorizer(max_features=400, stop_words="english", ngram_range=(1, 2), min_df=1)
        mat   = tfidf.fit_transform(texts)

        n_comp = min(40, mat.shape[1], mat.shape[0] - 1)
        reduced = Normalizer().fit_transform(TruncatedSVD(n_comp, random_state=42).fit_transform(mat))

        # 2D for scatter
        coords2 = TruncatedSVD(2, random_state=42).fit_transform(mat)

        k  = min(self.n, len(df))
        km = KMeans(k, random_state=42, n_init=10)
        km.fit(reduced)
        labels = km.labels_

        terms = tfidf.get_feature_names_out()
        names = {}
        for cid in range(k):
            mask = labels == cid
            if not mask.any():
                names[cid] = f"Topic {cid+1}"
                continue
            centroid = np.asarray(mat[mask].mean(axis=0)).flatten()
            top = centroid.argsort()[-3:][::-1]
            names[cid] = " / ".join(terms[i].title() for i in top)

        df = df.copy()
        df["topic_id"]    = labels
        df["topic_label"] = [names[l] for l in labels]
        df["px"] = coords2[:, 0]
        df["py"] = coords2[:, 1]
        return df

    def type_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.groupby("category").agg(count=("title", "count"))
            .reset_index().sort_values("count", ascending=False)
        )

    def topic_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.groupby("topic_label")
            .agg(count=("title", "count"), sources=("category", lambda x: ", ".join(x.unique())))
            .reset_index().sort_values("count", ascending=False)
        )
