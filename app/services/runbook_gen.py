# app/services/runbook_gen.py
import json
from jinja2 import Template

from .ai_client import call_llm
from .phi_scrub import scrub_text
from .classifier import classify_ticket   # <-- NEW

from ..extensions import db
from ..models import Ticket, Runbook


# ======================================================
# BULK ASSIGN TOPICS
# ======================================================

def assign_topics_to_tickets(tickets):
    """
    Assign taxonomy-based topics to a list of Ticket objects.

    Uses hybrid classifier (heuristics + LLM fallback) from services.classifier.
    """
    for t in tickets:
        t.topic = classify_ticket(t)

    db.session.commit()


# ======================================================
# GENERATE RUNBOOK
# ======================================================

def generate_runbook_for_topic(topic: str) -> Runbook:
    """Create/update the runbook for a given topic."""
    tickets = (
        Ticket.query
        .filter_by(topic=topic)
        .order_by(Ticket.opened_at)
        .all()
    )

    payload = {
        "topic": topic,
        "tickets": [
            {
                "number": t.number,
                "short_description": scrub_text(t.short_description or ""),
                "description": scrub_text(t.description or ""),
                "opened_at": str(t.opened_at),
            }
            for t in tickets
        ],
    }

    prompt = f"""
You are writing an operational runbook for IT/SOC engineers.

INPUT (JSON):
{json.dumps(payload, indent=2)}

REQUIREMENTS:
- Return ONLY valid JSON.
- Top-level keys: "title", "summary", "steps", "references".
- "title": short string (<= 80 chars).
- "summary": 2–4 sentences describing the scenario and overall approach.
- "steps": ordered list of clear, imperative strings ("Do X", "Check Y").
- "references": list of short strings (playbooks, docs, URLs, tools).

Example (structure only):

{{
  "title": "Email issue: VPN-related MFA failures",
  "summary": "Short paragraph...",
  "steps": [
    "Step 1 ...",
    "Step 2 ..."
  ],
  "references": [
    "Some SOP or KB article",
    "Tool: CrowdStrike console",
    "Tool: Rapid7 IVM"
  ]
}}
"""

    raw = call_llm(prompt)

    print("RAW LLM OUTPUT (runbook_gen):", raw)

    # Attempt to parse JSON from the model
    try:
        data = json.loads(raw)
    except Exception as e:
        print("JSON PARSE ERROR in generate_runbook_for_topic:", e)
        # Fallback: wrap raw text in a minimal JSON
        data = {
            "title": f"Runbook for {topic}",
            "summary": scrub_text(raw),
            "steps": [],
            "references": [],
        }

    # Normalize missing keys
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

    rb = Runbook.query.filter_by(topic=topic).first()
    if not rb:
        rb = Runbook(topic=topic, title=title)
        db.session.add(rb)

    rb.title = title
    rb.markdown = markdown   # <-- this is the correct variable
    rb.tickets_used = len(tickets)

    db.session.commit()
    return rb
