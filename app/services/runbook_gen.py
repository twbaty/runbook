# app/services/runbook_gen.py

import json
from flask import current_app
from jinja2 import Template

from ..models import Ticket, Runbook
from ..extensions import db
from .ai_client import call_llm


def generate_runbook_for_topic(topic: str) -> Runbook:
    # Get all tickets under this topic
    tickets = Ticket.query.filter_by(topic=topic).order_by(Ticket.opened_at).all()

    # Build input payload for the LLM
    payload = {
        "topic": topic,
        "tickets": [
            {
                "number": t.number,
                "short_description": t.short_description,
                "description": t.description,
                "opened_at": str(t.opened_at)
            }
            for t in tickets
        ]
    }

    prompt = f"""
You are a security analyst. Write a runbook in structured JSON.

INPUT DATA:
{json.dumps(payload, indent=2)}

REQUIREMENTS:
- Return ONLY valid JSON.
- Keys must be: "title", "summary", "steps", "references".
- "steps" must be a list of strings.
"""

    # Call LLM
    raw = call_llm(prompt)

    print("\nRAW LLM OUTPUT:\n", raw)

    # Try parsing JSON
    try:
        data = json.loads(raw)
    except Exception as e:
        print("JSON PARSE ERROR:", e)
        data = {
            "title": f"Runbook for {topic}",
            "summary": raw,
            "steps": [],
            "references": []
        }

    # Markdown template
    template = Template("""
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

    markdown = template.render(runbook=data)

    # Save or update runbook in DB
    rb = Runbook.query.filter_by(topic=topic).first()
    if not rb:
        rb = Runbook(topic=topic, title=data.get("title", f"Runbook for {topic}"))
        db.session.add(rb)

    rb.title = data.get("title", f"Runbook for {topic}")
    rb.markdown = markdown

    db.session.commit()

    return rb
