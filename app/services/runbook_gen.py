# app/services/runbook_gen.py

import json
from jinja2 import Template

from .ai_client import call_llm
from .phi_scrub import scrub_text

from ..extensions import db
from ..models import Ticket, Runbook


# ======================================================
# STRICT TOPIC CLASSIFIER
# ======================================================

CATEGORIES = [
    "email_issue",
    "vpn_failure",
    "malware",
    "phishing",
    "endpoint_issue",
    "identity_issue",
    "network_issue",
    "access_issue",
    "cloud_issue",
    "ransomware",
    "security_issue",
    "other",
]


def classify_ticket_topic(ticket: Ticket) -> str:
    """Assign a topic using a strict fixed taxonomy."""
    text = scrub_text(f"{ticket.short_description}\n\n{ticket.description or ''}")

    prompt = f"""
You are a classifier. Choose exactly ONE category from the list below.

Valid categories:
{", ".join(CATEGORIES)}

Ticket text:
{text}

Rules:
- Return ONLY the category name.
- If unsure, return "other".
- Do NOT create new categories.
- Do NOT return variations.
"""

    raw = call_llm(prompt).strip().lower().split()[0]

    return raw if raw in CATEGORIES else "other"


# ======================================================
# BULK TOPIC ASSIGNMENT
# ======================================================

def assign_topics_to_tickets(tickets):
    """Assign AI-derived topics to a list of Ticket objects."""
    for t in tickets:
        t.topic = classify_ticket_topic(t)
    db.session.commit()


# ======================================================
# RUNBOOK GENERATION
# ======================================================

def generate_runbook_for_topic(topic: str) -> Runbook:
    """Create or update a runbook for a given topic."""

    tickets = (
        Ticket.query.filter_by(topic=topic)
        .order_by(Ticket.opened_at)
        .all()
    )

    payload = {
        "topic": topic,
        "tickets": [
            {
                "number": t.number,
                "short_description": scrub_text(t.short_description),
                "description": scrub_text(t.description or ""),
                "opened_at": str(t.opened_at),
            }
            for t in tickets
        ],
    }

    prompt = f"""
Write a JSON runbook for the following topic.

INPUT:
{json.dumps(payload, indent=2)}

REQUIREMENTS:
- Return ONLY valid JSON
- Required keys: "title", "summary", "steps", "references"
- "steps" must be a list of strings
"""

    raw = call_llm(prompt)

    # Try to parse JSON output from LLM
    try:
        data = json.loads(raw)
    except Exception:
        data = {
            "title": f"Runbook for {topic}",
            "summary": raw,
            "steps": [],
            "references": [],
        }

    # Markdown template
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

    # Write/update runbook database entry
    rb = Runbook.query.filter_by(topic=topic).first()
    if not rb:
        rb = Runbook(topic=topic)
        db.session.add(rb)

    rb.title = data.get("title", f"Runbook for {topic}")
    rb.markdown = markdown
    rb.json_blob = json.dumps(data, indent=2)
    rb.tickets_used = len(tickets)

    db.session.commit()
    return rb
