# ======================================================
# Runbook Generation Service (Final Clean Version)
# ======================================================

import json
from jinja2 import Template

from .ai_client import call_llm
from .phi_scrub import scrub_text

from ..extensions import db
from ..models import Ticket, Runbook


# ======================================================
# TOPIC CLASSIFICATION (AI)
# ======================================================

def classify_ticket_topic(ticket: Ticket) -> str:
    """Assign a topic label to a ticket using local LLM."""
    text = scrub_text(f"{ticket.short_description}\n\n{ticket.description or ''}")

    prompt = f"""
Classify the topic of this ticket into ONE short label, lowercase:

Examples:
vpn_failure, phishing, malware, email_issue, endpoint_issue,
identity_issue, network_issue, access_issue, cloud_issue

Incident text:
{text}

Return ONLY the label.
"""

    raw = call_llm(prompt).strip().lower()
    return raw.split()[0] if raw else "uncategorized"



# ======================================================
# BULK TOPIC ASSIGNMENT
# ======================================================

def assign_topics_to_tickets(tickets):
    for t in tickets:
        t.topic = classify_ticket_topic(t)
    db.session.commit()



# ======================================================
# RUNBOOK GENERATION — MAIN PIPELINE
# ======================================================

def generate_runbook_for_topic(topic: str) -> Runbook:
    """Create/update a runbook for a given topic."""
    tickets = Ticket.query.filter_by(topic=topic).order_by(Ticket.opened_at).all()

    payload = {
        "topic": topic,
        "tickets": [
            {
                "number": t.number,
                "short_description": scrub_text(t.short_description),
                "description": scrub_text(t.description or ""),
                "opened_at": str(t.opened_at)
            }
            for t in tickets
        ]
    }

    # ================================
    # Strong JSON-controlled prompt
    # ================================
    prompt = f"""
You are generating a runbook for Tier 1/Tier 2 IT support.

INPUT TICKETS:
{json.dumps(payload, indent=2)}

Your output must be ONLY valid JSON with EXACTLY:

{{
  "title": "",
  "summary": "",
  "steps": [],
  "references": []
}}

Rules:
- "summary" = 2–4 sentences explaining the problem.
- "steps" = 5–12 actionable bullet steps (imperative action).
- "references" = tools, consoles, or docs (short phrases only).
- NO MARKDOWN
- NO CODE BLOCKS
- NO SCHEMAS
- NO EXTRA KEYS

Return JSON and NOTHING else.
"""

    raw = call_llm(prompt)

    # ================================
    # Attempt strict JSON parse
    # ================================
    try:
        data = json.loads(raw)
    except Exception:
        # Fallback — salvage something usable
        data = {
            "title": f"Runbook for {topic}",
            "summary": raw[:2000],  # store raw but truncated
            "steps": ["Review raw LLM output — failed structured parse."],
            "references": []
        }

    # Ensure minimal keys exist
    data.setdefault("summary", "")
    data.setdefault("steps", [])
    data.setdefault("references", [])

    # Remove code fences if model leaked them
    data["summary"] = (
        data["summary"]
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    # ================================
    # Build Markdown Output
    # ================================
    md_template = Template("""
# {{ runbook.title }}

## Summary
{{ runbook.summary }}

## Steps
{% if runbook.steps %}
{% for step in runbook.steps %}
- {{ step }}
{% endfor %}
{% else %}
_No steps returned — model output weak or malformed._
{% endif %}

{% if runbook.references %}
## References
{% for ref in runbook.references %}
- {{ ref }}
{% endfor %}
{% endif %}
""")

    markdown = md_template.render(runbook=data)

    # ================================
    # DB WRITE / UPDATE
    # ================================
    rb = Runbook.query.filter_by(topic=topic).first()
    if not rb:
        rb = Runbook(topic=topic, title=data.get("title", f"Runbook for {topic}"))
        db.session.add(rb)

    rb.title = data.get("title", f"Runbook for {topic}")
    rb.markdown = markdown
    rb.tickets_used = len(tickets)

    db.session.commit()
    return rb
