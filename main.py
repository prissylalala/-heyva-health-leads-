import argparse
import csv
import json
import logging
import os
from background_checker import check_lead
from lead_finder import find_leads
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_manual_leads(csv_path: str) -> list[dict]:
    """Load leads from manual_leads.csv."""
    leads = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lead = {
                "name": row.get("name", "").strip(),
                "title": row.get("title", "").strip(),
                "company": row.get("company", "").strip(),
                "industry": row.get("industry", "").strip(),
                "linkedin_url": row.get("linkedin_url", "").strip(),
                "linkedin_about": row.get("linkedin_about", "").strip(),
                "linkedin_posts": [p.strip() for p in row.get("linkedin_posts", "").split("|") if p.strip()],
            }
            if lead["name"]:
                leads.append(lead)
            else:
                logger.warning(f"Skipping lead with missing name: {row}")
    return leads


def run_pipeline(discover: bool = False):
    """Run Phase 1: optionally discover leads, then run background checks, output raw_leads.json."""
    # Step 0: Discover leads from LinkedIn if requested
    if discover:
        logger.info("Step 0: Discovering leads from LinkedIn...")
        find_leads()
        logger.info("Lead discovery complete. Proceeding to background checks.")

    # Load leads
    csv_path = config.MANUAL_LEADS_PATH
    if not os.path.exists(csv_path):
        logger.error(f"Manual leads file not found: {csv_path}")
        logger.info("Run with --discover flag or create leads_data/manual_leads.csv manually")
        return

    leads = load_manual_leads(csv_path)
    logger.info(f"Loaded {len(leads)} leads from {csv_path}")

    if not leads:
        logger.error("No valid leads found in CSV.")
        return

    # Run background checks
    enriched_leads = []
    for i, lead in enumerate(leads, 1):
        logger.info(f"Processing lead {i}/{len(leads)}: {lead['name']}")
        try:
            bg_data = check_lead(lead["name"], lead["company"])
            lead.update(bg_data)
            enriched_leads.append(lead)
        except Exception as e:
            logger.error(f"Failed to process {lead['name']}: {e}")
            lead["social_profiles"] = {"twitter": None, "facebook": None, "instagram": None}
            lead["social_posts"] = []
            lead["google_mentions"] = []
            lead["data_quality"] = "limited"
            enriched_leads.append(lead)

    # Save output
    os.makedirs(os.path.dirname(config.RAW_LEADS_PATH), exist_ok=True)
    with open(config.RAW_LEADS_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched_leads, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(enriched_leads)} leads to {config.RAW_LEADS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Heyva Health Lead Gen Pipeline")
    parser.add_argument("--discover", action="store_true", help="Discover leads from LinkedIn before background checks")
    args = parser.parse_args()
    run_pipeline(discover=args.discover)
