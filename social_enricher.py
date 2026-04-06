"""
Social Enricher — deep-scrapes LinkedIn profiles and Twitter/X for posts,
language style, interests, and campaigns. Also guesses company email.
"""
import re
import time
import logging
import unicodedata
import config
from firecrawl import FirecrawlApp

logger = logging.getLogger(__name__)

# ─── Known company domain mappings ───────────────────────────────────────────
KNOWN_DOMAINS = {
    "medco": "medcoenergi.com",
    "pertamina": "pertamina.com",
    "unilever": "unilever.com",
    "reckitt": "reckitt.com",
    "danone": "danone.com",
    "nestle": "nestle.com",
    "indofood": "indofood.co.id",
    "wings": "wingscorp.com",
    "telkom": "telkom.co.id",
    "bri": "bri.co.id",
    "bca": "bca.co.id",
    "mandiri": "bankmandiri.co.id",
    "bni": "bni.co.id",
    "cimb": "cimbniaga.co.id",
    "danamon": "danamon.co.id",
    "permata": "permatabank.co.id",
    "allianz": "allianz.co.id",
    "axa": "axa.co.id",
    "cigna": "cigna.co.id",
    "prudential": "prudential.co.id",
    "manulife": "manulife.co.id",
    "siemens": "siemens.com",
    "shell": "shell.com",
    "chevron": "chevron.com",
    "repsol": "repsol.com",
    "total": "totalenergies.com",
    "exxon": "exxonmobil.com",
    "bp": "bp.com",
    "schlumberger": "slb.com",
    "halliburton": "halliburton.com",
    "tokopedia": "tokopedia.com",
    "shopee": "shopee.co.id",
    "lazada": "lazada.co.id",
    "traveloka": "traveloka.com",
    "bukalapak": "bukalapak.com",
    "gojek": "gojek.com",
    "grab": "grab.com",
    "glico": "glico.co.id",
    "tetra": "tetrapak.com",
    "soho": "soho-indonesia.com",
    "goodyear": "goodyear.com",
    "inchcape": "inchcape.co.id",
    "chubb": "chubb.com",
    "takeda": "takeda.com",
    "sinarmas": "sinarmas.com",
    "keppel": "keppel.com",
    "deloitte": "deloitte.com",
    "godrej": "godrej.com",
    "gsk": "gsk.com",
    "glaxo": "gsk.com",
    "jumeirah": "jumeirah.com",
    "westin": "westin.com",
    "bocorocco": "bocorocco.com",
    "wom": "wom.co.id",
    "ace": "acehardware.co.id",
}


def normalise(text: str) -> str:
    """Lowercase, remove accents and non-alpha chars."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


def guess_domain(company: str) -> str:
    """Guess company email domain from company name."""
    if not company:
        return ""
    cleaned = normalise(company)
    for key, domain in KNOWN_DOMAINS.items():
        if key in cleaned:
            return domain
    # Strip common Indonesian company words and return a guess
    stripped = re.sub(
        r"\b(pt|tbk|cv|group|indonesia|persero|inc|ltd|corp|asia|global|international)\b",
        "", company, flags=re.IGNORECASE
    )
    stripped = re.sub(r"[^a-zA-Z0-9]", "", stripped).lower()
    if len(stripped) >= 3:
        return f"{stripped}.com"
    return ""


def guess_email(name: str, company: str) -> str:
    """
    Generate likely email address pattern.
    Returns e.g. 'dasril.dahya@medcoenergi.com' or 'dasril.dahya@[medcoenergi.com]' if unverified.
    """
    if not name:
        return ""
    # Clean name
    clean = normalise(name)
    parts = clean.split() if " " in name else [p for p in re.split(r"[^a-z]", clean) if p]
    # Use original name parts split by spaces
    name_parts = [normalise(p) for p in name.split() if normalise(p)]
    name_parts = [p for p in name_parts if len(p) > 1]  # remove single chars
    if not name_parts:
        return ""
    first = name_parts[0]
    last = name_parts[-1] if len(name_parts) > 1 else ""

    domain = guess_domain(company)
    if not domain:
        suffix = "[company.com]"
    else:
        suffix = domain

    if last and last != first:
        return f"{first}.{last}@{suffix}"
    return f"{first}@{suffix}"


def extract_linkedin_posts(markdown: str) -> list:
    """Parse recent posts/activity from a scraped LinkedIn profile markdown."""
    posts = []
    if not markdown:
        return posts

    lines = markdown.split("\n")
    in_activity = False
    buffer = []

    for line in lines:
        line_lower = line.lower().strip()
        # Detect start of activity/posts section
        if any(kw in line_lower for kw in ["activity", "posts", "artikel", "postingan"]):
            in_activity = True
            continue
        # Stop at next major section
        if in_activity and line.startswith("##") and "activit" not in line_lower:
            in_activity = False
        if in_activity and len(line.strip()) > 60:
            buffer.append(line.strip())
            if len(buffer) >= 4:
                posts.append(" ".join(buffer))
                buffer = []
                if len(posts) >= 5:
                    break

    # Fallback: grab any long paragraph-like lines from the page
    if not posts:
        for line in lines:
            if len(line.strip()) > 80 and not line.startswith("#") and not line.startswith("|"):
                posts.append(line.strip())
                if len(posts) >= 3:
                    break

    return [p[:500] for p in posts]


def extract_twitter_posts(markdown: str) -> list:
    """Parse tweets from a scraped Twitter/X profile page markdown."""
    posts = []
    if not markdown:
        return posts
    lines = markdown.split("\n")
    for line in lines:
        stripped = line.strip()
        # Tweets tend to be medium-length, no markdown headers
        if 40 < len(stripped) < 300 and not stripped.startswith("#") and not stripped.startswith("|"):
            posts.append(stripped)
            if len(posts) >= 8:
                break
    return posts


def find_twitter_url(lead: dict) -> str:
    """Find Twitter/X URL from existing social profiles or google mentions."""
    social = lead.get("social_profiles", {})
    if social.get("twitter"):
        return social["twitter"]
    # Try google_mentions
    for mention in lead.get("google_mentions", []):
        m = re.search(r"https?://(twitter|x)\.com/([A-Za-z0-9_]+)", mention)
        if m:
            return m.group(0)
    return ""


def scrape_linkedin(url: str, app: FirecrawlApp) -> dict:
    """Scrape a LinkedIn profile page. Returns dict with posts and full text."""
    try:
        time.sleep(2)
        result = app.scrape_url(url, formats=["markdown"])
        markdown = getattr(result, "markdown", "") or ""
        posts = extract_linkedin_posts(markdown)
        return {
            "linkedin_posts_scraped": posts,
            "linkedin_raw": markdown[:4000],
        }
    except Exception as e:
        logger.warning(f"LinkedIn scrape failed for {url}: {e}")
        return {}


def scrape_twitter(url: str, app: FirecrawlApp) -> dict:
    """Scrape a public Twitter/X profile. Returns dict with posts."""
    try:
        time.sleep(2)
        result = app.scrape_url(url, formats=["markdown"])
        markdown = getattr(result, "markdown", "") or ""
        posts = extract_twitter_posts(markdown)
        return {"twitter_posts_scraped": posts}
    except Exception as e:
        logger.warning(f"Twitter scrape failed for {url}: {e}")
        return {}


def enrich_lead(lead: dict, app: FirecrawlApp) -> dict:
    """
    Run full social enrichment for one lead.
    Returns a dict of new fields to merge into the lead.
    """
    updates = {}

    # 1. Guess email if not already set
    if not lead.get("email_guess"):
        email = guess_email(lead.get("name", ""), lead.get("company", "") or lead.get("title", ""))
        updates["email_guess"] = email

    # 2. Scrape LinkedIn profile for posts
    linkedin_url = lead.get("linkedin_url", "")
    if linkedin_url and not lead.get("linkedin_posts_scraped"):
        li_data = scrape_linkedin(linkedin_url, app)
        updates.update(li_data)

    # 3. Scrape Twitter/X if URL available
    twitter_url = find_twitter_url(lead)
    if twitter_url and not lead.get("twitter_posts_scraped"):
        tw_data = scrape_twitter(twitter_url, app)
        updates.update(tw_data)

    return updates
