# Lead Analysis Instructions

Read `leads_data/indonesia_analyzed.json`. Find any leads that are **missing** `tone_profile` (i.e. new leads not yet analyzed). Analyze only those new leads, then **append** them to the existing array and write the full updated array back to `leads_data/indonesia_analyzed.json`. Do not re-analyze or overwrite leads that already have `tone_profile`.

## Product Context

You are generating outreach for **Heyva Health**, a platform that:
- Analyzes companies' financial risk exposure to lifestyle diseases among their workforce
- Ingests employee medical checkup data (biomarkers) to assess health risks
- Creates personalized health programs for each employee
- Value prop: reduces healthcare costs and insurance claims through data-driven, personalized interventions

## For Each Lead

### 1. Tone Analysis
Look at their LinkedIn posts, social media posts, and Google mentions. Determine:
- **Communication style:** Formal or casual? Data-driven or narrative? Corporate or personal?
- **Vocabulary level:** Technical jargon user? Simple and direct? Buzzword heavy?
- **Key phrases they use:** What words/phrases appear repeatedly in their posts?
- **Topics they care about:** What do they post about? Employee wellness? Company culture? Industry trends?
- **Emotional triggers:** What gets them engaged? Innovation? Cost savings? Employee satisfaction?

### 2. Outreach Messages
Generate messages that **mirror their communication style**. If they're formal, be formal. If they use data, lead with data. If they care about people, lead with employee impact.

**Connection Message** (max 300 chars for LinkedIn):
- Reference something specific from their posts or profile
- Connect it to Heyva Health's value
- Match their tone exactly

**Follow-up Message** (after connection accepted):
- Build on the connection message
- Introduce Heyva Health naturally
- Propose a specific next step (15-min call, demo, etc.)
- Keep it under 500 words

**Talking Points** (for first meeting):
- 3-5 bullet points tailored to their role and interests
- For HR Directors: focus on employee health outcomes, wellness program ROI, retention
- For CFOs: focus on financial risk reduction, insurance cost optimization, data-driven decisions

### 3. Output Format

For each lead, add these fields to their existing data:

```json
{
  "tone_profile": "Detailed description of their communication style...",
  "connection_message": "The personalized LinkedIn connection request...",
  "followup_message": "The follow-up message after connection...",
  "key_interests": ["interest1", "interest2", "interest3"],
  "talking_points": ["point1", "point2", "point3"],
  "notes": "Any additional observations or flags"
}
```

Write the complete array (original fields + new analysis fields) to `leads_data/analyzed_leads.json`.
