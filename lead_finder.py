"""
Lead Finder — Discovers HR Directors and CFOs on LinkedIn via web search.
Uses firecrawl CLI to search and scrape LinkedIn profiles.
"""
import json
import os
import subprocess
import logging
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Search queries targeting different segments
SEARCH_QUERIES = [
    {
        "query": 'site:linkedin.com/in HR Director oil gas company Singapore employee benefits insurance',
        "role": "hr",
        "industry": "Oil & Gas",
    },
    {
        "query": 'site:linkedin.com/in CFO oil gas company Asia Pacific',
        "role": "cfo",
        "industry": "Oil & Gas",
    },
    {
        "query": 'site:linkedin.com/in HR Director technology company Singapore employee wellness health',
        "role": "hr",
        "industry": "Technology",
    },
    {
        "query": 'site:linkedin.com/in CFO technology MNC Singapore health insurance benefits',
        "role": "cfo",
        "industry": "Technology",
    },
    {
        "query": 'site:linkedin.com/in HR Director MNC Singapore healthcare benefits',
        "role": "hr",
        "industry": "MNC",
    },
    {
        "query": 'site:linkedin.com/in CFO multinational Singapore insurance employee',
        "role": "cfo",
        "industry": "MNC",
    },
]


def run_search(query: str, output_file: str, limit: int = 10) -> dict:
    """Run a firecrawl search and return results."""
    cmd = [
        "firecrawl", "search", query,
        "--limit", str(limit),
        "--scrape",
        "-o", output_file,
        "--json",
    ]
    logger.info(f"Searching: {query[:80]}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"Search failed: {result.stderr}")
            return {}
        with open(output_file) as f:
            return json.load(f)
    except subprocess.TimeoutExpired:
        logger.error(f"Search timed out for: {query[:50]}")
        return {}
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {}


def extract_leads_from_results(data: dict, role: str, industry: str) -> list[dict]:
    """Extract lead info from firecrawl search results."""
    leads = []
    results = data.get("data", [])
    if isinstance(data.get("data"), dict):
        results = data["data"].get("web", [])

    for r in results:
        url = r.get("url", r.get("link", ""))
        if not url or "linkedin.com/in/" not in url:
            continue

        title = r.get("title", "")
        description = r.get("description", r.get("snippet", ""))
        markdown = r.get("markdown", r.get("content", ""))

        # Parse name and job title from LinkedIn title format: "Name - Title - LinkedIn"
        name = ""
        job_title = ""
        if " - " in title:
            parts = title.split(" - ")
            name = parts[0].strip()
            job_parts = [p.strip() for p in parts[1:] if "linkedin" not in p.lower()]
            job_title = " - ".join(job_parts) if job_parts else ""

        # Try to extract company from description or markdown
        company = ""
        if markdown:
            for line in markdown.split("\n"):
                if "experience" in line.lower() or "current" in line.lower():
                    company = line.strip()[:100]
                    break

        lead = {
            "name": name,
            "title": job_title,
            "company": company,
            "industry": industry,
            "linkedin_url": url.split("?")[0],
            "linkedin_about": description[:500] if description else "",
            "linkedin_posts": [],
            "search_role": role,
            "raw_markdown": markdown[:3000] if markdown else "",
        }
        leads.append(lead)

    return leads


def find_leads(limit_per_query: int = 10) -> list[dict]:
    """Run all searches and return deduplicated leads."""
    firecrawl_dir = os.path.join(config.BASE_DIR, ".firecrawl")
    os.makedirs(firecrawl_dir, exist_ok=True)

    all_leads = []
    seen_urls = set()

    for i, search in enumerate(SEARCH_QUERIES, 1):
        output_file = os.path.join(firecrawl_dir, f"search-{search['role']}-{search['industry'].lower().replace(' ', '-').replace('&', '')}-{i}.json")
        data = run_search(search["query"], output_file, limit=limit_per_query)

        if not data:
            continue

        leads = extract_leads_from_results(data, search["role"], search["industry"])

        for lead in leads:
            if lead["linkedin_url"] not in seen_urls and lead["name"]:
                seen_urls.add(lead["linkedin_url"])
                all_leads.append(lead)

    logger.info(f"Found {len(all_leads)} unique leads across all searches")

    # Save discovered leads
    output_path = os.path.join(config.LEADS_DATA_DIR, "discovered_leads.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_leads, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved to {output_path}")

    # Also write to CSV for the main pipeline
    import csv
    csv_path = config.MANUAL_LEADS_PATH
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "title", "company", "industry", "linkedin_url", "linkedin_about", "linkedin_posts"])
        writer.writeheader()
        for lead in all_leads:
            writer.writerow({
                "name": lead["name"],
                "title": lead["title"],
                "company": lead["company"],
                "industry": lead["industry"],
                "linkedin_url": lead["linkedin_url"],
                "linkedin_about": lead["linkedin_about"],
                "linkedin_posts": "|".join(lead.get("linkedin_posts", [])),
            })
    logger.info(f"Wrote {len(all_leads)} leads to {csv_path}")

    return all_leads


if __name__ == "__main__":
    leads = find_leads()
    print(f"\n{'='*80}")
    print(f"LEAD DISCOVERY COMPLETE: {len(leads)} leads found")
    print(f"{'='*80}")
    for i, lead in enumerate(leads, 1):
        print(f"{i:2d}. {lead['name']:<30s} | {lead['title'][:40]:<40s} | {lead['industry']}")
