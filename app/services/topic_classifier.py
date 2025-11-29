# app/services/topic_classifier.py
"""
Deterministic topic classifier for ServiceNow tickets.
NO AI. NO randomness.
Maps tickets into a fixed, SOC-appropriate category set.
"""

import re


# ============================================================
# FIXED TOPIC SET (Option A)
# ============================================================

TOPICS = {
    "email_issue",
    "vpn_issue",
    "identity_issue",
    "access_issue",
    "endpoint_issue",
    "network_issue",
    "cloud_issue",
    "security_issue",
    "server_issue",
    "database_issue",
    "other",
}


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def _clean(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    # collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def _contains(text: str, *keywords) -> bool:
    """Case-insensitive keyword search."""
    text = text.lower()
    return any(kw in text for kw in keywords)


# ============================================================
# MAIN CLASSIFIER
# ============================================================

def classify(text: str) -> str:
    """
    Deterministic classification using keyword rules.
    Returns one of the fixed TOPICS.
    """
    t = _clean(text)

    # -------------------------------
    # EMAIL
    # -------------------------------
    if _contains(t,
        "email", "mail", "outlook",
        "phish", "spoof", "spam", "blocked sender",
        "mfa email", "smtp"
    ):
        return "email_issue"

    # -------------------------------
    # VPN
    # -------------------------------
    if _contains(t,
        "vpn", "globalprotect", "anyconnect",
        "remote access", "tunnel"
    ):
        return "vpn_issue"

    # -------------------------------
    # IDENTITY
    # -------------------------------
    if _contains(t,
        "mfa", "duo", "okta", "auth", "authentication",
        "password", "reset", "lockout"
    ):
        return "identity_issue"

    # -------------------------------
    # ACCESS PERMISSIONS
    # -------------------------------
    if _contains(t,
        "access", "permission", "privilege",
        "authorize", "rights", "role"
    ):
        return "access_issue"

    # -------------------------------
    # ENDPOINT DEVICE
    # -------------------------------
    if _contains(t,
        "laptop", "desktop", "workstation", "computer",
        "blue screen", "bsod", "slow machine",
        "endpoint", "device"
    ):
        return "endpoint_issue"

    # -------------------------------
    # NETWORK
    # -------------------------------
    if _contains(t,
        "network", "switch", "router", "firewall",
        "wireless", "wifi", "lan", "wan"
    ):
        return "network_issue"

    # -------------------------------
    # CLOUD
    # -------------------------------
    if _contains(t,
        "azure", "aws", "gcp",
        "cloud", "sharepoint", "onedrive"
    ):
        return "cloud_issue"

    # -------------------------------
    # SECURITY ALERTS
    # -------------------------------
    if _contains(t,
        "malware", "virus", "trojan",
        "edr", "falcon", "crowdstrike",
        "alert", "ioc", "compromise",
    ):
        return "security_issue"

    # -------------------------------
    # SERVER / APPLICATION
    # -------------------------------
    if _contains(t,
        "server", "iis", "apache",
        "service down", "service failure",
        "application error", "503", "500"
    ):
        return "server_issue"

    # -------------------------------
    # DATABASE
    # -------------------------------
    if _contains(t,
        "sql", "oracle", "postgres",
        "database", "db", "query failure"
    ):
        return "database_issue"

    # -------------------------------
    # FALLBACK
    # -------------------------------
    return "other"
