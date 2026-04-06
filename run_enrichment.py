#!/usr/bin/env python3
"""
Enrich existing leads with social media data and email guesses.
Scrapes LinkedIn profiles and Twitter/X for posts, activity, language style.

Usage:
    python3 run_enrichment.py              # enrich all leads missing data
    python3 run_enrichment.py --limit 20   # enrich first 20 only (firecrawl quota)
"""
import json
import argparse
import logging
import os
import config
from firecrawl import FirecrawlApp
from social_enricher import enrich_lead

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ANALYZED_FILE = os.path.join(config.LEADS_DATA_DIR, "indonesia_analyzed.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max leads to enrich (0 = all)")
    args = parser.parse_args()

    app = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)

    with open(ANALYZED_FILE, "r", encoding="utf-8") as f:
        leads = json.load(f)

    # Only enrich leads that are missing social data
    to_enrich = [l for l in leads if not l.get("linkedin_posts_scraped") and not l.get("email_guess")]
    if args.limit:
        to_enrich = to_enrich[:args.limit]

    logger.info(f"Enriching {len(to_enrich)} leads (out of {len(leads)} total)")

    lead_index = {l.get("linkedin_url", ""): i for i, l in enumerate(leads)}
    success = 0

    for i, lead in enumerate(to_enrich, 1):
        name = lead.get("name", "Unknown")
        url  = lead.get("linkedin_url", "")
        logger.info(f"[{i}/{len(to_enrich)}] Enriching {name}...")

        try:
            updates = enrich_lead(lead, app)
            if updates:
                idx = lead_index.get(url)
                if idx is not None:
                    leads[idx].update(updates)
                success += 1
                logger.info(f"  ✓ email_guess={updates.get('email_guess','')} | "
                            f"li_posts={len(updates.get('linkedin_posts_scraped',[]))} | "
                            f"tw_posts={len(updates.get('twitter_posts_scraped',[]))}")
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")

        # Save every 10 leads
        if i % 10 == 0:
            with open(ANALYZED_FILE, "w", encoding="utf-8") as f:
                json.dump(leads, f, indent=2, ensure_ascii=False)
            logger.info(f"  → Progress saved ({i} done)")

    # Final save
    with open(ANALYZED_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    logger.info(f"\nDone! {success}/{len(to_enrich)} enriched.")
    logger.info(f"Saved to {ANALYZED_FILE}")


if __name__ == "__main__":
    main()
