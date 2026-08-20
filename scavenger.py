import argparse, json, logging, os, random, re, sys
from datetime import datetime, timezone
try:
    import requests
except ImportError:
    requests = None
try:
    import feedparser
except ImportError:
    feedparser = None

logger = logging.getLogger("scavenger")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

DEFAULT_RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://www.reddit.com/r/technology/.rss",
    "https://www.reddit.com/r/science/.rss",
]

EVERGREEN_TOPICS = [
    {"headline": "Why the ocean is the next frontier for climate innovation", "source": "evergreen", "keywords": ["climate", "ocean", "innovation"]},
    {"headline": "The rise of AI-generated art and what it means for creators", "source": "evergreen", "keywords": ["AI", "art", "creators"]},
    {"headline": "How small habits compound into massive life changes", "source": "evergreen", "keywords": ["habits", "life", "productivity"]},
    {"headline": "A beginner's guide to understanding the stock market", "source": "evergreen", "keywords": ["stock market", "finance", "beginner"]},
    {"headline": "The psychology behind why we procrastinate", "source": "evergreen", "keywords": ["psychology", "procrastination", "productivity"]},
    {"headline": "Why space exploration is entering a new golden age", "source": "evergreen", "keywords": ["space", "exploration", "science"]},
    {"headline": "The future of renewable energy technologies", "source": "evergreen", "keywords": ["energy", "renewable", "future"]}
]

NORMALIZE_RE = re.compile(r"[^a-z0-9 ]+")
STOP_WORDS = {"this", "that", "with", "from", "have", "will", "your", "what", "when", "where", "which", "about", "their", "there"}

def normalize_title(s): return NORMALIZE_RE.sub("", s.lower()).strip()
def extract_keywords(text):
    words = re.findall(r"[A-Za-z]{4,}", text.lower())
    return list(dict.fromkeys([w for w in words if w not in STOP_WORDS]))[:8]

def fetch_rss(feeds):
    if feedparser is None: return []
    items = []
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:8]:
                if entry.get("link") and entry.get("title"):
                    title = entry.title.strip()
                    items.append({"headline": title, "url": entry.link, "source": url, "keywords": extract_keywords(title)})
        except Exception: pass
    return items

def generate_seeds(n=7):
    candidates = []
    rss_env = os.getenv("RSS_FEEDS")
    rss_feeds = [f.strip() for f in rss_env.split(",") if f.strip()] if rss_env else DEFAULT_RSS_FEEDS
    candidates.extend(fetch_rss(rss_feeds))

    seen, unique = set(), []
    for c in candidates:
        norm = normalize_title(c.get("headline", ""))
        if not norm or norm in seen: continue
        seen.add(norm)
        unique.append(c)

    rng = random.Random(datetime.now(timezone.utc).strftime("%Y%m%d"))
    rng.shuffle(unique)

    seeds = []
    for i, c in enumerate(unique[:n]):
        seeds.append({"seed_id": f"seed-{i+1:02d}", "headline": c["headline"], "topic": c["headline"], "url": c.get("url", ""), "source": c.get("source", "unknown"), "keywords": c.get("keywords", [])})
    
    if len(seeds) < n:
        for topic in EVERGREEN_TOPICS:
            if len(seeds) >= n: break
            if normalize_title(topic["headline"]) in seen: continue
            seeds.append({"seed_id": f"seed-{len(seeds)+1:02d}", "headline": topic["headline"], "topic": topic["headline"], "url": "", "source": topic["source"], "keywords": topic["keywords"]})
    return seeds[:n]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=7)
    parser.add_argument("--output", type=str, default="seeds.json")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--input", type=str, default="seeds.json")
    args = parser.parse_args()

    if args.matrix:
        with open(args.input, "r", encoding="utf-8") as f: seeds = json.load(f)
        print(json.dumps({"include": [{"seed_index": i, "seed_id": s["seed_id"]} for i, s in enumerate(seeds)]}))
        return

    seeds = generate_seeds(args.n)
    with open(args.output, "w", encoding="utf-8") as f: json.dump(seeds, f, indent=2)
    logger.info("Wrote %d seeds to %s", len(seeds), args.output)

if __name__ == "__main__": main()
