import requests
import feedparser
import re
from urllib.parse import quote_plus

_UA = "MiniPalantir/1.0 (research)"
_HEADERS = {"User-Agent": _UA}


class IntelFetcher:

    def wikipedia(self, query: str) -> list[dict]:
        items = []
        try:
            sr = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": query,
                        "format": "json", "srlimit": 4},
                headers=_HEADERS, timeout=8,
            ).json()
            for r in sr.get("query", {}).get("search", []):
                try:
                    s = requests.get(
                        f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(r['title'])}",
                        headers=_HEADERS, timeout=8,
                    ).json()
                    items.append({
                        "title": s.get("title", r["title"]),
                        "body": s.get("extract", "")[:600],
                        "url": s.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "source": "Wikipedia",
                        "category": "Encyclopedia",
                        "published": "",
                    })
                except Exception:
                    pass
        except Exception:
            pass
        return items

    def reddit(self, query: str, limit: int = 20) -> list[dict]:
        items = []
        try:
            data = requests.get(
                "https://www.reddit.com/search.json",
                params={"q": query, "sort": "new", "limit": limit, "type": "link"},
                headers=_HEADERS, timeout=10,
            ).json()
            for p in data.get("data", {}).get("children", []):
                d = p.get("data", {})
                items.append({
                    "title": d.get("title", ""),
                    "body": (d.get("selftext") or "")[:400],
                    "url": "https://reddit.com" + d.get("permalink", ""),
                    "source": d.get("subreddit_name_prefixed", "Reddit"),
                    "category": "Social Media",
                    "published": "",
                    "score": d.get("score", 0),
                    "comments": d.get("num_comments", 0),
                })
        except Exception:
            pass
        return items

    def news(self, query: str, max_items: int = 25) -> list[dict]:
        items = []
        try:
            feed = feedparser.parse(
                f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            )
            for e in feed.entries[:max_items]:
                items.append({
                    "title": e.get("title", ""),
                    "body": re.sub(r"<[^>]+>", "", e.get("summary", ""))[:400],
                    "url": e.get("link", ""),
                    "source": e.get("source", {}).get("title", "News"),
                    "category": "News",
                    "published": e.get("published", ""),
                })
        except Exception:
            pass
        return items

    def duckduckgo(self, query: str) -> list[dict]:
        items = []
        try:
            data = requests.get(
                f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1",
                headers=_HEADERS, timeout=8,
            ).json()
            if data.get("AbstractText"):
                items.append({
                    "title": data.get("Heading", query),
                    "body": data["AbstractText"][:500],
                    "url": data.get("AbstractURL", ""),
                    "source": "DuckDuckGo",
                    "category": "Web Search",
                    "published": "",
                })
            for r in data.get("RelatedTopics", [])[:10]:
                if isinstance(r, dict) and "Text" in r:
                    items.append({
                        "title": r["Text"][:80],
                        "body": r["Text"][:300],
                        "url": r.get("FirstURL", ""),
                        "source": "DuckDuckGo",
                        "category": "Web Search",
                        "published": "",
                    })
        except Exception:
            pass
        return items

    def fetch_all(self, query: str) -> list[dict]:
        results = []
        for fn in (self.wikipedia, self.reddit, self.news, self.duckduckgo):
            results.extend(fn(query))
        return results
