# app/services/runbook_gen.py
import json
from textwrap import shorten

from jinja2 import Template

from .ai_client import call_llm
from .phi_scrub import scrub_text
from .classifier import classify_ticket

from ..extensions import db
from ..models import Ticket, Runbook

# -------------------------------------------------------------------
# Config for summarisation / batching
# -------------------------------------------------------------------

MAX_TICKETS_FOR_SUMMARY = 400     # cap tickets per topic used for summary
SUMMARY_BATCH_SIZE = 80           # tickets per LLM batch (5 batches max)
MAX_FIELD_CHARS = 300             # truncate long descriptions for prompt


ENV_CONTEXT = """
You are helping an enterprise IT / Security team at a large US healthcare provider.

Environment facts (always assume these):
- Email: Microsoft 365 / Exchange Online with Proofpoint (TAP/TRAP, URL Defense, DLP).
- Endpoint: CrowdStrike Falcon (EDR / ITP).
- Network / VPN: firewall-backed VPN (e.g., Palo Alto / GlobalProtect or similar).
- Monitoring: Rapid7 InsightIDR (SIEM) and InsightVM (vulnerability management).
- Tickets are often poorly documented; you must infer sane, opinionated best-practice steps.

When generating runbooks, include concrete checks in these tools when relevant:
- For email issues: Proofpoint portal, quarantine, URL / attachment rewrites, user-reported phishing, O365 message trace.
- For access issues: IAM / Entra ID, group membership, conditional access, MFA status, device compliance.
- For endpoint issues: CrowdStrike console (detections, host info, sensor status, network containment).
- For network issues: firewall / VPN portal, logs, and basic connectivity triage.
"""


# -------------------------------------------------------------------
# Topic assignment (uses classifier.py, mostly heuristic)
# -------------------------------------------------------------------

def assign_topics_to_tickets(tickets):
    """
    Assign taxonomy-based topics to a list of Ticket objects.

    Uses hybrid classifier (heuristics + LLM fallback) from services.classifier.
    """
    for t in tickets:
        t.topic = classify_ticket(t)

    db.session.commit()


# -------------------------------------------------------------------
# Ticket summarisation helpers
# -------------------------------------------------------------------

def _ticket_brief(t: Ticket) -> dict:
    """Minimal, scrubbed view of a ticket for prompts."""
    return {
        "number": t.number or "",
        "short_description": shorten(scrub_text(t.short_description or ""), MAX_FIELD_CHARS),
        "description": shorten(scrub_text(t.description or ""), MAX_FIELD_CHARS),
        "category": (t.category or "").lower(),
        "subcategory": (t.subcategory or "").lower(),
        "assignment_group": (t.assignment_group or "").lower(),
        "ci": (t.ci or "").lower(),
    }


def summarize_tickets_for_topic(topic: str, tickets: list[Ticket]) -> str:
    """
    Summarise a large set of tickets into a compact description of patterns.

    Strategy:
    - Take up to MAX_TICKETS_FOR_SUMMARY most recent tickets.
    - Chunk into SUMMARY_BATCH_SIZE.
    - For each chunk, get a short pattern summary from the LLM.
    - Merge chunk summaries with a final LLM call.
    """
    if not tickets:
        return f"No historical tickets exist for topic '{topic}'."

    # Use the most recent tickets; they best represent current environment
    sample = tickets[-MAX_TICKETS_FOR_SUMMARY:]

    batch_summaries: list[str] = []

    for i in range(0, len(sample), SUMMARY_BATCH_SIZE):
        batch = sample[i : i + SUMMARY_BATCH_SIZE]
        brief_batch = [_ticket_brief(t) for t in batch]

        prompt = f"""
{ENV_CONTEXT}

You are analysing incident tickets for topic: '{topic}'.

Here is a JSON array of example tickets (fields are already scrubbed of PHI):
{json.dumps(brief_batch, indent=2)}

From ONLY these tickets, produce a short analysis of patterns.

REQUIREMENTS:
- Return plain text, no JSON.
- 5–10 bullet-style lines (but you may format as plain text).
- Focus on:
  - common symptoms users report,
  - frequent root causes / misconfigurations,
  - tools that are *actually* touched (email gateway, endpoint, SIEM, VPN, IAM, etc.),
  - typical fixes or workarounds,
  - escalation paths (who / which group gets involved).

Keep it under ~300 words.
"""
        raw = call_llm(prompt)
        batch_summaries.append(scrub_text(raw).strip())

    if len(batch_summaries) == 1:
        return batch_summaries[0]

    # Merge multiple batch summaries
    merge_prompt = f"""
{ENV_CONTEXT}

You are consolidating multiple partial analyses for topic '{topic}'.

Here are several short summaries, each describing patterns in a subset of tickets:

--------
{chr(10*2).join(batch_summaries)}
--------

TASK:
- Produce ONE cohesive summary (250–400 words).
- Merge overlapping ideas.
- Emphasise: typical triggers, common root causes, standard tools / consoles used, and escalation paths.

Return plain text, no JSON.
"""
    merged = call_llm(merge_prompt)
    return scrub_text(merged).strip()


# -------------------------------------------------------------------
# Runbook generation
# -------------------------------------------------------------------

def generate_runbook_for_topic(topic: str) -> Runbook:
    """
    Create/update the runbook for a given topic.

    Pipeline:
    1. Load tickets for that topic.
    2. Summarise patterns across tickets (summarize_tickets_for_topic).
    3. Ask LLM to turn that summary into a structured JSON runbook.
    4. Render JSON into markdown and persist to DB.
    """
    tickets = (
        Ticket.query
        .filter_by(topic=topic)
        .order_by(Ticket.opened_at)
        .all()
    )

    # Step 1: summarise ticket history
    summary_text = summarize_tickets_for_topic(topic, tickets)

    # Step 2: build runbook via JSON-only LLM call
    runbook_prompt = f"""
{ENV_CONTEXT}

You are an experienced Tier 2 / Tier 3 engineer writing a practical runbook.

TOPIC: "{topic}"

TICKET HISTORY SUMMARY (from real incident tickets):
\"\"\"
{summary_text}
\"\"\"

TASK:
Generate a JSON object describing the operational runbook for this topic.

STRICT REQUIREMENTS:
- Return ONLY valid JSON. No markdown, no backticks, no comments.
- Top-level keys: "title", "summary", "steps", "references".
- "title": short string (<= 80 chars) that an engineer would recognise in a dashboard.
- "summary": 2–4 sentences describing the scenario and overall approach.
- "steps": ordered list of clear, imperative strings.
  - Think like a senior who knows Proofpoint, CrowdStrike, Rapid7, O365, VPN, Entra ID.
  - Include concrete checks and commands where appropriate, not generic fluff.
- "references": list of short strings naming KBs, tools, or consoles to open.

Example of the expected SHAPE (not the content):

{{
  "title": "Email issue: suspected phishing or missing message",
  "summary": "Short paragraph describing when this runbook applies...",
  "steps": [
    "Confirm the user's identity and contact details; verify the reported symptoms.",
    "In Proofpoint TAP/TRAP, search for the sender, subject, and URLs; check if the message was quarantined or rewritten.",
    "Run an O365 message trace for the affected time window and recipient.",
    "In CrowdStrike, locate the endpoint and review recent detections or suspicious processes.",
    "If compromise is suspected, isolate the host and follow the incident-response playbook."
  ],
  "references": [
    "Tool: Proofpoint TAP/TRAP console",
    "Tool: Microsoft 365 Message Trace",
    "Tool: CrowdStrike host search / Detections",
    "SOP: Corporate phishing-response playbook"
  ]
}}

Now generate the JSON for topic "{topic}" based on the ticket summary above.
"""

    raw = call_llm(runbook_prompt)
    print("RAW LLM OUTPUT (runbook_gen):", raw)

    # Step 3: JSON parsing with defensive fallback
    data = _safe_parse_runbook_json(raw, topic)

    # Normalise missing keys
    title = data.get("title") or f"Runbook for {topic}"
    summary = data.get("summary") or ""
    steps = data.get("steps") or []
    refs = data.get("references") or data.get("refs") or []

    # Render into markdown
    md_template = Template(
        """
# {{ title }}

## Summary
{{ summary }}

## Steps
{% if steps %}
{% for step in steps %}
- {{ step }}
{% endfor %}
{% else %}
_(No steps were generated for this topic yet.)_
{% endif %}

## References
{% if refs %}
{% for ref in refs %}
- {{ ref }}
{% endfor %}
{% else %}
_(No references recorded yet.)_
{% endif %}
"""
    )

    markdown = md_template.render(
        title=title,
        summary=summary,
        steps=steps,
        refs=refs,
    )

    # Step 4: upsert Runbook row
    rb = Runbook.query.filter_by(topic=topic).first()
    if not rb:
        rb = Runbook(topic=topic, title=title)
        db.session.add(rb)

    rb.title = title
    rb.markdown = markdown
    rb.tickets_used = len(tickets)

    db.session.commit()
    return rb


def _safe_parse_runbook_json(raw: str, topic: str) -> dict:
    """
    Best-effort JSON extraction for the runbook response.
    If parsing fails, fall back to a minimal structure.
    """
    text = raw.strip()

    # First attempt: direct parse
    try:
        return json.loads(text)
    except Exception as e:
        print("Direct JSON parse failed:", e)

    # Second attempt: try to extract the first {...} block
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        candidate = text[start:end]
        return json.loads(candidate)
    except Exception as e:
        print("Bracket-slice JSON parse failed:", e)

    # Final fallback
    return {
        "title": f"Runbook for {topic}",
        "summary": scrub_text(text),
        "steps": [],
        "references": [],
    }
