# SUSS OpenClaw — Heyva Health Lead Gen & Profiling Tool

## What This Does
Finds HR Directors and CFOs on LinkedIn (Indonesia focus), runs Google background checks, analyzes their communication style, generates personalized outreach messages for Heyva Health, and provides a tracking dashboard.

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the dashboard (already has 38 analyzed Indonesia leads)
```bash
python3 -m streamlit run dashboard.py
```
Opens at http://localhost:8501

### 3. To find NEW leads
```bash
# Requires firecrawl CLI installed (npm install -g firecrawl)
python3 main.py --discover
```

### 4. To run background checks (requires Google API key)
```bash
export GOOGLE_API_KEY="your-key"
export GOOGLE_CSE_ID="your-cse-id"
python3 main.py
```

### 5. To run tone analysis (Phase 2 — uses Claude Code subscription)
```bash
claude "Read leads_data/raw_leads.json and analyze each lead following analyze.md. Write output to leads_data/analyzed_leads.json"
```

### 6. To generate Excel
```bash
python3 excel_writer.py
```

## File Structure
```
suss_openclaw/
├── config.py              # Search filters, API keys, paths
├── lead_finder.py         # Discovers leads on LinkedIn via web search
├── background_checker.py  # Google + social media background checks
├── main.py                # Pipeline orchestrator (--discover flag)
├── analyze.md             # Claude Code prompt for tone analysis
├── excel_writer.py        # Generates formatted Excel output
├── linkedin_scraper.py    # Optional automated LinkedIn scraper
├── dashboard.py           # Streamlit tracking dashboard
├── requirements.txt       # Python dependencies
├── leads_data/            # All lead data (JSON + CSV)
│   ├── manual_leads.csv
│   ├── indonesia_analyzed.json  # 38 Indonesia leads with priority scores
│   ├── analyzed_batch1.json     # Global leads batch 1 (CFOs)
│   ├── analyzed_batch2.json     # Global leads batch 2 (HR Directors)
│   └── ...
├── output/                # Generated Excel files
└── docs/                  # Design spec and implementation plan
```

## Pipeline Flow
1. `lead_finder.py` — search LinkedIn for leads via firecrawl
2. `main.py` — load leads from CSV, run Google background checks
3. Claude Code (Phase 2) — analyze tone, generate personalized outreach
4. `excel_writer.py` — output to formatted Excel
5. `dashboard.py` — track contacts, replies, meetings

## Dashboard Features
- Priority-sorted leads (P1-P5)
- Contact status tracking (Not Contacted / Contacted / Replied / Meeting)
- LinkedIn profile links
- Google background info
- Personalized outreach messages
- Filter by priority, status, role
- Export to Excel
- Hourly refresh

## Product: Heyva Health
- Financial risk exposure analysis for lifestyle diseases
- Biomarker-based insights from employee medical checkups
- Personalized health programs per employee
- Reduces healthcare costs and insurance claims

## Target Leads
- HR Directors, CFOs
- Oil & gas, MNCs, tech companies
- Companies with insurance/health reimbursement packages
- Focus: Indonesia
