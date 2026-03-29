#!/usr/bin/env python3
"""
Run Claude tone analysis on leads missing tone_profile.
Generates: tone_profile, connection_message, followup_message,
           key_interests, talking_points, google_background, country.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 run_tone_analysis.py
"""
import json
import os
import time
import anthropic

ANALYZED_FILE = os.path.join(os.path.dirname(__file__), "leads_data", "indonesia_analyzed.json")
CURRENT_YEAR = 2026

def build_prompt(lead: dict) -> str:
    return f"""You are a B2B sales strategist for Heyva Health — an Indonesia-based digital health company that helps HR Directors and CFOs reduce employee health costs using biomarker analytics and personalized wellness programs.

Analyze this lead and generate highly personalised, current (year {CURRENT_YEAR}) outreach materials.

LEAD DATA:
- Name: {lead.get('name', 'Unknown')}
- Title: {lead.get('title', '')}
- Company: {lead.get('company', '')}
- Industry: {lead.get('industry', '')}
- LinkedIn About: {lead.get('linkedin_about', '')}
- LinkedIn URL: {lead.get('linkedin_url', '')}

INSTRUCTIONS:
1. Only reference activities, roles, or achievements that are current or still ongoing. Do NOT reference things from before 2023 unless they are clearly still relevant today.
2. If no specific data is available, write generic but warm Indonesia-context messages.
3. Keep connection message under 300 characters (LinkedIn limit).
4. Make follow-up message feel like a real person wrote it — not a template.

Return ONLY a valid JSON object with these exact keys:
{{
  "tone_profile": "2-3 sentence description of their communication style and what they care about",
  "connection_message": "Short LinkedIn connection request under 300 chars. Mention their role/company specifically.",
  "followup_message": "A 3-4 sentence follow-up message after connecting. Reference Heyva Health value prop relevant to their role. Ask for a 15-min call.",
  "key_interests": ["interest1", "interest2", "interest3"],
  "talking_points": ["specific talking point 1", "specific talking point 2", "specific talking point 3"],
  "google_background": "1-2 sentence summary of what we know about them and their company's health/benefits stance",
  "country": "Indonesia"
}}"""


def analyze_lead(client: anthropic.Anthropic, lead: dict) -> dict:
    prompt = build_prompt(lead)
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ Set ANTHROPIC_API_KEY first:\n   export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    client = anthropic.Anthropic(api_key=api_key)

    with open(ANALYZED_FILE, "r", encoding="utf-8") as f:
        leads = json.load(f)

    needs_analysis = [l for l in leads if not l.get("tone_profile")]
    has_analysis = [l for l in leads if l.get("tone_profile")]

    print(f"✓ Loaded {len(leads)} leads")
    print(f"  {len(has_analysis)} already have tone analysis")
    print(f"  {len(needs_analysis)} need analysis\n")

    if not needs_analysis:
        print("All leads already analyzed!")
        return

    # Build lookup dict for fast merge
    lead_index = {l.get("linkedin_url", ""): i for i, l in enumerate(leads)}

    success = 0
    failed = 0

    for i, lead in enumerate(needs_analysis, 1):
        name = lead.get("name", "Unknown")
        url = lead.get("linkedin_url", "")
        print(f"[{i}/{len(needs_analysis)}] Analyzing {name}...", end=" ", flush=True)

        try:
            result = analyze_lead(client, lead)
            # Merge result back into the lead
            idx = lead_index[url]
            leads[idx].update(result)
            leads[idx]["country"] = "Indonesia"
            print(f"✓")
            success += 1

            # Save after every 5 leads to preserve progress
            if success % 5 == 0:
                with open(ANALYZED_FILE, "w", encoding="utf-8") as f:
                    json.dump(leads, f, indent=2, ensure_ascii=False)
                print(f"  → Saved progress ({success} done so far)")

            # Rate limit: 1 request/sec to be safe
            time.sleep(1.2)

        except json.JSONDecodeError as e:
            print(f"✗ JSON parse error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1
            time.sleep(3)  # Back off on error

    # Final save
    with open(ANALYZED_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Done! {success} analyzed, {failed} failed")
    print(f"Saved to {ANALYZED_FILE}")


if __name__ == "__main__":
    main()
