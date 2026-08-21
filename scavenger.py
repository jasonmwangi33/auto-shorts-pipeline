import argparse
import json
import logging
import random
import re
import html
from datetime import datetime, timezone

try:
    import feedparser
except ImportError:
    feedparser = None

logger = logging.getLogger("scavenger")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

REDDIT_FEEDS = [
    "https://www.reddit.com/r/AmItheAsshole/top/.rss?t=day",
    "https://www.reddit.com/r/confession/top/.rss?t=day",
    "https://www.reddit.com/r/TrueOffMyChest/top/.rss?t=day",
    "https://www.reddit.com/r/pettyrevenge/top/.rss?t=day"
]

EVERGREEN_STORIES = [
    {
        "headline": "AITA for refusing to attend my sister's wedding after what she did?",
        "topic": "r/AmItheAsshole",
        "subreddit": "r/AmItheAsshole",
        "keywords": ["wedding", "sister", "family", "drama"]
    },
    {
        "headline": "I discovered my coworker has been taking credit for my work for six months.",
        "topic": "r/TrueOffMyChest",
        "subreddit": "r/TrueOffMyChest",
        "keywords": ["workplace", "coworker", "revenge", "career"]
    },
    {
        "headline": "My landlord tried to keep my deposit, so I used the law against him.",
        "topic": "r/pettyrevenge",
        "subreddit": "r/pettyrevenge",
        "keywords": ["landlord", "deposit", "petty", "justice"]
    },
    {
        "headline": "When did you realize someone was living in their own movie?",
        "topic": "r/AskReddit",
        "subreddit": "r/AskReddit",
        "keywords": ["reddit", "stories", "delusional", "funny"]
    }
]

def fetch_reddit_stories(n: int = 7) -> list:
    candidates = []
    if feedparser is not None:
        for url in REDDIT_FEEDS:
            try:
                parsed = feedparser.parse(url)
                sub_match = re.search(r'r/(\w+)', url)
                sub_name = f"r/{sub_match.group(1)}" if sub_match else "r/RedditStories"
                
                for entry in parsed.entries[:6]:
                    title = entry.title.strip()
                    clean_title = re.sub(r'\[.*?\]', '', title).strip()
                    if len(clean_title) < 15:
                        continue
                    candidates.append({
                        "headline": clean_title,
                        "topic": sub_name,
                        "subreddit": sub_name,
                        "url": entry.link,
                        "source": "reddit",
                        "keywords": ["reddit", "story", "drama", "aita"]
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")

    rng = random.Random(datetime.now(timezone.utc).strftime("%Y%m%d"))
    rng.shuffle(candidates)

    seeds = []
    for i, c in enumerate(candidates[:n]):
        c["seed_id"] = f"seed-{i+1:02d}"
        c["seed_index"] = i
        seeds.append(c)

    # Backfill with evergreen drama if needed
    idx = len(seeds)
    while len(seeds) < n:
        backup = dict(EVERGREEN_STORIES[idx % len(EVERGREEN_STORIES)])
        backup["seed_id"] = f"seed-{idx+1:02d}"
        backup["seed_index"] = idx
        seeds.append(backup)
        idx += 1

    return seeds[:n]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=7)
    parser.add_argument("--output", type=str, default="seeds.json")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--input", type=str, default="seeds.json")
    args = parser.parse_args()

    if args.matrix:
        with open(args.input, "r", encoding="utf-8") as f:
            seeds = json.load(f)
        print(json.dumps({"include": [{"seed_index": i, "seed_id": s["seed_id"]} for i, s in enumerate(seeds)]}))
        return

    seeds = fetch_reddit_stories(args.n)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(seeds, f, indent=2)
    logger.info(f"Successfully saved {len(seeds)} Reddit stories to {args.output}")

if __name__ == "__main__":
    main()
