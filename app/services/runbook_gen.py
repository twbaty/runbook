# app/services/runbook_gen.py
import json
from datetime import datetime
from typing import List, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape
from flask import current_app

from ..extensions import db
from ..models import Ticket, Runbook
from .ai_client import call_llm

def get_env():
    """Return a Jinja2 environment bound to the app context."""
    root = current_app.root_path
    return Environment(
        loader=FileSystemLoader(root + "/templates"),
        autoescape=select_autoescape(["html", "xml", "md"])
    )

def classify_ticket_topic(ticket: Ticket) -> str:
    prompt = f"""
You are classifying a ServiceNow security-related ticket into a high-level topic label.
Return ONE short, lowercase label, no explanation.

Example labels:
- phishing
- vpn_failure
- cs_detection
- malware
- email_delivery
- privileged_access
- user_support
- other

Ticket:
Short description: {ticket.short_description}
Description: {ticket.description}
Work notes: {ticket.work_notes}
Resolution notes: {ticket.resolution_notes}
Category: {ticket.category}
Subcategory: {ticket.subcategory}
Assignment group: {ticket.assignment_group}
"""
    label = call_llm(prompt).strip().split()[0].lower()
    return label or "other"

def assign_topics_to_tickets(tickets: List[Ticket]) -> None:
    for t in tickets:
        if not t.topic:
            t.topic = classify_ticket_topic(t)
    db.session.commit()

def generate_runbook_for_topic(topic: str) -> Runbook:
    tickets = Ticket.query.filter_by(topic=topic).order_by(Ticket.opened_at.desc()).all()
    if not tickets:
        raise ValueError(f"No tickets found for topic '{topic}'")

    sample = tickets[:30]

    corpus = ""
    for t in sample:
        corpus += f"""
Ticket {t.number}
Short: {t.short_description}
Description: {t.description}
Work notes: {t.work_notes}
Resolution: {t.resolution_notes}
Opened: {t.opened_at}
Closed: {t.closed_at}
---
"""

    schema_hint = """
{
  "topic": "...",
  "title": "...",
  "scope": "...",
  "detection_signals": ["..."],
  "mitre_techniques": ["T1059", "..."],
  "prerequisites": ["..."],
  "investigation_steps": [{"title": "...", "details": "..."}],
  "containment_steps": [{"title": "...", "details": "..."}],
  "eradication_steps": [{"title": "...", "details": "..."}],
  "recovery_steps": [{"title": "...", "details": "..."}],
  "validation_checks": ["..."],
  "escalation_criteria": ["..."],
  "done_criteria": ["..."],
  "known_pitfalls": ["..."]
}
"""

    prompt = f"""
You are a senior security operations engineer.

Using the following incident tickets (all related to the same type of issue),
derive a STANDARDIZED incident response runbook.

Output ONLY valid JSON matching this structure (no comments, no extra keys):

{schema_hint}

Tickets:
{corpus}
"""
    raw = call_llm(prompt)
    data = json.loads(raw)

    # Render markdown from template
    env = get_env()
    temPlate = env.get_template("runbook.md.j2")

    markdown = template.render(runbook=data)

    rb = Runbook.query.filter_by(topic=topic).first()
    if rb is None:
        rb = Runbook(topic=topic)

    rb.title = data.get("title", f"{topic} runbook")
    rb.markdown = markdown
    rb.json_blob = json.dumps(data, indent=2)
    rb.tickets_used = len(sample)
    rb.last_updated = datetime.utcnow()

    db.session.add(rb)
    db.session.commit()

    return rb
