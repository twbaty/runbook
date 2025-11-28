# app/services/runbook_gen.py
import json
from jinja2 import Template

from .ai_client import call_llm
from .phi_scrub import scrub_text

from ..extensions import db
from ..models import Ticket, Runbook


# ======================================================
# CLASSIFY TOPICS (AI)
# ======================================================

def classify_ticket_topic(ticket: Ticket) -> str:
    """Assign a topic label to a ticket using local LLM."""
    text = scrub_text(f"{ticket.short_description}\n\n{ticket.description or ''}")

    prompt = f"""
Classify the topic of this ticket into ONE short label, lowercase:

Valid examples:
- vpn_failure
- phishing
- malware
- email_issue
- endpoint_issue
- ransomware
- identity_issue
- network_issue
- access_issue
- cloud_issue

Incident text:
{text}

Return ONLY the label. No extra words.
"""

    raw = call_llm(prompt)
    label = raw.split()[0].lower().strip()
    return label or "uncategorized"



# ======================================================
# BULK ASSIGN TOPICS
# ======================================================

def assign_topics_to_tickets(tickets):
    """Assign AI-derived topics to a list of Ticket objects."""
    for t in tickets:
        t.topic = classify_ticket_topic(t)
    db.session.commit()



# ======================================================
# GENERATE RUNBOOK
# ======================================================

def generate_runbook_for_topic(topic: str) -> Runbook:
    """Create/update the runbook for a given topic."""

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

        prompt = f"""
You are generating a runbook for Tier 1/Tier 2 IT analysts.

INPUT (tickets):
{json.dumps(payload, indent=2)}

REQUIREMENTS:
- Return ONLY valid JSON.
- Do NOT include markdown, schemas, metadata, or explanation.
- JSON must have EXACTLY these keys:
  "title", "summary", "steps", "references"
- "title": short and human-readable.
- "summary": 2–4 sentences explaining the problem in plain language based on ticket patterns.
- "steps": 5–12 operational steps that reflect common remediation actions found in the tickets.
    * Steps MUST be imperative commands (e.g., "Check X", "Verify Y").
    * Steps MUST be practical, actionable, and specific.
- "references": list of related tools, consoles, dashboards, or documentation links
    * Keep them short, e.g. "O365 Admin Center → Message Trace"

ABSOLUTELY DO NOT:
- produce schemas
- wrap anything in markdown
- nest keys
- embed the entire JSON inside one field

Return ONLY the JSON object.
"""


    raw = call_llm(prompt)

    # Try JSON
    try:
        data = json.loads(raw)
    except Exception:
        data = {
            "title": f"Runbook for {topic}",
            "summary": raw,
            "steps": [],
            "references": []
        }

    # Markdown renderer
    md_template = Template("""
# {{ runbook.title }}

## Summary
{{ runbook.summary }}

## Steps
{% for step in runbook.steps %}
- {{ step }}
{% endfor %}

## References
{% for ref in runbook.references %}
- {{ ref }}
{% endfor %}
""")

    markdown = md_template.render(runbook=data)

    # Save or update database record
    rb = Runbook.query.filter_by(topic=topic).first()
    if not rb:
        rb = Runbook(topic=topic, title=data.get("title", f"Runbook for {topic}"))
        db.session.add(rb)

    rb.title = data.get("title", f"Runbook for {topic}")
    rb.markdown = markdown      # <-- FIXED. This is the correct variable.
    rb.json_blob = json.dumps(data)
    rb.tickets_used = len(tickets)

    db.session.commit()
    return rb
