"""
Heyva Health — Lead CRM Dashboard (Kanban)
Run with: streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
import json
import os
import random
from datetime import datetime
import pydeck as pdk

# ─── Config ──────────────────────────────────────────────────────────────────
DATA_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads_data")
TRACKING_FILE = os.path.join(DATA_DIR, "tracking.json")
ANALYZED_FILE = os.path.join(DATA_DIR, "indonesia_analyzed.json")
CURRENT_YEAR  = 2026

st.set_page_config(page_title="Heyva Health CRM", page_icon="🏥", layout="wide")

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
.kanban-card {
    border-left: 4px solid #ccc;
    padding: 10px 12px;
    margin: 6px 0;
    background: #ffffff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    font-size: 13px;
}
.kanban-card.high  { border-left-color: #2ecc71; }
.kanban-card.mid   { border-left-color: #f1c40f; }
.kanban-card.low   { border-left-color: #e74c3c; }
.kanban-col-header {
    text-align: center;
    padding: 8px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 8px;
}
.badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    margin: 2px;
}
</style>
""", unsafe_allow_html=True)

# ─── Geography ────────────────────────────────────────────────────────────────
INDONESIA_CITIES = {
    "jakarta":    {"lat": -6.2088,  "lon": 106.8456, "label": "Jakarta"},
    "bekasi":     {"lat": -6.2383,  "lon": 106.9756, "label": "Bekasi"},
    "tangerang":  {"lat": -6.1783,  "lon": 106.6319, "label": "Tangerang"},
    "depok":      {"lat": -6.4025,  "lon": 106.7942, "label": "Depok"},
    "bogor":      {"lat": -6.5971,  "lon": 106.8060, "label": "Bogor"},
    "bandung":    {"lat": -6.9175,  "lon": 107.6191, "label": "Bandung"},
    "surabaya":   {"lat": -7.2575,  "lon": 112.7521, "label": "Surabaya"},
    "semarang":   {"lat": -6.9932,  "lon": 110.4203, "label": "Semarang"},
    "yogyakarta": {"lat": -7.7956,  "lon": 110.3695, "label": "Yogyakarta"},
    "medan":      {"lat": 3.5952,   "lon": 98.6722,  "label": "Medan"},
    "palembang":  {"lat": -2.9761,  "lon": 104.7754, "label": "Palembang"},
    "bali":       {"lat": -8.6705,  "lon": 115.2126, "label": "Bali"},
    "denpasar":   {"lat": -8.6705,  "lon": 115.2126, "label": "Bali"},
    "makassar":   {"lat": -5.1477,  "lon": 119.4327, "label": "Makassar"},
    "balikpapan": {"lat": -1.2379,  "lon": 116.8529, "label": "Balikpapan"},
    "batam":      {"lat": 1.0457,   "lon": 104.0305, "label": "Batam"},
    "manado":     {"lat": 1.4748,   "lon": 124.8421, "label": "Manado"},
    "pekanbaru":  {"lat": 0.5071,   "lon": 101.4478, "label": "Pekanbaru"},
    "banten":     {"lat": -6.1200,  "lon": 106.1503, "label": "Banten"},
    "serang":     {"lat": -6.1200,  "lon": 106.1503, "label": "Banten"},
    "cilegon":    {"lat": -6.0025,  "lon": 106.0513, "label": "Banten"},
}
INDONESIA_SIGNALS = ["indonesia", "jakarta", "surabaya", "bandung", "bali", "medan", "indonesian"]


def is_indonesia_verified(lead: dict) -> bool:
    if "id.linkedin.com" in lead.get("linkedin_url", ""):
        return True
    text = " ".join([lead.get("linkedin_about", ""), lead.get("title", ""), lead.get("company", "")]).lower()
    return any(s in text for s in INDONESIA_SIGNALS)


def detect_city(lead: dict) -> str:
    text = " ".join([
        lead.get("linkedin_url", ""), lead.get("linkedin_about", ""),
        lead.get("company", ""), " ".join(lead.get("google_mentions", [])),
    ]).lower()
    for city_key in INDONESIA_CITIES:
        if city_key in text:
            return city_key
    return "jakarta"


def is_active_profile(lead: dict) -> bool:
    """
    Returns False for thin/inactive profiles:
    - Very short LinkedIn about (likely no real profile / no photo)
    - No google mentions AND no social posts AND linkedin_only data quality
    Deprioritised in the New Leads tab.
    """
    about_len = len(lead.get("linkedin_about", ""))
    has_google = bool(lead.get("google_mentions"))
    has_posts  = bool(lead.get("social_posts"))
    has_bg     = bool(lead.get("google_background"))
    if about_len < 100 and not has_google and not has_posts and not has_bg:
        return False
    return True


def has_current_content(text: str) -> bool:
    """Check if text references current years (2024–2026)."""
    return any(yr in text for yr in ["2024", "2025", "2026"])


# ─── Scoring ──────────────────────────────────────────────────────────────────
HEYVA_INTEREST_KEYWORDS = [
    "health", "wellness", "wellbeing", "well-being", "medical", "insurance",
    "benefits", "employee health", "lifestyle", "disease", "biomarker",
    "healthcare", "cost reduction", "risk", "preventive", "prevention",
    "mental health", "occupational health", "benefit", "reimbursement",
]
HEALTH_GENEROSITY_KEYWORDS = [
    "wellness program", "health benefit", "employee wellbeing", "wellbeing program",
    "health initiative", "medical benefit", "health reimbursement", "health budget",
    "employee health", "occupational health", "mental health program", "wellness budget",
    "health insurance", "benefit package", "health allowance", "medical checkup",
    "health subsidy", "wellness initiative", "employee assistance", "health fund",
    "corporate wellness", "preventive health", "medical coverage", "health plan",
    "well-being", "health culture", "healthy workplace",
]
INDUSTRY_SCORES = {
    "oil_gas":         (["oil", "gas", "energy", "petroleum", "refinery", "mining", "petrochemical"], 25),
    "pharma_health":   (["pharma", "pharmaceutical", "health", "medical", "hospital", "biotech", "clinic"], 24),
    "mnc":             (["multinational", "mnc", "global", "international", "unilever", "reckitt", "danone", "nestle", "shell", "chevron", "exxon"], 22),
    "banking_finance": (["banking", "bank", "bri", "bca", "mandiri", "bni", "cimb", "danamon", "permata", "financial services", "multifinance", "insurance", "asset management", "investment"], 22),
    "fmcg":            (["fmcg", "consumer goods", "fast moving", "unilever", "nestle", "danone", "indofood", "wings", "coca-cola", "p&g", "procter"], 20),
    "ecommerce":       (["e-commerce", "ecommerce", "marketplace", "tokopedia", "shopee", "lazada", "traveloka", "bukalapak", "blibli", "gojek", "grab"], 20),
    "manufacturing":   (["manufacturing", "factory", "production", "industrial", "textile", "automotive", "cement", "steel"], 20),
    "tech":            (["technology", "tech", "software", "it ", "digital", "startup", "saas", "fintech"], 18),
    "hospitality":     (["hospitality", "hotel", "resort", "tourism", "travel", "airline", "catering", "restaurant", "leisure"], 18),
    "real_estate":     (["real estate", "property", "developer", "construction", "infrastructure", "realty"], 15),
    "media_news":      (["media", "news", "publishing", "broadcast", "television", "radio", "journalist", "entertainment", "advertising"], 15),
    "finance":         (["finance", "financial", "cfo", "treasury", "accounting"], 18),
}
INDUSTRY_LABELS = {
    "oil_gas": "Oil & Gas", "pharma_health": "Pharma / Health", "mnc": "MNC",
    "banking_finance": "Banking & Finance", "fmcg": "FMCG", "ecommerce": "E-Commerce",
    "manufacturing": "Manufacturing", "tech": "Tech", "hospitality": "Hospitality",
    "real_estate": "Real Estate", "media_news": "Media & News", "finance": "Finance", "other": "Other",
}


def detect_industry(lead: dict) -> tuple:
    searchable = " ".join([
        lead.get("industry", ""), lead.get("company", ""), lead.get("title", ""),
        " ".join(lead.get("google_mentions", [])), lead.get("linkedin_about", ""),
    ]).lower()
    for key, (kws, score) in INDUSTRY_SCORES.items():
        if any(kw in searchable for kw in kws):
            return key, score
    return "other", 5


def score_role(lead: dict) -> tuple:
    t = lead.get("title", "").lower()
    if any(k in t for k in ["hr director", "human resources director", "people director", "head of hr", "chief people"]):
        return 25, "HR Director"
    if any(k in t for k in ["hr", "human resources", "people", "talent", "hrd"]):
        return 20, "HR"
    if any(k in t for k in ["cfo", "chief financial", "finance director", "head of finance", "vp finance"]):
        return 22, "CFO/Finance"
    if any(k in t for k in ["ceo", "president", "managing director", "general manager"]):
        return 18, "C-Suite"
    return 8, "Other"


def score_health_generosity(lead: dict) -> tuple:
    searchable = " ".join([
        lead.get("linkedin_about", ""), lead.get("tone_profile", ""),
        lead.get("google_background", ""), " ".join(lead.get("google_mentions", [])),
        " ".join(lead.get("social_posts", [])),
        " ".join(lead.get("key_interests", []) if isinstance(lead.get("key_interests"), list) else []),
    ]).lower()
    matched = list(dict.fromkeys([kw for kw in HEALTH_GENEROSITY_KEYWORDS if kw in searchable]))
    if len(matched) >= 5: return 25, matched[:5]
    if len(matched) >= 3: return 18, matched[:3]
    if len(matched) >= 1: return 10, matched[:2]
    return 3, []


def score_data_quality(lead: dict) -> int:
    dq = lead.get("data_quality", "")
    return 15 if dq == "full" else 8 if dq == "limited" else 4


def score_interest_alignment(lead: dict) -> tuple:
    interests = lead.get("key_interests", [])
    if not isinstance(interests, list): interests = []
    searchable = " ".join(interests).lower()
    matched = list(dict.fromkeys([kw for kw in HEYVA_INTEREST_KEYWORDS if kw in searchable]))
    return min(10, len(matched) * 2), matched[:5]


def compute_lead_score(lead: dict) -> dict:
    role_score, role_label         = score_role(lead)
    industry_key, industry_score   = detect_industry(lead)
    generosity_score, gen_signals  = score_health_generosity(lead)
    quality_score                  = score_data_quality(lead)
    alignment_score, aligned       = score_interest_alignment(lead)
    total = role_score + industry_score + generosity_score + quality_score + alignment_score
    return {
        "total": total,
        "role_score": role_score, "role_label": role_label,
        "industry_key": industry_key, "industry_label": INDUSTRY_LABELS.get(industry_key, "Other"),
        "industry_score": industry_score, "generosity_score": generosity_score,
        "generosity_signals": gen_signals, "quality_score": quality_score,
        "alignment_score": alignment_score, "aligned_interests": aligned,
    }


def score_tier(total: int) -> str:
    return "High Fit" if total >= 70 else "Medium Fit" if total >= 50 else "Low Fit"


def tier_css(total: int) -> str:
    return "high" if total >= 70 else "mid" if total >= 50 else "low"


def score_color(total: int) -> str:
    return "🟢" if total >= 70 else "🟡" if total >= 50 else "🔴"


# ─── Tone & Engagement ────────────────────────────────────────────────────────
TONE_KEYWORDS = {
    "Data-Driven":    ["data", "metric", "kpi", "roi", "analytics", "insight", "evidence", "results", "numbers", "performance"],
    "People-Focused": ["people", "employee", "team", "culture", "wellbeing", "talent", "human", "community", "empathy"],
    "Formal":         ["corporate", "strategic", "executive", "professional", "governance", "compliance", "stakeholder"],
    "Visionary":      ["innovation", "future", "transform", "disrupt", "pioneer", "vision", "change", "growth"],
    "Cost-Conscious": ["cost", "saving", "efficiency", "budget", "financial", "reduce", "optimize", "roi", "profit"],
}


def detect_tone_badges(lead: dict) -> list:
    searchable = " ".join([
        lead.get("tone_profile", ""), lead.get("linkedin_about", ""),
        " ".join(lead.get("social_posts", [])),
    ]).lower()
    badges = [b for b, kws in TONE_KEYWORDS.items() if sum(1 for kw in kws if kw in searchable) >= 2]
    return badges or ["Balanced"]


def get_engagement_angle(lead: dict, score: dict) -> str:
    """Build a specific, current engagement angle using actual lead data."""
    role      = score["role_label"]
    tone      = detect_tone_badges(lead)
    company   = lead.get("company", "their company") or "their company"
    interests = lead.get("key_interests", [])
    interest_str = ", ".join(interests[:2]) if isinstance(interests, list) and interests else ""
    gen_sigs  = score.get("generosity_signals", [])
    bg        = lead.get("google_background", "")

    # Pull a current-year reference if available
    recent_note = ""
    full_text = " ".join([bg, lead.get("tone_profile", ""), " ".join(lead.get("google_mentions", []))])
    for sentence in full_text.split("."):
        if any(yr in sentence for yr in ["2024", "2025", "2026"]):
            recent_note = sentence.strip()[:100]
            break

    if "CFO" in role or "Finance" in role:
        if "Data-Driven" in tone or "Cost-Conscious" in tone:
            base = f"Lead with financial risk data — quantify the cost of untreated lifestyle disease at {company}. Reference insurance claim reduction and absenteeism ROI."
        else:
            base = f"Frame Heyva as a cost-reduction tool for {company} — lower insurance claims, reduced absenteeism, measurable health-risk exposure."
    elif "HR" in role:
        if "People-Focused" in tone:
            base = f"Lead with employee wellbeing impact at {company} — personalised health programs, workforce morale, and retention."
            if interest_str:
                base += f" Connect to their interest in: {interest_str}."
        elif "Data-Driven" in tone:
            base = f"Lead with workforce health analytics for {company} — biomarker-based risk insights, measurable wellness ROI. They respond to evidence and numbers."
        else:
            base = f"Emphasise Heyva's personalised employee health programs and how they reduce HR's burden managing health-related absenteeism at {company}."
    else:
        base = f"Tailor pitch to their strategic priorities at {company}."
        if interest_str:
            base += f" Known interests: {interest_str}."

    if gen_sigs:
        base += f" They already show investment in: {gen_sigs[0]} — position Heyva as the next evolution of that."
    if recent_note:
        base += f" Recent context: {recent_note}."

    return base


# ─── Data I/O ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_leads():
    if not os.path.exists(ANALYZED_FILE):
        return []
    with open(ANALYZED_FILE, "r") as f:
        return json.load(f)


def load_tracking():
    if not os.path.exists(TRACKING_FILE):
        return {}
    with open(TRACKING_FILE, "r") as f:
        return json.load(f)


def save_tracking(tracking):
    with open(TRACKING_FILE, "w") as f:
        json.dump(tracking, f, indent=2, ensure_ascii=False)


# ─── Lead Detail Card (used in both tabs) ─────────────────────────────────────
STATUSES = ["Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Won", "Not Interested"]
STATUS_ICONS = {"Not Contacted": "⬜", "Contacted - No Reply": "📤", "Contacted - Replied": "📩",
                "Meeting Scheduled": "📅", "Won": "🏆", "Not Interested": "❌"}


def render_lead_detail(lead, sc, track, url, key_prefix, tracking):
    """Full lead detail inside an expander."""
    status  = track.get("status", "Not Contacted")
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.markdown("#### Fit Score Breakdown")
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Role Fit",        f"{sc['role_score']}/25",        help=sc['role_label'])
        s2.metric("Industry Fit",    f"{sc['industry_score']}/25",    help=sc['industry_label'])
        s3.metric("Health Generosity", f"{sc['generosity_score']}/25")
        s4.metric("Data Quality",    f"{sc['quality_score']}/15")
        s5.metric("Interest Match",  f"{sc['alignment_score']}/10")
        if sc["generosity_signals"]:
            st.caption(f"Health signals: {', '.join(sc['generosity_signals'])}")
        st.markdown("---")

        city_label = INDONESIA_CITIES[detect_city(lead)]["label"]
        st.markdown(f"**Company:** {lead.get('company', 'N/A')}")
        st.markdown(f"**Location:** {city_label}, Indonesia")
        st.markdown(f"**Industry:** {sc['industry_label']}")
        st.markdown(f"**LinkedIn:** [{url}]({url})")
        if lead.get("priority_reason"):
            st.markdown(f"**Priority Reason:** {lead.get('priority_reason')}")
        if lead.get("google_background"):
            st.markdown(f"**Background:** {lead.get('google_background')}")
        st.markdown("---")

        st.markdown("#### Engagement Guide")
        tone_badges = detect_tone_badges(lead)
        badge_str = " ".join([f"`{b}`" for b in tone_badges])
        st.markdown(f"**Style:** {badge_str}")
        if lead.get("tone_profile"):
            st.markdown(f"**Tone Profile:** {lead.get('tone_profile')}")
        if isinstance(lead.get("key_interests"), list) and lead["key_interests"]:
            st.markdown(f"**Key Interests:** {', '.join(lead['key_interests'])}")

        engagement = get_engagement_angle(lead, sc)
        st.info(f"**How to open:** {engagement}")
        st.markdown("---")

        # Messages — flag if stale (no current-year reference)
        conn_msg = lead.get("connection_message", "")
        follow_msg = lead.get("followup_message", "")
        if not conn_msg:
            conn_msg = f"Hi {lead.get('name','').split()[0] if lead.get('name') else 'there'}, I'd love to connect and share how Heyva Health helps {sc['role_label']}s in Indonesia reduce health-related costs."
        if not follow_msg:
            follow_msg = f"Thanks for connecting! Heyva Health uses biomarker analytics to help companies in {sc['industry_label']} reduce employee health risks and insurance costs. Would you have 15 minutes for a quick call?"

        if not has_current_content(conn_msg + follow_msg):
            st.warning("⚠️ Messages may not reference current activities — run tone analysis to refresh.")

        st.markdown("**Connection Message:**")
        st.code(conn_msg, language=None)
        st.markdown("**Follow-up Message:**")
        st.text_area("", follow_msg, height=100, key=f"{key_prefix}_followup", disabled=True)

        if isinstance(lead.get("talking_points"), list) and lead["talking_points"]:
            st.markdown("**Talking Points:**")
            for tp in lead["talking_points"]:
                st.markdown(f"- {tp}")

    with col_r:
        st.markdown("### Update Status")
        new_status = st.selectbox(
            "Status", STATUSES,
            index=STATUSES.index(status) if status in STATUSES else 0,
            key=f"{key_prefix}_status"
        )
        new_notes = st.text_area("Notes", track.get("notes", ""), height=120, key=f"{key_prefix}_notes")
        contact_date_val = track.get("contacted_date", "")
        new_date = st.date_input(
            "Date Contacted",
            value=datetime.strptime(contact_date_val, "%Y-%m-%d").date() if contact_date_val else None,
            key=f"{key_prefix}_date",
        )
        if st.button("💾 Save", key=f"{key_prefix}_save"):
            tracking[url] = {
                "status": new_status, "notes": new_notes,
                "contacted_date": new_date.isoformat() if new_date else "",
                "updated_at": datetime.now().isoformat(),
            }
            save_tracking(tracking)
            st.success("Saved!")
            st.rerun()


# ─── App ──────────────────────────────────────────────────────────────────────
st.title("Heyva Health — Lead CRM Dashboard 🏥")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')} · Refresh page to update")

leads = load_leads()
if not leads:
    st.error("No leads found. Run the pipeline first.")
    st.stop()

tracking = load_tracking()

# Pre-compute everything
lead_scores = {l.get("linkedin_url", ""): compute_lead_score(l) for l in leads}
lead_cities = {l.get("linkedin_url", ""): detect_city(l) for l in leads}

# Categorise each lead
for lead in leads:
    url = lead.get("linkedin_url", "")
    lead["_status"]  = tracking.get(url, {}).get("status", "Not Contacted")
    lead["_active"]  = is_active_profile(lead)
    lead["_sc"]      = lead_scores[url]
    lead["_total"]   = lead_scores[url]["total"]

# ─── Summary Metrics ──────────────────────────────────────────────────────────
total_leads = len(leads)
high_fit    = sum(1 for l in leads if l["_total"] >= 70)
contacted   = sum(1 for l in leads if l["_status"] != "Not Contacted")
replied     = sum(1 for l in leads if l["_status"] == "Contacted - Replied")
meetings    = sum(1 for l in leads if l["_status"] == "Meeting Scheduled")
won         = sum(1 for l in leads if l["_status"] == "Won")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Leads",    total_leads)
c2.metric("High Fit (70+)", high_fit)
c3.metric("In Pipeline",    contacted)
c4.metric("Replied",        replied)
c5.metric("Meetings",       meetings)
c6.metric("Won 🏆",         won)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_pipeline, tab_new, tab_map, tab_analytics = st.tabs(
    ["📋 Pipeline (CRM)", "🎯 New Leads", "🗺️ Map", "📊 Analytics"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PIPELINE / KANBAN
# ══════════════════════════════════════════════════════════════════════════════
with tab_pipeline:
    st.markdown("### Sales Pipeline")
    st.caption("Leads automatically move here once you set their status in New Leads or below.")

    PIPELINE_STAGES = [
        ("📤 Contacted",      "Contacted - No Reply",  "#3498db"),
        ("📩 Replied",        "Contacted - Replied",   "#9b59b6"),
        ("📅 Meeting",        "Meeting Scheduled",     "#e67e22"),
        ("🏆 Won",            "Won",                   "#2ecc71"),
        ("❌ Not Interested", "Not Interested",         "#95a5a6"),
    ]

    stage_cols = st.columns(len(PIPELINE_STAGES))

    for col_idx, (col_label, stage_status, col_color) in enumerate(PIPELINE_STAGES):
        stage_leads = sorted(
            [l for l in leads if l["_status"] == stage_status],
            key=lambda x: x["_total"], reverse=True
        )
        with stage_cols[col_idx]:
            st.markdown(
                f'<div class="kanban-col-header" style="background:{col_color}22; color:{col_color};">'
                f'{col_label}<br/><small style="font-weight:400">{len(stage_leads)} leads</small></div>',
                unsafe_allow_html=True
            )
            for i, lead in enumerate(stage_leads):
                url     = lead.get("linkedin_url", "")
                sc      = lead["_sc"]
                total   = lead["_total"]
                tier    = tier_css(total)
                track   = tracking.get(url, {})
                name    = lead.get("name", "Unknown")
                company = lead.get("company", "") or lead.get("title", "").split(" at ")[-1] if " at " in lead.get("title","") else ""
                title_short = lead.get("title", "")[:42]
                tone_badges = detect_tone_badges(lead)
                days_ago = ""
                cd = track.get("contacted_date", "")
                if cd:
                    try:
                        delta = (datetime.now().date() - datetime.strptime(cd, "%Y-%m-%d").date()).days
                        days_ago = f"· {delta}d ago"
                    except: pass

                with st.expander(f"{score_color(total)} {name}"):
                    st.markdown(f"**{title_short}**")
                    if company:
                        st.markdown(f"🏢 {company}")
                    st.markdown(f"Score: **{total}/75** {days_ago}")
                    st.markdown(" ".join([f"`{b}`" for b in tone_badges]))
                    st.markdown(f"[LinkedIn ↗]({url})")
                    render_lead_detail(lead, sc, track, url, f"pipe_{stage_status[:4]}_{i}", tracking)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — NEW LEADS
# ══════════════════════════════════════════════════════════════════════════════
with tab_new:
    # Only show Not Contacted leads
    new_leads = [l for l in leads if l["_status"] == "Not Contacted"]
    active_leads   = sorted([l for l in new_leads if l["_active"]],  key=lambda x: x["_total"], reverse=True)
    inactive_leads = sorted([l for l in new_leads if not l["_active"]], key=lambda x: x["_total"], reverse=True)

    # Sidebar-style filters within the tab
    st.markdown(f"### New Leads — {len(active_leads)} active profiles")

    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        tier_filter = st.selectbox("Fit Score", ["All", "High Fit (70+)", "Medium Fit (50-69)", "Low Fit (<50)"])
    with fcol2:
        all_industries = sorted(set(l["_sc"]["industry_label"] for l in active_leads))
        ind_filter = st.multiselect("Industry", all_industries, default=all_industries)
    with fcol3:
        all_roles = sorted(set(l["_sc"]["role_label"] for l in active_leads))
        role_filter = st.multiselect("Role", all_roles, default=all_roles)
    with fcol4:
        all_cities = sorted(set(INDONESIA_CITIES[lead_cities[l.get("linkedin_url","")]]["label"] for l in active_leads))
        city_filter = st.multiselect("City", all_cities, default=all_cities)

    def passes_filter(lead):
        sc    = lead["_sc"]
        total = lead["_total"]
        if tier_filter == "High Fit (70+)" and total < 70: return False
        if tier_filter == "Medium Fit (50-69)" and not (50 <= total < 70): return False
        if tier_filter == "Low Fit (<50)" and total >= 50: return False
        if sc["industry_label"] not in ind_filter: return False
        if sc["role_label"] not in role_filter: return False
        city_lbl = INDONESIA_CITIES[lead_cities[lead.get("linkedin_url","")]]["label"]
        if city_lbl not in city_filter: return False
        return True

    filtered = [l for l in active_leads if passes_filter(l)]
    st.caption(f"Showing {len(filtered)} leads")

    for i, lead in enumerate(filtered):
        url   = lead.get("linkedin_url", "")
        sc    = lead["_sc"]
        total = lead["_total"]
        track = tracking.get(url, {})

        missing_analysis = not lead.get("tone_profile")
        tone_note = " ⚠️ pending analysis" if missing_analysis else ""

        with st.expander(
            f"{score_color(total)} {total}/75 | {sc['role_label']} | 🇮🇩 {lead.get('name','Unknown')} — {lead.get('title','')[:50]}{tone_note}"
        ):
            render_lead_detail(lead, sc, track, url, f"new_{i}", tracking)

    # ── Thin / Low-priority profiles ──────────────────────────────────────────
    if inactive_leads:
        with st.expander(f"⚠️ Low Priority — Inactive / Incomplete Profiles ({len(inactive_leads)})"):
            st.caption("These profiles have minimal LinkedIn content and no online activity signals. They may not have a profile photo or active presence. Review manually before outreach.")
            for i, lead in enumerate(inactive_leads):
                url   = lead.get("linkedin_url", "")
                sc    = lead["_sc"]
                total = lead["_total"]
                track = tracking.get(url, {})
                with st.expander(f"⚫ {total}/75 | {lead.get('name','Unknown')} — {lead.get('title','')[:50]}"):
                    render_lead_detail(lead, sc, track, url, f"inactive_{i}", tracking)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab_map:
    st.markdown("### Lead Map — Indonesia")
    map_rows = []
    for lead in leads:
        url      = lead.get("linkedin_url", "")
        sc       = lead["_sc"]
        total    = lead["_total"]
        city_key = lead_cities[url]
        ci       = INDONESIA_CITIES[city_key]
        random.seed(url)
        map_rows.append({
            "lat": ci["lat"] + random.uniform(-0.08, 0.08),
            "lon": ci["lon"] + random.uniform(-0.08, 0.08),
            "name": lead.get("name", "Unknown"),
            "title": lead.get("title", ""),
            "city": ci["label"],
            "score": total,
            "tier": score_tier(total),
            "status": lead["_status"],
            "r": 50 if total >= 70 else (255 if total >= 50 else 220),
            "g": 180 if total >= 70 else (200 if total >= 50 else 50),
            "b": 50,
            "radius": 8000 + total * 300,
        })

    map_df = pd.DataFrame(map_rows)
    layer  = pdk.Layer(
        "ScatterplotLayer", data=map_df,
        get_position=["lon", "lat"], get_fill_color=["r", "g", "b", 180],
        get_radius="radius", pickable=True, auto_highlight=True,
    )
    view = pdk.ViewState(latitude=-2.5, longitude=118.0, zoom=4, pitch=0)
    tooltip = {
        "html": "<b>{name}</b><br/>{title}<br/>📍 {city}<br/>Score: {score} — {tier}<br/>Status: {status}",
        "style": {"backgroundColor": "#1a1a2e", "color": "white", "fontSize": "13px", "padding": "8px"},
    }
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view, tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    ))
    city_counts = map_df.groupby("city").size().reset_index(name="Leads").sort_values("Leads", ascending=False)
    st.caption("📍 " + " · ".join(f"{r['city']} ({r['Leads']})" for _, r in city_counts.iterrows()))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    st.markdown("### Analytics")
    a1, a2 = st.columns(2)

    with a1:
        st.markdown("**Fit Score Distribution**")
        buckets = {"High Fit (70+)": 0, "Medium Fit (50-69)": 0, "Low Fit (<50)": 0}
        for l in leads:
            t = l["_total"]
            if t >= 70:   buckets["High Fit (70+)"] += 1
            elif t >= 50: buckets["Medium Fit (50-69)"] += 1
            else:         buckets["Low Fit (<50)"] += 1
        st.bar_chart(pd.DataFrame(list(buckets.items()), columns=["Tier","Count"]).set_index("Tier"), color="#2D8B2D")

    with a2:
        st.markdown("**Industry Breakdown**")
        ind_counts = {}
        for l in leads:
            ind = l["_sc"]["industry_label"]
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        st.bar_chart(pd.DataFrame(list(ind_counts.items()), columns=["Industry","Count"]).sort_values("Count", ascending=False).set_index("Industry"))

    st.markdown("**Pipeline Progress**")
    pipeline_counts = {}
    for l in leads:
        s = l["_status"]
        pipeline_counts[s] = pipeline_counts.get(s, 0) + 1
    stage_order = ["Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Won", "Not Interested"]
    rows = [(s, pipeline_counts.get(s, 0)) for s in stage_order]
    st.bar_chart(pd.DataFrame(rows, columns=["Stage","Count"]).set_index("Stage"), color="#3498db")

    with st.expander("Export to Excel"):
        if st.button("Generate Excel"):
            rows = []
            for lead in leads:
                url = lead.get("linkedin_url", "")
                track = tracking.get(url, {})
                sc = lead["_sc"]
                rows.append({
                    "Name": lead.get("name",""), "Title": lead.get("title",""),
                    "Company": lead.get("company",""),
                    "City": INDONESIA_CITIES[lead_cities[url]]["label"],
                    "Fit Score": lead["_total"], "Fit Tier": score_tier(lead["_total"]),
                    "Role": sc["role_label"], "Industry": sc["industry_label"],
                    "LinkedIn URL": url,
                    "Status": lead["_status"],
                    "Date Contacted": track.get("contacted_date",""),
                    "Notes": track.get("notes",""),
                    "Tone Badges": ", ".join(detect_tone_badges(lead)),
                    "Tone Profile": lead.get("tone_profile",""),
                    "Engagement Angle": get_engagement_angle(lead, sc),
                    "Connection Message": lead.get("connection_message",""),
                    "Follow-up Message": lead.get("followup_message",""),
                    "Talking Points": "\n".join(lead.get("talking_points",[])) if isinstance(lead.get("talking_points"), list) else "",
                    "Key Interests": ", ".join(lead.get("key_interests",[])) if isinstance(lead.get("key_interests"), list) else "",
                    "Active Profile": lead["_active"],
                })
            df = pd.DataFrame(rows).sort_values("Fit Score", ascending=False)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"heyva_leads_{ts}.xlsx")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            df.to_excel(out, index=False)
            st.success(f"Exported to {out}")
