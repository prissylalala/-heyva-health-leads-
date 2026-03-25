"""
Lead Finder — Discovers HR Directors and CFOs on LinkedIn via web search.
Uses firecrawl Python SDK to search and scrape LinkedIn profiles.
"""
import json
import os
import logging
import config
from firecrawl import FirecrawlApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Search queries targeting different segments
SEARCH_QUERIES = [
    {
        "query": 'site:id.linkedin.com/in "HR Director" "oil" OR "gas" OR "energy" Indonesia',
        "role": "hr",
        "industry": "Oil & Gas",
    },
    {
        "query": 'site:id.linkedin.com/in "CFO" OR "Finance Director" "oil" OR "gas" Indonesia',
        "role": "cfo",
        "industry": "Oil & Gas",
    },
    {
        "query": 'site:id.linkedin.com/in "HR Director" technology Indonesia "employee wellness" OR "health benefit"',
        "role": "hr",
        "industry": "Technology",
    },
    {
        "query": 'site:id.linkedin.com/in "CFO" technology Indonesia "health insurance" OR "employee benefit"',
        "role": "cfo",
        "industry": "Technology",
    },
    {
        "query": 'site:id.linkedin.com/in "HR Director" manufacturing Indonesia "health" OR "benefit"',
        "role": "hr",
        "industry": "Manufacturing",
    },
    {
        "query": 'site:id.linkedin.com/in "CFO" manufacturing Indonesia "insurance" OR "employee"',
        "role": "cfo",
        "industry": "Manufacturing",
    },
    {
        "query": 'site:id.linkedin.com/in "HR Director" hospitality Indonesia Jakarta Bali',
        "role": "hr",
        "industry": "Hospitality",
    },
    {
        "query": 'site:id.linkedin.com/in "HR Director" "real estate" OR "property" Indonesia Jakarta',
        "role": "hr",
        "industry": "Real Estate",
    },
    {
        "query": 'site:id.linkedin.com/in "HR Director" OR "People Director" MNC Indonesia Jakarta "wellbeing" OR "wellness"',
        "role": "hr",
        "industry": "MNC",
    },
]


_firecrawl_app = None

def get_firecrawl():
    global _firecrawl_app
    if _firecrawl_app is None:
        _firecrawl_app = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)
    return _firecrawl_app


def run_search(query: str, output_file: str, limit: int = 10) -> list:
    """Run a firecrawl search and return list of result dicts."""
    logger.info(f"Searching: {query[:80]}...")
    try:
        app = get_firecrawl()
        results = app.search(query, limit=limit)
        # Convert SearchData object to list of dicts
        web_results = results.web if hasattr(results, "web") and results.web else []
        data = [
            {
                "url": r.url,
                "title": r.title or "",
                "description": r.description or "",
            }
            for r in web_results
        ]
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        return data
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


def extract_leads_from_results(data: list, role: str, industry: str) -> list[dict]:
    """Extract lead info from firecrawl search results."""
    leads = []
    results = data if isinstance(data, list) else []

    for r in results:
        url = r.get("url", "")
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

        leads = extract_leads_from_results(data, search["role"], search["industry"])  # type: ignore

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
