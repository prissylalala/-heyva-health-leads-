import os

# Search filters
TARGET_TITLES = ["HR Director", "CFO", "Chief Financial Officer", "Head of HR"]
TARGET_INDUSTRIES = ["Oil & Gas", "Technology", "MNC", "E-Commerce", "FMCG", "Banking & Finance"]
TARGET_CRITERIA = ["insurance", "health reimbursement", "employee benefits"]

# Rate limiting
GOOGLE_DELAY_SECONDS = (2, 5)
SCRAPE_DELAY_SECONDS = (3, 8)

# Google Custom Search API (free tier: 100 queries/day)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")

# Firecrawl API
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "fc-652abbe6be484b599ad2d9467cd6a134")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_DATA_DIR = os.path.join(BASE_DIR, "leads_data")
RAW_LEADS_PATH = os.path.join(LEADS_DATA_DIR, "raw_leads.json")
ANALYZED_LEADS_PATH = os.path.join(LEADS_DATA_DIR, "analyzed_leads.json")
MANUAL_LEADS_PATH = os.path.join(LEADS_DATA_DIR, "manual_leads.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
