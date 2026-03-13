import json
import random
import time
import logging
from typing import Optional
from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def google_search(name: str, company: str) -> list[dict]:
    """Search Google for a person at a company. Returns list of search results."""
    if not config.GOOGLE_API_KEY or not config.GOOGLE_CSE_ID:
        logger.warning("Google API key or CSE ID not set. Skipping Google search.")
        return []

    query = f'"{name}" "{company}"'
    try:
        service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
        result = service.cse().list(q=query, cx=config.GOOGLE_CSE_ID, num=10).execute()
        items = result.get("items", [])
        return [{"title": item.get("title", ""), "link": item.get("link", ""), "snippet": item.get("snippet", "")} for item in items]
    except Exception as e:
        logger.error(f"Google search failed for {name}: {e}")
        return []


def find_social_profiles(search_results: list[dict]) -> dict:
    """Extract social media profile URLs from Google search results."""
    profiles = {"twitter": None, "facebook": None, "instagram": None}
    for result in search_results:
        link = result.get("link", "").lower()
        if "twitter.com/" in link or "x.com/" in link:
            profiles["twitter"] = result["link"]
        elif "facebook.com/" in link:
            profiles["facebook"] = result["link"]
        elif "instagram.com/" in link:
            profiles["instagram"] = result["link"]
    return profiles


def scrape_public_posts(url: str, max_posts: int = 5) -> list[str]:
    """Attempt to scrape public posts from a social media profile URL.
    Returns list of post text. Returns empty list if blocked or private."""
    try:
        delay = random.uniform(*config.SCRAPE_DELAY_SECONDS)
        time.sleep(delay)
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Could not access {url}: HTTP {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        # Extract text from paragraphs and article tags as a general approach
        texts = []
        for tag in soup.find_all(["p", "article", "span"], limit=50):
            text = tag.get_text(strip=True)
            if len(text) > 30:
                texts.append(text)
        return texts[:max_posts]
    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return []


def check_lead(name: str, company: str) -> dict:
    """Run full background check for one lead. Returns dict with social profiles, posts, google mentions."""
    logger.info(f"Background checking: {name} at {company}")

    # Google search
    delay = random.uniform(*config.GOOGLE_DELAY_SECONDS)
    time.sleep(delay)
    search_results = google_search(name, company)

    # Extract social profiles
    social_profiles = find_social_profiles(search_results)

    # Scrape public posts from found social profiles
    social_posts = []
    for platform, url in social_profiles.items():
        if url:
            posts = scrape_public_posts(url)
            social_posts.extend(posts)

    # Google mentions (titles + snippets from non-social results)
    social_domains = ["twitter.com", "x.com", "facebook.com", "instagram.com", "linkedin.com"]
    google_mentions = [
        f"{r['title']} - {r['snippet']}"
        for r in search_results
        if not any(domain in r.get("link", "").lower() for domain in social_domains)
    ]

    # Determine data quality
    has_social = any(social_profiles.values())
    data_quality = "full" if has_social and social_posts else ("linkedin_only" if not has_social else "limited")

    return {
        "social_profiles": social_profiles,
        "social_posts": social_posts,
        "google_mentions": google_mentions,
        "data_quality": data_quality,
    }
