# app/services/classifier.py
"""
Ticket topic classifier.

Hybrid approach:
  1. Heuristics / keyword rules (fast, stable)
  2. LLM fallback (only when heuristics say 'other')
  3. Canonicalization into a fixed taxonomy.

Taxonomy (Option A):

  access_issue
  email_issue
  endpoint_issue
  network_issue
  cloud_issue
  vpn_issue
  security_issue
  phishing
  malware
  other
"""

from __future__ import annotations

from typing import List
import re

from ..models import Ticket
from .phi_scrub import scrub_text
from .ai_client import call_llm


CANONICAL_TOPICS = [
    "access_issue",
    "email_issue",
    "endpoint_issue",
    "network_issue",
    "cloud_issue",
    "vpn_issue",
    "security_issue",
    "phishing",
    "malware",
    "other",
]


def canonicalize_label(raw: str) -> str:
    """
    Map messy labels to our fixed taxonomy.
    Very forgiving: handles dashes, spaces, plural forms, etc.
    """
    if not raw:
        return "other"

    s = raw.strip().lower()

    # kill punctuation / spaces / underscores
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")

    # direct hits
    if s in CANONICAL_TOPICS:
        return s

    # common variants / typos / synonyms
    mapping = {
        "vpn": "vpn_issue",
        "vpnfailure": "vpn_issue",
        "vpn_issue_ticket": "vpn_issue",
        "vpn_issue_sla": "vpn_issue",

        "email": "email_issue",
        "mail": "email_issue",
        "emailissue": "email_issue",
        "email_issue_ticket": "email_issue",

        "endpoint": "endpoint_issue",
        "endpointissue": "endpoint_issue",

        "network": "network_issue",
        "networkissue": "network_issue",

        "cloud": "cloud_issue",
        "cloudissue": "cloud_issue",

        "security": "security_issue",
        "securityissue": "security_issue",
        "security_incident": "security_issue",
        "security_alert": "security_issue",

        "phish": "phishing",
        "phishing_email": "phishing",

        "virus": "malware",
        "ransomware": "malware",
        "trojan": "malware",
        "malwareinfection": "malware",
    }

    if s in mapping:
        return mapping[s]

    # If the LLM returns something like "email issue", normalize spaces
    s2 = s.replace("-", "_").replace("__", "_")
    if s2 in CANONICAL_TOPICS:
        return s2

    return "other"


# ---------------------------------------------------------------------------
# Heuristic keyword rules
# ---------------------------------------------------------------------------

# Order matters: earlier rules win.
HEURISTIC_RULES = [
    # Highly specific first (phishing / malware)
    (
        "phishing",
        [
            "phish", "phishing", "suspicious email", "spoofed", "impersonation",
            "fake email", "credential harvest", "link looks suspicious",
        ],
    ),
    (
        "malware",
        [
            "malware", "virus", "ransomware", "crypto locker", "cryptolocker",
            "trojan", "infection", "infected", "quarantined file",
        ],
    ),
    (
        "vpn_issue",
        [
            "vpn", "globalprotect", "global protect", "anyconnect",
            "remote access", "tunnel", "cannot connect vpn", "vpn failure",
        ],
    ),
    (
        "access_issue",
        [
            "login failed", "logon failed", "cannot log in", "cannot login",
            "sign in", "signin", "locked out", "lockout",
            "account locked", "password reset", "reset password",
            "mfa", "2fa", "two-factor", "duo", "entra", "okta", "auth error",
        ],
    ),
    (
        "email_issue",
        [
            "email", "e-mail", "outlook", "mailbox", "o365", "office 365",
            "exchange", "cannot send", "cannot receive", "bounce", "bounced",
            "undeliverable", "smtp", "message trace",
        ],
    ),
    (
        "endpoint_issue",
        [
            "laptop", "desktop", "workstation", "pc", "thin client",
            "endpoint", "agent", "sensor", "antivirus", "defender", "crowdstrike",
            "cylance", "mcafee", "trendmicro", "slow computer", "blue screen",
        ],
    ),
    (
        "network_issue",
        [
            "network down", "no network", "no connectivity", "cannot reach",
            "packet loss", "latency", "switch", "router", "firewall",
            "wifi", "wireless", "ssid", "lan", "wan", "link down",
        ],
    ),
    (
        "cloud_issue",
        [
            "azure", "aws", "gcp", "cloud", "s3", "bucket", "blob",
            "resource group", "subscription", "tenant",
        ],
    ),
    (
        "security_issue",
        [
            "siem", "soc", "security alert", "security incident",
            "correlation rule", "ioc", "indicator", "compromise", "breach",
            "threat", "edr", "idp", "ids", "ips",
        ],
    ),
]


def _build_ticket_text(ticket: Ticket) -> str:
    """
    Concatenate important fields into one blob for classification.
    """
    parts: List[str] = [
        ticket.short_description or "",
        ticket.description or "",
        ticket.category or "",
        ticket.subcategory or "",
        ticket.assignment_group or "",
        ticket.ci or "",
    ]
    text = " ".join(parts)
    return scrub_text(text)


def _heuristic_classify(text: str) -> str:
    """
    Simple keyword-based classification into our taxonomy.
    Returns a canonical topic or 'other'.
    """
    if not text:
        return "other"

    low = text.lower()

    for topic, keywords in HEURISTIC_RULES:
        for kw in keywords:
            if kw in low:
                return topic

    return "other"


def _llm_classify(text: str) -> str:
    """
    LLM-based classifier. Only called when heuristics say 'other'.

    We FORCE the model to choose ONE of our taxonomy labels.
    """
    prompt = f"""
You are a classifier for IT incident tickets.

Your job is to assign ONE topic label from this fixed list:

- access_issue
- email_issue
- endpoint_issue
- network_issue
- cloud_issue
- vpn_issue
- security_issue
- phishing
- malware
- other

Rules:
- Read the ticket text.
- Pick the ONE best fitting label from the above list.
- If you are not sure, use "other".
- Respond with ONLY the raw label, nothing else.

Ticket text:
{text}
"""

    raw = call_llm(prompt)
    # Take the first token/word in case the model babbles
    label = raw.strip().split()[0]
    return canonicalize_label(label)


def classify_ticket(ticket: Ticket) -> str:
    """
    Main entry point.

    1) Build text from ticket fields
    2) Run heuristic classifier
    3) If result is 'other', call LLM to try to refine
    4) Fallback to 'other' if LLM fails
    """
    text = _build_ticket_text(ticket)

    # Quick out if ticket is basically empty
    if not text or len(text.split()) < 3:
        return "other"

    # Step 1: heuristics
    topic = _heuristic_classify(text)
    if topic != "other":
        return topic

    # Step 2: LLM fallback
    try:
        topic = _llm_classify(text)
        if topic in CANONICAL_TOPICS:
            return topic
    except Exception as e:
        # Don't blow up the import because of LLM weirdness
        print("LLM classify error:", e)

    return "other"
