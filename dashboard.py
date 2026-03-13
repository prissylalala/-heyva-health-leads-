"""
Heyva Health Lead Tracking Dashboard
Run with: streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import pydeck as pdk

# Config
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads_data")
TRACKING_FILE = os.path.join(DATA_DIR, "tracking.json")
ANALYZED_FILE = os.path.join(DATA_DIR, "indonesia_analyzed.json")

# Page config
st.set_page_config(page_title="Heyva Health Leads", page_icon="🏥", layout="wide")

# --- Indonesia Geography ---

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
}

DEFAULT_CITY = "jakarta"


INDONESIA_LOCATION_SIGNALS = ["indonesia", "jakarta", "surabaya", "bandung", "bali", "medan", "indonesian"]

def is_indonesia_verified(lead: dict) -> bool:
    """Returns True if the lead is based in Indonesia.
    Checks LinkedIn domain first, then falls back to location signals in profile text."""
    url = lead.get("linkedin_url", "")
    if "id.linkedin.com" in url:
        return True
    # Non-ID domain: check linkedin_about, title, company only (not google_mentions to avoid false positives)
    text = " ".join([
        lead.get("linkedin_about", ""),
        lead.get("title", ""),
        lead.get("company", ""),
    ]).lower()
    return any(s in text for s in INDONESIA_LOCATION_SIGNALS)


def detect_city(lead: dict) -> str:
    """Detect Indonesian city from lead text. Defaults to Jakarta."""
    text = " ".join([
        lead.get("linkedin_url", ""),
        lead.get("linkedin_about", ""),
        lead.get("company", ""),
        " ".join(lead.get("google_mentions", [])),
    ]).lower()
    for city_key in INDONESIA_CITIES:
        if city_key in text:
            return city_key
    return DEFAULT_CITY


# --- Scoring Engine ---

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
    # (keywords to detect in industry/company/mentions, score)
    "oil_gas":        (["oil", "gas", "energy", "petroleum", "refinery", "mining", "petrochemical"], 25),
    "pharma_health":  (["pharma", "pharmaceutical", "health", "medical", "hospital", "biotech", "clinic"], 24),
    "mnc":            (["multinational", "mnc", "global", "international", "unilever", "reckitt", "danone", "nestle", "shell", "chevron", "exxon", "bp "], 22),
    "manufacturing":  (["manufacturing", "factory", "production", "industrial", "fmcg", "consumer goods", "textile", "automotive"], 20),
    "tech":           (["technology", "tech", "software", "it ", "digital", "startup", "saas", "fintech", "e-commerce", "ecommerce"], 18),
    "hospitality":    (["hospitality", "hotel", "resort", "tourism", "travel", "airline", "catering", "restaurant", "leisure"], 18),
    "real_estate":    (["real estate", "property", "developer", "construction", "infrastructure", "realty"], 15),
    "media_news":     (["media", "news", "publishing", "broadcast", "television", "radio", "journalist", "entertainment", "advertising"], 15),
    "finance":        (["finance", "financial", "banking", "bank", "investment", "insurance company", "asset management"], 18),
}

INDUSTRY_LABELS = {
    "oil_gas": "Oil & Gas",
    "pharma_health": "Pharma / Health",
    "mnc": "MNC",
    "manufacturing": "Manufacturing",
    "tech": "Tech",
    "hospitality": "Hospitality",
    "real_estate": "Real Estate",
    "media_news": "Media & News",
    "finance": "Finance",
    "other": "Other",
}


def detect_industry(lead: dict) -> tuple[str, int]:
    """Returns (industry_key, score)."""
    searchable = " ".join([
        lead.get("industry", ""),
        lead.get("company", ""),
        lead.get("title", ""),
        " ".join(lead.get("google_mentions", [])),
        lead.get("linkedin_about", ""),
    ]).lower()

    for key, (keywords, score) in INDUSTRY_SCORES.items():
        if any(kw in searchable for kw in keywords):
            return key, score
    return "other", 5


def score_role(lead: dict) -> tuple[int, str]:
    title = lead.get("title", "").lower()
    if any(k in title for k in ["hr director", "human resources director", "people director", "head of hr", "chief people"]):
        return 25, "HR Director"
    if any(k in title for k in ["hr", "human resources", "people", "talent", "hrd"]):
        return 20, "HR"
    if any(k in title for k in ["cfo", "chief financial", "finance director", "head of finance", "vp finance"]):
        return 22, "CFO/Finance"
    if any(k in title for k in ["ceo", "president", "managing director", "general manager"]):
        return 18, "C-Suite"
    return 8, "Other"


def score_health_generosity(lead: dict) -> tuple[int, list[str]]:
    """Score 0-25 based on signals the company invests in employee health/wellness."""
    searchable = " ".join([
        lead.get("linkedin_about", ""),
        lead.get("tone_profile", ""),
        lead.get("google_background", ""),
        " ".join(lead.get("google_mentions", [])),
        " ".join(lead.get("social_posts", [])),
        " ".join(lead.get("key_interests", []) if isinstance(lead.get("key_interests"), list) else []),
    ]).lower()

    matched = [kw for kw in HEALTH_GENEROSITY_KEYWORDS if kw in searchable]
    unique_signals = list(dict.fromkeys(matched))  # deduplicate preserving order

    if len(unique_signals) >= 5:
        return 25, unique_signals[:5]
    elif len(unique_signals) >= 3:
        return 18, unique_signals[:3]
    elif len(unique_signals) >= 1:
        return 10, unique_signals[:2]
    return 3, []


def score_data_quality(lead: dict) -> int:
    dq = lead.get("data_quality", "")
    if dq == "full":
        return 15
    if dq == "limited":
        return 8
    return 4  # linkedin_only or missing


def score_interest_alignment(lead: dict) -> tuple[int, list[str]]:
    interests = lead.get("key_interests", [])
    if not isinstance(interests, list):
        interests = []
    searchable = " ".join(interests).lower()
    matched = [kw for kw in HEYVA_INTEREST_KEYWORDS if kw in searchable]
    unique = list(dict.fromkeys(matched))
    score = min(10, len(unique) * 2)
    return score, unique[:5]


def compute_lead_score(lead: dict) -> dict:
    role_score, role_label = score_role(lead)
    industry_key, industry_score = detect_industry(lead)
    generosity_score, generosity_signals = score_health_generosity(lead)
    quality_score = score_data_quality(lead)
    alignment_score, aligned_interests = score_interest_alignment(lead)

    total = role_score + industry_score + generosity_score + quality_score + alignment_score

    return {
        "total": total,
        "role_score": role_score,
        "role_label": role_label,
        "industry_key": industry_key,
        "industry_label": INDUSTRY_LABELS.get(industry_key, "Other"),
        "industry_score": industry_score,
        "generosity_score": generosity_score,
        "generosity_signals": generosity_signals,
        "quality_score": quality_score,
        "alignment_score": alignment_score,
        "aligned_interests": aligned_interests,
    }


def score_color(total: int) -> str:
    if total >= 70:
        return "🟢"
    if total >= 50:
        return "🟡"
    return "🔴"


def score_tier(total: int) -> str:
    if total >= 70:
        return "High Fit"
    if total >= 50:
        return "Medium Fit"
    return "Low Fit"


# --- Tone Engine ---

TONE_KEYWORDS = {
    "Data-Driven": ["data", "metric", "kpi", "roi", "analytics", "insight", "evidence", "results", "numbers", "performance"],
    "People-Focused": ["people", "employee", "team", "culture", "wellbeing", "talent", "human", "community", "empathy"],
    "Formal": ["corporate", "strategic", "executive", "professional", "governance", "compliance", "stakeholder"],
    "Visionary": ["innovation", "future", "transform", "disrupt", "pioneer", "vision", "change", "growth"],
    "Cost-Conscious": ["cost", "saving", "efficiency", "budget", "financial", "reduce", "optimize", "roi", "profit"],
}


def detect_tone_badges(lead: dict) -> list[str]:
    searchable = " ".join([
        lead.get("tone_profile", ""),
        lead.get("linkedin_about", ""),
        " ".join(lead.get("social_posts", [])),
    ]).lower()
    badges = [badge for badge, kws in TONE_KEYWORDS.items() if sum(1 for kw in kws if kw in searchable) >= 2]
    return badges or ["Balanced"]


def get_engagement_angle(lead: dict, score: dict) -> str:
    role = score["role_label"]
    tone = detect_tone_badges(lead)
    interests = lead.get("key_interests", [])
    interest_str = ", ".join(interests[:3]) if isinstance(interests, list) else ""

    if "CFO" in role or "Finance" in role:
        if "Data-Driven" in tone or "Cost-Conscious" in tone:
            return f"Lead with financial risk data — quantify the cost of untreated lifestyle disease in their workforce. Reference ROI and insurance claim reduction numbers."
        return f"Frame Heyva Health as a cost-reduction tool — reduced insurance claims, lower absenteeism costs, measurable financial risk exposure."
    if "HR" in role:
        if "People-Focused" in tone:
            return f"Lead with employee wellbeing impact — personalized health programs, workforce morale, and retention. Connect to their known interest in: {interest_str}."
        if "Data-Driven" in tone:
            return f"Lead with workforce health analytics — biomarker-based risk insights, measurable wellness program ROI. They respond to evidence."
        return f"Emphasize Heyva Health's personalized employee health programs and how they reduce HR's burden managing health-related absenteeism."
    return f"Tailor pitch to their strategic priorities. Known interests: {interest_str}."


# --- Data Loading ---

@st.cache_data(ttl=3600)
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


# --- Main App ---

st.title("Heyva Health — Lead Tracking Dashboard")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Click 'Rerun' or refresh page to update")

leads = load_leads()
if not leads:
    st.error("No analyzed leads found. Run the pipeline first.")
    st.stop()

tracking = load_tracking()

# Pre-compute scores and cities for all leads
lead_scores = {lead.get("linkedin_url", ""): compute_lead_score(lead) for lead in leads}
lead_cities = {lead.get("linkedin_url", ""): detect_city(lead) for lead in leads}

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Fit tier filter
tier_options = ["All", "High Fit (70+)", "Medium Fit (50-69)", "Low Fit (<50)"]
selected_tier = st.sidebar.selectbox("Fit Score", tier_options)

# Status filter
status_options = ["All", "Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Not Interested"]
selected_status = st.sidebar.selectbox("Contact Status", status_options)

# Industry filter
all_industry_labels = sorted(set(lead_scores[l.get("linkedin_url", "")]["industry_label"] for l in leads))
selected_industries = st.sidebar.multiselect("Industry", all_industry_labels, default=all_industry_labels)

# Role filter
all_roles = sorted(set(lead_scores[l.get("linkedin_url", "")]["role_label"] for l in leads))
selected_roles = st.sidebar.multiselect("Role", all_roles, default=all_roles)

# City filter
all_city_labels = sorted(set(INDONESIA_CITIES[lead_cities[l.get("linkedin_url", "")]]["label"] for l in leads))
selected_cities = st.sidebar.multiselect("City / Region", all_city_labels, default=all_city_labels)


# --- Apply Filters ---
filtered_leads = []
for lead in leads:
    url = lead.get("linkedin_url", "")
    track = tracking.get(url, {})
    status = track.get("status", "Not Contacted")
    sc = lead_scores[url]
    total = sc["total"]
    tier = score_tier(total)

    if selected_tier == "High Fit (70+)" and total < 70:
        continue
    if selected_tier == "Medium Fit (50-69)" and not (50 <= total < 70):
        continue
    if selected_tier == "Low Fit (<50)" and total >= 50:
        continue
    if selected_status != "All" and status != selected_status:
        continue
    if sc["industry_label"] not in selected_industries:
        continue
    if sc["role_label"] not in selected_roles:
        continue
    city_label = INDONESIA_CITIES[lead_cities[url]]["label"]
    if city_label not in selected_cities:
        continue
    filtered_leads.append(lead)

# --- Summary Metrics ---
total_leads = len(leads)
contacted = sum(1 for l in leads if tracking.get(l.get("linkedin_url", ""), {}).get("status", "Not Contacted") != "Not Contacted")
replied = sum(1 for l in leads if tracking.get(l.get("linkedin_url", ""), {}).get("status", "") == "Contacted - Replied")
meetings = sum(1 for l in leads if tracking.get(l.get("linkedin_url", ""), {}).get("status", "") == "Meeting Scheduled")
high_fit = sum(1 for l in leads if lead_scores[l.get("linkedin_url", "")]["total"] >= 70)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Leads", total_leads)
col2.metric("High Fit (70+)", high_fit)
col3.metric("Contacted", contacted)
col4.metric("Replied", replied)
col5.metric("Meetings", meetings)

# --- Score Distribution Chart ---
st.subheader("Fit Score Distribution")
score_buckets = {"High Fit (70+)": 0, "Medium Fit (50-69)": 0, "Low Fit (<50)": 0}
for l in leads:
    t = lead_scores[l.get("linkedin_url", "")]["total"]
    if t >= 70:
        score_buckets["High Fit (70+)"] += 1
    elif t >= 50:
        score_buckets["Medium Fit (50-69)"] += 1
    else:
        score_buckets["Low Fit (<50)"] += 1
dist_df = pd.DataFrame(list(score_buckets.items()), columns=["Tier", "Count"])
st.bar_chart(dist_df.set_index("Tier"), color="#2D8B2D")

# --- Industry Breakdown ---
with st.expander("Industry Breakdown", expanded=False):
    industry_counts = {}
    for l in leads:
        ind = lead_scores[l.get("linkedin_url", "")]["industry_label"]
        industry_counts[ind] = industry_counts.get(ind, 0) + 1
    ind_df = pd.DataFrame(list(industry_counts.items()), columns=["Industry", "Count"]).sort_values("Count", ascending=False)
    st.bar_chart(ind_df.set_index("Industry"))

# --- Indonesia Map ---
st.subheader("Lead Map — Indonesia")

map_rows = []
for lead in leads:
    url = lead.get("linkedin_url", "")
    sc = lead_scores[url]
    city_key = lead_cities[url]
    city_info = INDONESIA_CITIES[city_key]
    total = sc["total"]
    # Spread pins slightly so they don't stack on same city
    import random
    random.seed(url)  # deterministic jitter per lead
    map_rows.append({
        "lat": city_info["lat"] + random.uniform(-0.08, 0.08),
        "lon": city_info["lon"] + random.uniform(-0.08, 0.08),
        "name": lead.get("name", "Unknown"),
        "title": lead.get("title", ""),
        "city": city_info["label"],
        "score": total,
        "tier": score_tier(total),
        # Color: green=high, yellow=medium, red=low
        "r": 50 if total >= 70 else (255 if total >= 50 else 220),
        "g": 180 if total >= 70 else (200 if total >= 50 else 50),
        "b": 50,
        "radius": 8000 + total * 300,
    })

map_df = pd.DataFrame(map_rows)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position=["lon", "lat"],
    get_fill_color=["r", "g", "b", 180],
    get_radius="radius",
    pickable=True,
    auto_highlight=True,
)

view = pdk.ViewState(
    latitude=-2.5,
    longitude=118.0,
    zoom=4,
    pitch=0,
)

tooltip = {
    "html": "<b>{name}</b><br/>{title}<br/>📍 {city}<br/>Score: {score} — {tier}",
    "style": {"backgroundColor": "#1a1a2e", "color": "white", "fontSize": "13px", "padding": "8px"},
}

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip=tooltip,
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
))

city_counts = map_df.groupby("city").size().reset_index(name="Leads").sort_values("Leads", ascending=False)
st.caption("📍 " + " · ".join(f"{r['city']} ({r['Leads']})" for _, r in city_counts.iterrows()) + "  *(undetected city defaults to Jakarta)*")

# --- Leads Table ---
st.subheader(f"Leads ({len(filtered_leads)} showing)")

sorted_leads = sorted(filtered_leads, key=lambda x: lead_scores[x.get("linkedin_url", "")]["total"], reverse=True)

for i, lead in enumerate(sorted_leads):
    url = lead.get("linkedin_url", "")
    track = tracking.get(url, {})
    status = track.get("status", "Not Contacted")
    sc = lead_scores[url]
    total = sc["total"]
    emoji = score_color(total)
    tier = score_tier(total)

    status_icons = {
        "Not Contacted": "⬜",
        "Contacted - No Reply": "📤",
        "Contacted - Replied": "📩",
        "Meeting Scheduled": "📅",
        "Not Interested": "❌",
    }
    status_icon = status_icons.get(status, "⬜")

    tone_badges = detect_tone_badges(lead)
    engagement_angle = get_engagement_angle(lead, sc)

    with st.expander(
        f"{emoji} {total}/75 | {tier} | {status_icon} 🇮🇩 {lead.get('name', 'Unknown')} — {lead.get('title', '')[:50]}"
    ):
        col_left, col_right = st.columns([2, 1])

        with col_left:
            # --- Score Breakdown ---
            st.markdown("#### Fit Score Breakdown")
            score_cols = st.columns(5)
            score_cols[0].metric("Role Fit", f"{sc['role_score']}/25", help=sc['role_label'])
            score_cols[1].metric("Industry Fit", f"{sc['industry_score']}/25", help=sc['industry_label'])
            score_cols[2].metric("Health Generosity", f"{sc['generosity_score']}/25")
            score_cols[3].metric("Data Quality", f"{sc['quality_score']}/15")
            score_cols[4].metric("Interest Match", f"{sc['alignment_score']}/10")

            if sc["generosity_signals"]:
                st.caption(f"Health/benefits signals detected: {', '.join(sc['generosity_signals'])}")

            st.markdown("---")

            # --- Lead Info ---
            city_label = INDONESIA_CITIES[lead_cities[url]]["label"]
            st.markdown(f"**Company:** {lead.get('company', 'N/A')}")
            st.markdown(f"**Location:** {city_label}, Indonesia")
            st.markdown(f"**Industry:** {sc['industry_label']} — {lead.get('industry', 'N/A')}")
            st.markdown(f"**LinkedIn:** [{url}]({url})")
            st.markdown(f"**Priority Reason:** {lead.get('priority_reason', 'N/A')}")
            if lead.get("google_background"):
                st.markdown(f"**Google Background:** {lead.get('google_background', '')}")

            st.markdown("---")

            # --- Tone & Engagement Guide ---
            st.markdown("#### Engagement Guide")

            # Tone badges
            badge_str = " &nbsp; ".join([f"`{b}`" for b in tone_badges])
            st.markdown(f"**Communication Style:** {badge_str}", unsafe_allow_html=True)

            st.markdown(f"**Tone Profile:** {lead.get('tone_profile', 'N/A')}")

            if sc["aligned_interests"]:
                st.markdown(f"**Heyva-Aligned Interests:** {', '.join(sc['aligned_interests'])}")

            if lead.get("key_interests"):
                interests = lead.get("key_interests", [])
                if isinstance(interests, list):
                    st.markdown(f"**All Key Interests:** {', '.join(interests)}")

            st.info(f"**How to open the conversation:** {engagement_angle}")

            st.markdown("---")

            # --- Outreach Messages ---
            st.markdown("**Suggested Connection Message:**")
            st.code(lead.get("connection_message", "N/A"), language=None)

            st.markdown("**Suggested Follow-up Message:**")
            st.text_area("", lead.get("followup_message", "N/A"), height=100, key=f"followup_{i}", disabled=True)

            if lead.get("talking_points"):
                st.markdown("**Talking Points:**")
                points = lead.get("talking_points", [])
                if isinstance(points, list):
                    for tp in points:
                        st.markdown(f"- {tp}")

        with col_right:
            st.markdown("### Update Status")

            new_status = st.selectbox(
                "Status",
                ["Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Not Interested"],
                index=["Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Not Interested"].index(status),
                key=f"status_{i}"
            )

            notes_val = track.get("notes", "")
            new_notes = st.text_area("Notes", notes_val, height=100, key=f"notes_{i}")

            contact_date = track.get("contacted_date", "")
            new_date = st.date_input(
                "Date Contacted",
                value=datetime.strptime(contact_date, "%Y-%m-%d").date() if contact_date else None,
                key=f"date_{i}",
            )

            if st.button("Save", key=f"save_{i}"):
                tracking[url] = {
                    "status": new_status,
                    "notes": new_notes,
                    "contacted_date": new_date.isoformat() if new_date else "",
                    "updated_at": datetime.now().isoformat(),
                }
                save_tracking(tracking)
                st.success("Saved!")
                st.rerun()

# --- Export ---
st.sidebar.markdown("---")
st.sidebar.header("Export")
if st.sidebar.button("Export to Excel"):
    rows = []
    for lead in leads:
        url = lead.get("linkedin_url", "")
        track = tracking.get(url, {})
        sc = lead_scores[url]
        rows.append({
            "City": INDONESIA_CITIES[lead_cities[url]]["label"],
            "Country": "Indonesia",
            "Fit Score": sc["total"],
            "Fit Tier": score_tier(sc["total"]),
            "Name": lead.get("name", ""),
            "Title": lead.get("title", ""),
            "Role Label": sc["role_label"],
            "Company": lead.get("company", ""),
            "Industry": sc["industry_label"],
            "LinkedIn URL": url,
            "Status": track.get("status", "Not Contacted"),
            "Date Contacted": track.get("contacted_date", ""),
            "Tone Badges": ", ".join(detect_tone_badges(lead)),
            "Tone Profile": lead.get("tone_profile", ""),
            "Engagement Angle": get_engagement_angle(lead, sc),
            "Connection Message": lead.get("connection_message", ""),
            "Follow-up Message": lead.get("followup_message", ""),
            "Key Interests": ", ".join(lead.get("key_interests", [])) if isinstance(lead.get("key_interests"), list) else "",
            "Talking Points": "\n".join(lead.get("talking_points", [])) if isinstance(lead.get("talking_points"), list) else "",
            "Google Background": lead.get("google_background", ""),
            "Health Generosity Signals": ", ".join(sc["generosity_signals"]),
            "Role Score": sc["role_score"],
            "Industry Score": sc["industry_score"],
            "Health Generosity Score": sc["generosity_score"],
            "Data Quality Score": sc["quality_score"],
            "Interest Alignment Score": sc["alignment_score"],
            "Notes": track.get("notes", ""),
        })
    df = pd.DataFrame(rows).sort_values("Fit Score", ascending=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"heyva_indonesia_leads_{timestamp}.xlsx")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_excel(output_path, index=False)
    st.sidebar.success(f"Exported to {output_path}")
